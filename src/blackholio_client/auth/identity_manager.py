"""
Identity Manager - SpacetimeDB Identity Creation and Management

Handles creation, storage, and loading of SpacetimeDB identities
with support for cryptographic key generation and persistence.
"""

import os
import json
import logging
import hashlib
import secrets
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, Union
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from ..exceptions.connection_errors import (
    AuthenticationError,
    DataValidationError,
    create_data_validation_error
)


logger = logging.getLogger(__name__)


@dataclass
class Identity:
    """
    SpacetimeDB Identity representation.
    
    Contains the cryptographic identity and metadata for SpacetimeDB authentication.
    """
    name: str
    identity_id: str
    public_key: str  # Base64 encoded public key
    private_key: str  # Base64 encoded private key (encrypted in storage)
    created_at: float
    last_used: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Post-initialization validation."""
        if not self.name:
            raise ValueError("Identity name is required")
        if not self.identity_id:
            raise ValueError("Identity ID is required")
        if not self.public_key:
            raise ValueError("Public key is required")
        if not self.private_key:
            raise ValueError("Private key is required")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert identity to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Identity':
        """Create Identity from dictionary."""
        return cls(
            name=data['name'],
            identity_id=data['identity_id'],
            public_key=data['public_key'],
            private_key=data['private_key'],
            created_at=data['created_at'],
            last_used=data.get('last_used'),
            metadata=data.get('metadata', {})
        )
    
    def get_public_key_bytes(self) -> bytes:
        """Get public key as bytes."""
        import base64
        return base64.b64decode(self.public_key)
    
    def get_private_key_bytes(self) -> bytes:
        """Get private key as bytes."""
        import base64
        return base64.b64decode(self.private_key)
    
    def get_ed25519_private_key(self) -> ed25519.Ed25519PrivateKey:
        """Get Ed25519 private key object."""
        private_key_bytes = self.get_private_key_bytes()
        return ed25519.Ed25519PrivateKey.from_private_bytes(private_key_bytes)
    
    def get_ed25519_public_key(self) -> ed25519.Ed25519PublicKey:
        """Get Ed25519 public key object."""
        public_key_bytes = self.get_public_key_bytes()
        return ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
    
    def sign_data(self, data: bytes) -> bytes:
        """Sign data with this identity's private key."""
        private_key = self.get_ed25519_private_key()
        return private_key.sign(data)
    
    def verify_signature(self, data: bytes, signature: bytes) -> bool:
        """Verify signature against this identity's public key."""
        try:
            public_key = self.get_ed25519_public_key()
            public_key.verify(signature, data)
            return True
        except Exception:
            return False
    
    @classmethod
    def generate(cls, name: str = "default", metadata: Optional[Dict[str, Any]] = None) -> 'Identity':
        """
        Generate a new identity with Ed25519 keys.
        
        Args:
            name: Name for the identity
            metadata: Optional metadata
            
        Returns:
            New Identity instance
        """
        import base64
        from datetime import datetime
        
        # Generate Ed25519 key pair
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        
        # Serialize keys
        private_key_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
        public_key_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        # Encode to base64
        private_key_b64 = base64.b64encode(private_key_bytes).decode('ascii')
        public_key_b64 = base64.b64encode(public_key_bytes).decode('ascii')
        
        # Generate identity ID from public key
        import hashlib
        identity_id = hashlib.sha256(public_key_bytes).hexdigest()[:16]
        
        return cls(
            name=name,
            identity_id=identity_id,
            private_key=private_key_b64,
            public_key=public_key_b64,
            created_at=datetime.now().timestamp(),
            metadata=metadata or {}
        )


