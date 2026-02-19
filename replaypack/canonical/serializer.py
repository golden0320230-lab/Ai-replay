"""Canonical JSON serializer."""

from __future__ import annotations

import json
from typing import Any, Optional

from .normalizers import NormalizerRegistry


class CanonicalSerializer:
    """Deterministic JSON serializer.
    
    Produces byte-for-byte identical JSON output for
    logically equivalent data structures.
    """
    
    def __init__(self, normalizer_registry: Optional[NormalizerRegistry] = None):
        """Initialize serializer.
        
        Args:
            normalizer_registry: Registry of type normalizers.
        """
        self._normalizer = normalizer_registry or NormalizerRegistry()
    
    def serialize(self, data: Any) -> str:
        """Serialize data to canonical JSON string.
        
        Args:
            data: Data to serialize.
            
        Returns:
            Canonical JSON string.
        """
        # First normalize the data
        normalized = self._normalizer.normalize(data)
        
        # Then serialize with deterministic settings
        return json.dumps(
            normalized,
            sort_keys=True,           # Sort object keys
            separators=(',', ':'),    # Compact separators (no spaces)
            ensure_ascii=False,       # Allow Unicode characters
            check_circular=True,      # Safety check
        )
    
    def deserialize(self, data: str) -> Any:
        """Deserialize from JSON string.
        
        Args:
            data: JSON string to deserialize.
            
        Returns:
            Deserialized data.
        """
        return json.loads(data)
    
    def serialize_bytes(self, data: Any) -> bytes:
        """Serialize to canonical bytes (UTF-8 encoded).
        
        Args:
            data: Data to serialize.
            
        Returns:
            Canonical JSON as UTF-8 bytes.
        """
        return self.serialize(data).encode('utf-8')
