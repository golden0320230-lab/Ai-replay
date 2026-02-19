"""Type-specific normalizers for canonical form."""

from __future__ import annotations

import math
from datetime import datetime
from decimal import Decimal, ROUND_HALF_EVEN
from typing import Any, Callable, Dict, List, Optional


class FloatNormalizer:
    """Normalize floats to deterministic representation.
    
    Handles NaN, Infinity, and precision consistently.
    """
    
    def __init__(self, precision: int = 15):
        """Initialize with decimal precision.
        
        Args:
            precision: Decimal places to preserve (default 15 for double precision).
        """
        self.precision = precision
    
    def normalize(self, value: float) -> float:
        """Normalize float to canonical form.
        
        Args:
            value: Float to normalize.
            
        Returns:
            Normalized float.
        """
        # Handle special values
        if math.isnan(value):
            return float('nan')  # Standard NaN
        if math.isinf(value):
            return float('inf') if value > 0 else float('-inf')
        
        # Round to specified precision using banker's rounding
        d = Decimal(str(value))
        quantized = d.quantize(
            Decimal(10) ** -self.precision,
            rounding=ROUND_HALF_EVEN
        )
        return float(quantized)
    
    @staticmethod
    def is_special(value: float) -> bool:
        """Check if float is a special value (NaN, Inf)."""
        return math.isnan(value) or math.isinf(value)


class TimestampNormalizer:
    """Normalize timestamps to deterministic representation."""
    
    def __init__(self, unit: str = "ns"):
        """Initialize with time unit.
        
        Args:
            unit: Time unit - "ns" (nanoseconds), "us" (microseconds), 
                  "ms" (milliseconds), or "s" (seconds).
        """
        self.unit = unit
        self.multipliers = {
            "s": 1,
            "ms": 1_000,
            "us": 1_000_000,
            "ns": 1_000_000_000,
        }
    
    def normalize(self, value: datetime) -> int:
        """Normalize datetime to integer timestamp.
        
        Args:
            value: Datetime to normalize.
            
        Returns:
            Integer timestamp in specified units.
        """
        # Convert to UTC timestamp
        if value.tzinfo is not None:
            timestamp = value.timestamp()
        else:
            # Assume UTC for naive datetimes
            timestamp = value.timestamp()
        
        # Convert to specified unit
        multiplier = self.multipliers.get(self.unit, 1_000_000_000)
        return int(timestamp * multiplier)
    
    def normalize_ns(self, value: int) -> int:
        """Normalize nanosecond timestamp (pass-through with validation).
        
        Args:
            value: Nanosecond timestamp.
            
        Returns:
            Validated nanosecond timestamp.
        """
        # Ensure it's a positive integer
        if not isinstance(value, int):
            value = int(value)
        return max(0, value)


class StringNormalizer:
    """Normalize strings for canonical form."""
    
    def __init__(self, encoding: str = "utf-8"):
        """Initialize with encoding.
        
        Args:
            encoding: String encoding to use.
        """
        self.encoding = encoding
    
    def normalize(self, value: str) -> str:
        """Normalize string to canonical form.
        
        Handles Unicode normalization (NFC) to ensure
        different representations of same character
        produce identical output.
        
        Args:
            value: String to normalize.
            
        Returns:
            Normalized string.
        """
        import unicodedata
        
        # Normalize to NFC (Canonical Decomposition followed by Canonical Composition)
        normalized = unicodedata.normalize('NFC', value)
        
        return normalized


class BinaryNormalizer:
    """Normalize binary data for canonical form."""
    
    def __init__(self, max_bytes: int = 10_485_760):  # 10MB default
        """Initialize with size limit.
        
        Args:
            max_bytes: Maximum bytes to include directly (larger = hex hash).
        """
        self.max_bytes = max_bytes
    
    def normalize(self, value: bytes) -> str:
        """Normalize binary data to canonical form.
        
        Small binary data is base64-encoded.
        Large binary data is replaced with hash.
        
        Args:
            value: Binary data to normalize.
            
        Returns:
            Normalized representation (base64 or hash).
        """
        import base64
        import hashlib
        
        if len(value) <= self.max_bytes:
            # Encode small data as base64
            return "base64:" + base64.b64encode(value).decode('ascii')
        else:
            # Large data: use hash
            data_hash = hashlib.sha256(value).hexdigest()[:32]
            return f"hash:sha256:{data_hash}:size:{len(value)}"


class NormalizerRegistry:
    """Registry of type normalizers."""
    
    def __init__(self):
        self._normalizers: Dict[type, Callable[[Any], Any]] = {}
        self._float_normalizer = FloatNormalizer()
        self._timestamp_normalizer = TimestampNormalizer()
        self._string_normalizer = StringNormalizer()
        self._binary_normalizer = BinaryNormalizer()
    
    def register(self, type_: type, normalizer: Callable[[Any], Any]) -> None:
        """Register a normalizer for a type."""
        self._normalizers[type_] = normalizer
    
    def normalize(self, value: Any) -> Any:
        """Normalize a value using appropriate normalizer.
        
        Args:
            value: Value to normalize.
            
        Returns:
            Normalized value.
        """
        # Handle None
        if value is None:
            return None
        
        # Handle booleans (must check before int)
        if isinstance(value, bool):
            return value
        
        # Handle integers
        if isinstance(value, int):
            return value
        
        # Handle floats
        if isinstance(value, float):
            return self._float_normalizer.normalize(value)
        
        # Handle strings
        if isinstance(value, str):
            return self._string_normalizer.normalize(value)
        
        # Handle bytes
        if isinstance(value, bytes):
            return self._binary_normalizer.normalize(value)
        
        # Handle datetime
        if isinstance(value, datetime):
            return self._timestamp_normalizer.normalize(value)
        
        # Handle lists
        if isinstance(value, (list, tuple)):
            return [self.normalize(item) for item in value]
        
        # Handle dicts
        if isinstance(value, dict):
            # Sort keys and normalize values
            return {
                self.normalize(k): self.normalize(v)
                for k, v in sorted(value.items())
            }
        
        # Handle registered custom types
        for type_, normalizer in self._normalizers.items():
            if isinstance(value, type_):
                return normalizer(value)
        
        # Fallback: convert to string
        return str(value)