class IdentityManager:
    """
    Manages SpacetimeDB identities with secure storage and cryptographic operations.
    
    Provides identity creation, storage, loading, and management for SpacetimeDB
    authentication with Ed25519 cryptographic keys.
    """
    
    def __init__(self, identity_dir: Optional[Union[str, Path]] = None):
        """
        Initialize identity manager.
        
        Args:
            identity_dir: Directory to store identity files (default: ~/.blackholio/identities)
        """
        if identity_dir is None:
            self.identity_dir = Path.home() / ".blackholio" / "identities"
        else:
            self.identity_dir = Path(identity_dir)
        
        # Create directory if it doesn't exist
        self.identity_dir.mkdir(parents=True, exist_ok=True)
        
        # Set secure permissions (owner read/write only)
        if os.name != 'nt':  # Unix-like systems
            os.chmod(self.identity_dir, 0o700)
        
        self._identities: Dict[str, Identity] = {}
        self._load_identities()
        
        logger.info(f"Identity manager initialized with directory: {self.identity_dir}")
    
    def create_identity(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> Identity:
        """
        Create a new SpacetimeDB identity with Ed25519 keys.
        
        Args:
            name: Human-readable name for the identity
            metadata: Optional metadata to store with identity
            
        Returns:
            Created Identity object
            
        Raises:
            ValueError: If identity name already exists
        """
        if not name or not name.strip():
            raise ValueError("Identity name cannot be empty")
        
        name = name.strip()
        
        if name in self._identities:
            raise ValueError(f"Identity '{name}' already exists")
        
        # Generate Ed25519 key pair
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        
        # Serialize keys
        private_key_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
        public_key_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        # Encode to base64 for storage
        import base64
        private_key_b64 = base64.b64encode(private_key_bytes).decode('ascii')
        public_key_b64 = base64.b64encode(public_key_bytes).decode('ascii')
        
        # Create identity ID from public key hash
        identity_id = self._generate_identity_id(public_key_bytes)
        
        # Create identity object
        import time
        identity = Identity(
            name=name,
            identity_id=identity_id,
            public_key=public_key_b64,
            private_key=private_key_b64,
            created_at=time.time(),
            metadata=metadata or {}
        )
        
        # Store identity
        self._identities[name] = identity
        self._save_identity(identity)
        
        logger.info(f"Created new identity: {name} (ID: {identity_id})")
        return identity
    
    def load_identity(self, name: str) -> Optional[Identity]:
        """
        Load identity by name.
        
        Args:
            name: Identity name
            
        Returns:
            Identity object or None if not found
        """
        return self._identities.get(name)
    
    def get_identity_by_id(self, identity_id: str) -> Optional[Identity]:
        """
        Get identity by ID.
        
        Args:
            identity_id: Identity ID
            
        Returns:
            Identity object or None if not found
        """
        for identity in self._identities.values():
            if identity.identity_id == identity_id:
                return identity
        return None
    
    def list_identities(self) -> Dict[str, Identity]:
        """
        Get all available identities.
        
        Returns:
            Dictionary mapping names to Identity objects
        """
        return self._identities.copy()
    
    def delete_identity(self, name: str) -> bool:
        """
        Delete an identity.
        
        Args:
            name: Identity name
            
        Returns:
            True if deleted, False if not found
        """
        if name not in self._identities:
            return False
        
        # Remove from memory
        identity = self._identities.pop(name)
        
        # Remove file
        identity_file = self.identity_dir / f"{name}.json"
        try:
            if identity_file.exists():
                identity_file.unlink()
            logger.info(f"Deleted identity: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete identity file for {name}: {e}")
            # Re-add to memory if file deletion failed
            self._identities[name] = identity
            return False
    
    def update_last_used(self, name: str):
        """
        Update the last used timestamp for an identity.
        
        Args:
            name: Identity name
        """
        if name in self._identities:
            import time
            self._identities[name].last_used = time.time()
            self._save_identity(self._identities[name])
    
    def export_identity(self, name: str, password: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Export identity for backup or transfer.
        
        Args:
            name: Identity name
            password: Optional password for encryption
            
        Returns:
            Exported identity data or None if not found
        """
        identity = self.load_identity(name)
        if not identity:
            return None
        
        export_data = identity.to_dict()
        
        # Encrypt private key if password provided
        if password:
            # TODO: Implement password-based encryption
            logger.warning("Password encryption not yet implemented")
        
        return export_data
    
    def import_identity(self, data: Dict[str, Any], password: Optional[str] = None, 
                       overwrite: bool = False) -> bool:
        """
        Import identity from exported data.
        
        Args:
            data: Exported identity data
            password: Password if data is encrypted
            overwrite: Whether to overwrite existing identity
            
        Returns:
            True if imported successfully
        """
        try:
            # Decrypt if password provided
            if password:
                # TODO: Implement password-based decryption
                logger.warning("Password decryption not yet implemented")
            
            identity = Identity.from_dict(data)
            
            if identity.name in self._identities and not overwrite:
                raise ValueError(f"Identity '{identity.name}' already exists")
            
            self._identities[identity.name] = identity
            self._save_identity(identity)
            
            logger.info(f"Imported identity: {identity.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import identity: {e}")
            return False
    
    def _generate_identity_id(self, public_key_bytes: bytes) -> str:
        """Generate identity ID from public key."""
        # Create SHA-256 hash of public key
        digest = hashes.Hash(hashes.SHA256())
        digest.update(public_key_bytes)
        hash_bytes = digest.finalize()
        
        # Return first 16 bytes as hex string
        return hash_bytes[:16].hex()
    
    def _load_identities(self):
        """Load all identities from storage."""
        if not self.identity_dir.exists():
            return
        
        for identity_file in self.identity_dir.glob("*.json"):
            try:
                identity_file = Path(identity_file).resolve()
                if not str(identity_file).startswith(str(Path.cwd())):
                    raise ValueError(f"Path traversal detected: {identity_file}")
                with open(identity_file, 'r') as f:
                    data = json.load(f)
                
                identity = Identity.from_dict(data)
                self._identities[identity.name] = identity
                
            except Exception as e:
                logger.error(f"Failed to load identity from {identity_file}: {e}")
        
        logger.info(f"Loaded {len(self._identities)} identities")
    
    def _save_identity(self, identity: Identity):
        """Save identity to storage."""
        identity_file = self.identity_dir / f"{identity.name}.json"
        
        try:
            # Save with secure permissions
            identity_file = Path(identity_file).resolve()
            if not str(identity_file).startswith(str(Path.cwd())):
                raise ValueError(f"Path traversal detected: {identity_file}")
            with open(identity_file, 'w') as f:
                json.dump(identity.to_dict(), f, indent=2)
            
            # Set secure permissions (owner read/write only)
            if os.name != 'nt':  # Unix-like systems
                os.chmod(identity_file, 0o600)
                
        except Exception as e:
            logger.error(f"Failed to save identity {identity.name}: {e}")
            raise
    
    def get_or_create_default_identity(self, name: str = "default") -> Identity:
        """
        Get existing default identity or create one if it doesn't exist.
        
        Args:
            name: Name for the default identity
            
        Returns:
            Default Identity object
        """
        identity = self.load_identity(name)
        if identity is None:
            identity = self.create_identity(name, {"default": True})
        return identity


# Global identity manager instance
_global_identity_manager: Optional[IdentityManager] = None


def get_identity_manager(identity_dir: Optional[Union[str, Path]] = None) -> IdentityManager:
    """
    Get global identity manager instance.
    
    Args:
        identity_dir: Directory for identities (only used on first call)
        
    Returns:
        IdentityManager instance
    """
    global _global_identity_manager
    
    if _global_identity_manager is None:
        _global_identity_manager = IdentityManager(identity_dir)
    
    return _global_identity_manager


def set_identity_manager(manager: IdentityManager):
    """
    Set global identity manager instance.
    
    Args:
        manager: IdentityManager instance to set as global
    """
    global _global_identity_manager
    _global_identity_manager = manager