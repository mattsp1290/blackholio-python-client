#!/bin/bash
# 
# Automated Release Script for blackholio-python-client
#
# This script handles the complete release process including:
# - Version validation and bumping
# - Changelog generation  
# - Git tagging and pushing
# - GitHub release creation
# - Package building and validation
#
# Usage:
#   ./scripts/release.sh [major|minor|patch|auto] [--prerelease=alpha|beta|rc] [--dry-run]
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Configuration
PACKAGE_NAME="blackholio-client"
PYTHON_CMD="python3"
VERSION_MANAGER="$SCRIPT_DIR/version_manager.py"

# Default values
BUMP_TYPE="patch"
PRERELEASE=""
DRY_RUN=false
AUTO_BUMP=false
FORCE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        major|minor|patch|auto)
            BUMP_TYPE="$1"
            if [[ "$BUMP_TYPE" == "auto" ]]; then
                AUTO_BUMP=true
            fi
            shift
            ;;
        --prerelease=*)
            PRERELEASE="${1#*=}"
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [major|minor|patch|auto] [options]"
            echo ""
            echo "Options:"
            echo "  --prerelease=ID    Add prerelease identifier (alpha, beta, rc)"
            echo "  --dry-run          Show what would be done without making changes"
            echo "  --force            Skip confirmation prompts"
            echo "  -h, --help         Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 patch           # Bump patch version"
            echo "  $0 minor           # Bump minor version"
            echo "  $0 auto            # Auto-detect version bump from commits"
            echo "  $0 major --dry-run # Show what major release would do"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Change to project root
cd "$PROJECT_ROOT"

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_requirements() {
    log_info "Checking requirements..."
    
    # Check if we're in a git repository
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_error "Not in a git repository"
        exit 1
    fi
    
    # Check for uncommitted changes
    if [[ $(git status --porcelain) ]] && [[ "$FORCE" != true ]]; then
        log_error "Uncommitted changes detected. Commit or stash changes first, or use --force"
        git status --short
        exit 1
    fi
    
    # Check if we're on main branch
    CURRENT_BRANCH=$(git branch --show-current)
    if [[ "$CURRENT_BRANCH" != "main" ]] && [[ "$CURRENT_BRANCH" != "master" ]] && [[ "$FORCE" != true ]]; then
        log_warning "Not on main/master branch (currently on: $CURRENT_BRANCH)"
        if [[ "$DRY_RUN" != true ]]; then
            read -p "Continue anyway? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_error "Release cancelled"
                exit 1
            fi
        fi
    fi
    
    # Check Python version
    if ! command -v "$PYTHON_CMD" &> /dev/null; then
        log_error "Python 3 not found"
        exit 1
    fi
    
    # Check for required Python packages
    if ! "$PYTHON_CMD" -c "import toml" 2>/dev/null; then
        log_info "Installing required Python packages..."
        "$PYTHON_CMD" -m pip install toml
    fi
    
    # Check for gh CLI (optional)
    if ! command -v gh &> /dev/null; then
        log_warning "GitHub CLI (gh) not found - GitHub releases will be skipped"
    fi
    
    log_success "Requirements check passed"
}

get_current_version() {
    "$PYTHON_CMD" "$VERSION_MANAGER" current | cut -d' ' -f3
}

validate_version_bump() {
    local current_version=$(get_current_version)
    log_info "Current version: $current_version"
    
    # Get next version
    local next_version_args="next $BUMP_TYPE"
    if [[ -n "$PRERELEASE" ]]; then
        next_version_args="$next_version_args --prerelease $PRERELEASE"
    fi
    if [[ "$AUTO_BUMP" == true ]]; then
        next_version_args="$next_version_args --auto"
    fi
    
    local next_version=$("$PYTHON_CMD" "$VERSION_MANAGER" $next_version_args | cut -d' ' -f3)
    
    if [[ "$current_version" == "$next_version" ]]; then
        log_error "Version would not change ($current_version -> $next_version)"
        exit 1
    fi
    
    log_info "Next version: $next_version"
    echo "$next_version"
}

run_tests() {
    log_info "Running test suite..."
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "DRY RUN: Would run test suite"
        return 0
    fi
    
    # Run tests
    if ! make test-quick 2>/dev/null || ! "$PYTHON_CMD" -m pytest tests/ -x; then
        log_error "Tests failed - cannot proceed with release"
        exit 1
    fi
    
    log_success "All tests passed"
}

