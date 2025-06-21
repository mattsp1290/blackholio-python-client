"""
SpacetimeDB Client Generator

Dynamically generates SpacetimeDB client code for different server languages
using the SpacetimeDB CLI tool.
"""

import os
import subprocess
import shutil
import tempfile
import logging
from pathlib import Path
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import asyncio

def _validate_command_args(args: List[str]) -> None:
    """Validate command arguments to prevent injection attacks"""
    if not args:
        raise ValueError("Command arguments cannot be empty")
    
    # Check for dangerous characters
    dangerous_chars = [';', '&', '|', '`', '$', '(', ')']
    for arg in args:
        if not isinstance(arg, str):
            raise ValueError(f"All arguments must be strings, got {type(arg)}")
        for char in dangerous_chars:
            if char in arg:
                raise ValueError(f"Dangerous character '{char}' found in argument: {arg}")
    
    # Validate executable name
    if not args[0] or '..' in args[0] or '/' in args[0]:
        if args[0] not in ['spacetimedb', 'which', 'lsof']:
            raise ValueError(f"Invalid executable: {args[0]}")


from ..config.environment import EnvironmentConfig, get_environment_config
from ..exceptions.connection_errors import BlackholioConnectionError


logger = logging.getLogger(__name__)


@dataclass
class ClientGenerationConfig:
    """Configuration for client generation process."""
    server_language: str
    server_path: str
    output_dir: str
    generated_lang: str = "python"
    timeout: float = 30.0
    cleanup_on_error: bool = True


@dataclass
class GenerationResult:
    """Result of client generation process."""
    success: bool
    output_dir: str
    generated_files: List[str]
    error_message: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None


