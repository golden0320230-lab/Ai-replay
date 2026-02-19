"""Deterministic hashing for canonical data."""

from __future__ import annotations

import hashlib
from typing import Any, Optional

from .serializer import CanonicalSerializer


class CanonicalHasher:
    """Deterministic hasher for canonical data.
    
    Produces identical hashes for logically equivalent data
    across different platforms and Python versions.
    """
    
    def __init__(
        self,
        serializer: Optional[CanonicalSerializer] = None,
        algorithm: str = "sha256"
    ):
        """Initialize hasher.
        
        Args:
            serializer: Canonical serializer to use.
            algorithm: Hash algorithm (sha256, sha512, blake2b).
        """
        self._serializer = serializer or CanonicalSerializer()
        self._algorithm = algorithm
    
    def hash(self, data: Any) -> str:
        """Produce deterministic hash of data.
        
        Args:
            data: Data to hash.
            
        Returns:
            Hexadecimal hash string.
        """
        canonical = self._serializer.serialize_bytes(data)
        
        if self._algorithm == "sha256":
            return hashlib.sha256(canonical).hexdigest()
        elif self._algorithm == "sha512":
            return hashlib.sha512(canonical).hexdigest()
        elif self._algorithm == "blake2b":
            return hashlib.blake2b(canonical).hexdigest()
        else:
            raise ValueError(f"Unknown algorithm: {self._algorithm}")
    
    def hash_short(self, data: Any, length: int = 16) -> str:
        """Produce truncated hash for display/short IDs.
        
        Args:
            data: Data to hash.
            length: Length of hash to return.
            
        Returns:
            Truncated hexadecimal hash.
        """
        return self.hash(data)[:length]