build_package() {
    log_info "Building package..."
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "DRY RUN: Would build package"
        return 0
    fi
    
    # Clean previous builds
    rm -rf build/ dist/ *.egg-info/
    
    # Build package
    if ! "$PYTHON_CMD" -m build; then
        log_error "Package build failed"
        exit 1
    fi
    
    # Validate package
    if ! "$PYTHON_CMD" -m twine check dist/*; then
        log_error "Package validation failed"
        exit 1
    fi
    
    log_success "Package built and validated"
}

create_github_release() {
    local version="$1"
    local tag_name="v$version"
    
    log_info "Creating GitHub release..."
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "DRY RUN: Would create GitHub release $tag_name"
        return 0
    fi
    
    if ! command -v gh &> /dev/null; then
        log_warning "GitHub CLI not available - skipping GitHub release"
        return 0
    fi
    
    # Check if release already exists
    if gh release view "$tag_name" &>/dev/null; then
        log_warning "GitHub release $tag_name already exists"
        return 0
    fi
    
    # Generate release notes from changelog
    local release_notes=""
    if [[ -f "CHANGELOG.md" ]]; then
        # Extract release notes for this version from changelog
        release_notes=$(awk "/## \[$version\]/{flag=1; next} /## \[/{flag=0} flag" CHANGELOG.md | head -n -1)
    fi
    
    if [[ -z "$release_notes" ]]; then
        release_notes="Release $version

See CHANGELOG.md for detailed changes."
    fi
    
    # Create GitHub release
    if gh release create "$tag_name" \
        --title "Release $version" \
        --notes "$release_notes" \
        dist/*; then
        log_success "Created GitHub release $tag_name"
    else
        log_warning "Failed to create GitHub release (non-fatal)"
    fi
}

perform_release() {
    local version="$1"
    
    log_info "Performing release $version..."
    
    # Build release arguments
    local release_args="release $BUMP_TYPE"
    if [[ -n "$PRERELEASE" ]]; then
        release_args="$release_args --prerelease $PRERELEASE"
    fi
    if [[ "$AUTO_BUMP" == true ]]; then
        release_args="$release_args --auto"
    fi
    if [[ "$DRY_RUN" == true ]]; then
        release_args="$release_args --dry-run"
    fi
    
    # Run version manager
    if ! "$PYTHON_CMD" "$VERSION_MANAGER" $release_args; then
        log_error "Version management failed"
        exit 1
    fi
    
    if [[ "$DRY_RUN" == true ]]; then
        log_success "DRY RUN: Release simulation completed"
        return 0
    fi
    
    # Push changes to remote
    log_info "Pushing changes to remote..."
    if ! git push origin "$(git branch --show-current)" --tags; then
        log_error "Failed to push changes to remote"
        exit 1
    fi
    
    log_success "Release $version completed successfully!"
}

main() {
    echo "🚀 Starting release process for $PACKAGE_NAME..."
    echo "📋 Bump type: $BUMP_TYPE"
    if [[ -n "$PRERELEASE" ]]; then
        echo "🏷️  Prerelease: $PRERELEASE"
    fi
    if [[ "$DRY_RUN" == true ]]; then
        echo "🧪 DRY RUN MODE - No changes will be made"
    fi
    echo ""
    
    # Run preflight checks
    check_requirements
    
    # Validate version bump
    local next_version=$(validate_version_bump)
    
    # Confirm release
    if [[ "$DRY_RUN" != true ]] && [[ "$FORCE" != true ]]; then
        echo ""
        read -p "🚀 Release version $next_version? (y/N): " -r
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_error "Release cancelled by user"
            exit 0
        fi
    fi
    
    # Run tests
    run_tests
    
    # Build package
    build_package
    
    # Perform release
    perform_release "$next_version"
    
    # Create GitHub release
    create_github_release "$next_version"
    
    echo ""
    log_success "🎉 Release $next_version completed successfully!"
    echo ""
    echo "📋 Next steps:"
    echo "   - Verify the release on GitHub"
    echo "   - Update any dependent projects"
    echo "   - Announce the release to stakeholders"
    echo ""
}

# Run main function
main "$@"