class SpacetimeDBClientGenerator:
    """
    Generates SpacetimeDB client code for different server languages.
    
    This class handles the dynamic generation of SpacetimeDB client bindings
    based on the server language specified in environment configuration.
    """
    
    # Default server paths based on language
    DEFAULT_SERVER_PATHS = {
        'rust': '$HOME/git/Blackholio/server-rust',
        'python': '$HOME/git/Blackholio/server-python', 
        'csharp': '$HOME/git/Blackholio/server-csharp',
        'go': '$HOME/git/Blackholio/server-go'
    }
    
    # SpacetimeDB CLI executable paths
    SPACETIMEDB_CLI_PATHS = [
        '/Users/punk1290/git/SpacetimeDB/target/release/spacetimedb-cli',
        '/usr/local/bin/spacetimedb',
        'spacetimedb'  # System PATH
    ]
    
    def __init__(self, config: Optional[EnvironmentConfig] = None):
        """
        Initialize the client generator.
        
        Args:
            config: Environment configuration (uses global if not provided)
        """
        self.config = config or get_environment_config()
        self.spacetimedb_cli_path = self._find_spacetimedb_cli()
        self._generated_clients_cache: Dict[str, str] = {}
        
        logger.info(f"SpacetimeDB Client Generator initialized with server language: {self.config.server_language}")
    
    def _find_spacetimedb_cli(self) -> str:
        """
        Find the SpacetimeDB CLI executable.
        
        Returns:
            Path to spacetimedb-cli executable
            
        Raises:
            BlackholioConnectionError: If CLI not found
        """
        for cli_path in self.SPACETIMEDB_CLI_PATHS:
            expanded_path = os.path.expanduser(cli_path)
            
            if os.path.isfile(expanded_path) and os.access(expanded_path, os.X_OK):
                logger.info(f"Found SpacetimeDB CLI at: {expanded_path}")
                return expanded_path
        
        # Try using 'which' command
        try:
            result = subprocess.run(['which', 'spacetimedb'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                cli_path = result.stdout.strip()
                logger.info(f"Found SpacetimeDB CLI via 'which': {cli_path}")
                return cli_path
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            pass
        
        raise BlackholioConnectionError(
            "SpacetimeDB CLI not found. Please install SpacetimeDB or set correct path."
        )
    
    def get_server_path(self, server_language: Optional[str] = None) -> str:
        """
        Get the server path for the specified language.
        
        Args:
            server_language: Server language (uses config default if not provided)
            
        Returns:
            Expanded server path
            
        Raises:
            BlackholioConnectionError: If server path not found
        """
        language = server_language or self.config.server_language
        
        if language not in self.DEFAULT_SERVER_PATHS:
            raise BlackholioConnectionError(f"Unsupported server language: {language}")
        
        server_path = os.path.expanduser(self.DEFAULT_SERVER_PATHS[language])
        
        if not os.path.isdir(server_path):
            raise BlackholioConnectionError(f"Server directory not found: {server_path}")
        
        return server_path
    
    def generate_client(self, 
                       server_language: Optional[str] = None,
                       output_dir: Optional[str] = None,
                       force_regenerate: bool = False) -> GenerationResult:
        """
        Generate SpacetimeDB client code for the specified server language.
        
        Args:
            server_language: Server language to generate client for
            output_dir: Output directory (uses temp dir if not provided)
            force_regenerate: Force regeneration even if cached
            
        Returns:
            GenerationResult with generation status and details
        """
        language = server_language or self.config.server_language
        
        # Check cache if not forcing regeneration
        if not force_regenerate and language in self._generated_clients_cache:
            cached_dir = self._generated_clients_cache[language]
            if os.path.isdir(cached_dir):
                logger.info(f"Using cached client for {language}: {cached_dir}")
                return GenerationResult(
                    success=True,
                    output_dir=cached_dir,
                    generated_files=self._list_generated_files(cached_dir)
                )
        
        # Create generation config
        server_path = self.get_server_path(language)
        temp_output_dir = output_dir or tempfile.mkdtemp(prefix=f"spacetime_client_{language}_")
        
        gen_config = ClientGenerationConfig(
            server_language=language,
            server_path=server_path,
            output_dir=temp_output_dir,
            timeout=self.config.connection_timeout
        )
        
        logger.info(f"Generating SpacetimeDB client for {language} server at {server_path}")
        
        try:
            result = self._execute_generation(gen_config)
            
            if result.success:
                # Cache successful generation
                self._generated_clients_cache[language] = result.output_dir
                logger.info(f"Successfully generated client for {language}")
            else:
                logger.error(f"Failed to generate client for {language}: {result.error_message}")
                
                # Cleanup on error if requested
                if gen_config.cleanup_on_error and not output_dir:
                    self._cleanup_directory(temp_output_dir)
            
            return result
            
        except Exception as e:
            logger.error(f"Unexpected error during client generation: {e}")
            
            # Cleanup on error
            if gen_config.cleanup_on_error and not output_dir:
                self._cleanup_directory(temp_output_dir)
            
            return GenerationResult(
                success=False,
                output_dir=temp_output_dir,
                generated_files=[],
                error_message=str(e)
            )
    
    def _execute_generation(self, config: ClientGenerationConfig) -> GenerationResult:
        """
        Execute the actual client generation process.
        
        Args:
            config: Generation configuration
            
        Returns:
            GenerationResult with execution details
        """
        # Ensure output directory exists
        os.makedirs(config.output_dir, exist_ok=True)
        
        # Build spacetimedb generate command
        cmd = [
            self.spacetimedb_cli_path,
            'generate',
            '--lang', config.generated_lang,
            '--out-dir', config.output_dir
        ]
        
        logger.debug(f"Executing command: {' '.join(cmd)}")
        logger.debug(f"Working directory: {config.server_path}")
        
        try:
            # Execute the generation command
            result = subprocess.run(
                cmd,
                cwd=config.server_path,
                capture_output=True,
                text=True,
                timeout=config.timeout
            )
            
            stdout = result.stdout.strip() if result.stdout else ""
            stderr = result.stderr.strip() if result.stderr else ""
            
            logger.debug(f"Command stdout: {stdout}")
            if stderr:
                logger.debug(f"Command stderr: {stderr}")
            
            if result.returncode == 0:
                generated_files = self._list_generated_files(config.output_dir)
                
                if not generated_files:
                    return GenerationResult(
                        success=False,
                        output_dir=config.output_dir,
                        generated_files=[],
                        error_message="No files were generated",
                        stdout=stdout,
                        stderr=stderr
                    )
                
                return GenerationResult(
                    success=True,
                    output_dir=config.output_dir,
                    generated_files=generated_files,
                    stdout=stdout,
                    stderr=stderr
                )
            else:
                error_msg = f"Command failed with return code {result.returncode}"
                if stderr:
                    error_msg += f": {stderr}"
                
                return GenerationResult(
                    success=False,
                    output_dir=config.output_dir,
                    generated_files=[],
                    error_message=error_msg,
                    stdout=stdout,
                    stderr=stderr
                )
                
        except subprocess.TimeoutExpired:
            return GenerationResult(
                success=False,
                output_dir=config.output_dir,
                generated_files=[],
                error_message=f"Command timed out after {config.timeout} seconds"
            )
        except subprocess.SubprocessError as e:
            return GenerationResult(
                success=False,
                output_dir=config.output_dir,
                generated_files=[],
                error_message=f"Subprocess error: {e}"
            )
    
    def _list_generated_files(self, output_dir: str) -> List[str]:
        """
        List all generated files in the output directory.
        
        Args:
            output_dir: Directory to scan for generated files
            
        Returns:
            List of generated file paths
        """
        if not os.path.isdir(output_dir):
            return []
        
        generated_files = []
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                file_path = os.path.join(root, file)
                # Make path relative to output directory
                rel_path = os.path.relpath(file_path, output_dir)
                generated_files.append(rel_path)
        
        return sorted(generated_files)
    
    def _cleanup_directory(self, directory: str):
        """
        Clean up a directory and its contents.
        
        Args:
            directory: Directory to clean up
        """
        try:
            if os.path.isdir(directory):
                shutil.rmtree(directory)
                logger.debug(f"Cleaned up directory: {directory}")
        except Exception as e:
            logger.warning(f"Failed to cleanup directory {directory}: {e}")
    
    async def generate_client_async(self,
                                   server_language: Optional[str] = None,
                                   output_dir: Optional[str] = None,
                                   force_regenerate: bool = False) -> GenerationResult:
        """
        Asynchronously generate SpacetimeDB client code.
        
        Args:
            server_language: Server language to generate client for
            output_dir: Output directory (uses temp dir if not provided)
            force_regenerate: Force regeneration even if cached
            
        Returns:
            GenerationResult with generation status and details
        """
        loop = asyncio.get_event_loop()
        
        with ThreadPoolExecutor() as executor:
            try:
                result = await loop.run_in_executor(
                    executor,
                    self.generate_client,
                    server_language,
                    output_dir,
                    force_regenerate
                )
                return result
            except Exception as e:
                logger.error(f"Async generation failed: {e}")
                return GenerationResult(
                    success=False,
                    output_dir=output_dir or "",
                    generated_files=[],
                    error_message=f"Async execution failed: {e}"
                )
    
    def generate_all_clients(self, 
                            output_base_dir: Optional[str] = None,
                            force_regenerate: bool = False) -> Dict[str, GenerationResult]:
        """
        Generate clients for all supported server languages.
        
        Args:
            output_base_dir: Base directory for outputs (uses temp dirs if not provided)
            force_regenerate: Force regeneration for all languages
            
        Returns:
            Dictionary mapping language to GenerationResult
        """
        results = {}
        
        for language in self.DEFAULT_SERVER_PATHS.keys():
            try:
                output_dir = None
                if output_base_dir:
                    output_dir = os.path.join(output_base_dir, f"client_{language}")
                
                result = self.generate_client(
                    server_language=language,
                    output_dir=output_dir,
                    force_regenerate=force_regenerate
                )
                results[language] = result
                
            except Exception as e:
                logger.error(f"Failed to generate client for {language}: {e}")
                results[language] = GenerationResult(
                    success=False,
                    output_dir=output_dir or "",
                    generated_files=[],
                    error_message=str(e)
                )
        
        return results
    
    def clear_cache(self):
        """Clear the generated clients cache."""
        for language, cache_dir in self._generated_clients_cache.items():
            self._cleanup_directory(cache_dir)
        
        self._generated_clients_cache.clear()
        logger.info("Cleared generated clients cache")
    
    def get_cached_client(self, server_language: str) -> Optional[str]:
        """
        Get cached client directory for a server language.
        
        Args:
            server_language: Server language to get cached client for
            
        Returns:
            Cached client directory path or None if not cached
        """
        cached_dir = self._generated_clients_cache.get(server_language)
        
        if cached_dir and os.path.isdir(cached_dir):
            return cached_dir
        
        # Remove invalid cache entry
        if server_language in self._generated_clients_cache:
            del self._generated_clients_cache[server_language]
        
        return None
    
    def validate_spacetimedb_cli(self) -> Dict[str, Any]:
        """
        Validate SpacetimeDB CLI installation and capabilities.
        
        Returns:
            Validation results dictionary
        """
        try:
            # Test CLI accessibility
            result = subprocess.run([self.spacetimedb_cli_path, '--version'],
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                return {
                    'valid': False,
                    'error': f"CLI returned error code {result.returncode}",
                    'stderr': result.stderr
                }
            
            version_info = result.stdout.strip()
            
            # Test generate command help
            help_result = subprocess.run([self.spacetimedb_cli_path, 'generate', '--help'],
                                       capture_output=True, text=True, timeout=10)
            
            return {
                'valid': True,
                'cli_path': self.spacetimedb_cli_path,
                'version': version_info,
                'generate_help_available': help_result.returncode == 0
            }
            
        except subprocess.TimeoutExpired:
            return {
                'valid': False,
                'error': 'CLI validation timed out'
            }
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }
    
    def __str__(self) -> str:
        """String representation of the generator."""
        return f"SpacetimeDBClientGenerator(language={self.config.server_language}, cli={self.spacetimedb_cli_path})"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (f"SpacetimeDBClientGenerator(config={self.config}, "
                f"cli_path='{self.spacetimedb_cli_path}', "
                f"cached_clients={list(self._generated_clients_cache.keys())})")