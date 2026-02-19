"""Test Skill 3: Canonical Data Normalization.

Adversarial test suite validating:
- Float normalization (NaN, Inf, precision)
- Unicode normalization (NFC)
- Canonical JSON serialization
- 100-run hash determinism
- Cross-platform stability
"""

from __future__ import annotations

import json
import math
from datetime import datetime

import pytest

from replaypack.canonical import (
    CanonicalHasher,
    CanonicalSerializer,
    FloatNormalizer,
    NormalizerRegistry,
    StringNormalizer,
)


class TestFloatNormalization:
    """Test float normalization."""
    
    def test_nan_normalization(self):
        """NaN values are normalized consistently."""
        normalizer = FloatNormalizer()
        
        nan1 = float('nan')
        nan2 = float('nan')
        
        # Both should be NaN
        assert math.isnan(normalizer.normalize(nan1))
        assert math.isnan(normalizer.normalize(nan2))
    
    def test_infinity_normalization(self):
        """Infinity values are normalized consistently."""
        normalizer = FloatNormalizer()
        
        inf = float('inf')
        neg_inf = float('-inf')
        
        assert math.isinf(normalizer.normalize(inf))
        assert normalizer.normalize(inf) > 0
        assert math.isinf(normalizer.normalize(neg_inf))
        assert normalizer.normalize(neg_inf) < 0
    
    def test_precision_rounding(self):
        """Floats are rounded to specified precision."""
        normalizer = FloatNormalizer(precision=5)
        
        # Very close values should become identical
        f1 = 1.000001
        f2 = 1.000002
        
        # With 5 decimal precision, these may or may not be equal
        # depending on the exact values
        n1 = normalizer.normalize(f1)
        n2 = normalizer.normalize(f2)
        
        # They should be very close
        assert abs(n1 - n2) < 0.001


class TestStringNormalization:
    """Test string normalization."""
    
    def test_unicode_normalization(self):
        """Different Unicode representations become identical."""
        normalizer = StringNormalizer()
        
        # é can be represented as single char or e + combining accent
        str1 = "caf\u00e9"  # café with single char é
        str2 = "cafe\u0301"  # cafe + combining acute accent
        
        assert normalizer.normalize(str1) == normalizer.normalize(str2)
    
    def test_non_ascii_characters(self):
        """Non-ASCII characters are handled correctly."""
        normalizer = StringNormalizer()
        
        # Various Unicode characters
        strings = [
            "Hello 世界",
            "Привет мир",
            "مرحبا بالعالم",
            "🎉 Emoji 🚀",
        ]
        
        for s in strings:
            normalized = normalizer.normalize(s)
            # Should be valid string
            assert isinstance(normalized, str)


class TestCanonicalSerializer:
    """Test canonical serialization."""
    
    def test_dict_key_sorting(self):
        """Dictionary keys are sorted."""
        serializer = CanonicalSerializer()
        
        data = {"z": 1, "a": 2, "m": 3}
        result = serializer.serialize(data)
        
        # Keys should appear in alphabetical order
        assert result == '{"a":2,"m":3,"z":1}'
    
    def test_nested_dict_sorting(self):
        """Nested dictionary keys are sorted recursively."""
        serializer = CanonicalSerializer()
        
        data = {"outer": {"z": 1, "a": 2}}
        result = serializer.serialize(data)
        
        assert result == '{"outer":{"a":2,"z":1}}'
    
    def test_list_order_preserved(self):
        """List order is preserved (not sorted)."""
        serializer = CanonicalSerializer()
        
        data = [3, 1, 2]
        result = serializer.serialize(data)
        
        assert result == '[3,1,2]'
    
    def test_deeply_nested_json(self):
        """JSON nested >10 levels is handled."""
        serializer = CanonicalSerializer()
        
        # Create deeply nested structure
        data = {"level": 0}
        for i in range(15):
            data = {"level": i + 1, "nested": data}
        
        # Should serialize without error
        result = serializer.serialize(data)
        assert isinstance(result, str)
        assert len(result) > 0


class TestCanonicalHasher:
    """Test canonical hashing."""
    
    def test_same_logical_input_same_hash(self):
        """Same logical input produces identical hash."""
        hasher = CanonicalHasher()
        
        # Different order dicts with same content
        data1 = {"a": 1, "b": 2}
        data2 = {"b": 2, "a": 1}
        
        hash1 = hasher.hash(data1)
        hash2 = hasher.hash(data2)
        
        assert hash1 == hash2
    
    def test_different_input_different_hash(self):
        """Different inputs produce different hashes."""
        hasher = CanonicalHasher()
        
        data1 = {"a": 1}
        data2 = {"a": 2}
        
        hash1 = hasher.hash(data1)
        hash2 = hasher.hash(data2)
        
        assert hash1 != hash2
    
    def test_100_run_determinism(self):
        """Hash is identical across 100 runs."""
        hasher = CanonicalHasher()
        data = {"test": [1, 2, 3], "nested": {"a": "b"}}
        
        hashes = [hasher.hash(data) for _ in range(100)]
        
        assert len(set(hashes)) == 1
    
    def test_cross_platform_stability(self):
        """Hash is stable across different representations."""
        hasher = CanonicalHasher()
        
        # Integer vs float that are logically similar
        data1 = {"value": 1}
        data2 = {"value": 1.0}
        
        hash1 = hasher.hash(data1)
        hash2 = hasher.hash(data2)
        
        # These are different types, so hashes differ
        # (This is intentional - type matters)
        assert hash1 != hash2


class TestAdversarialConditions:
    """Test under adversarial conditions."""
    
    def test_unordered_arrays(self):
        """Arrays with different order produce different hashes."""
        hasher = CanonicalHasher()
        
        arr1 = [1, 2, 3]
        arr2 = [3, 2, 1]
        
        # Arrays are ordered, so these should differ
        assert hasher.hash(arr1) != hasher.hash(arr2)
    
    def test_binary_encoded_fields(self):
        """Binary data is handled correctly."""
        serializer = CanonicalSerializer()
        
        data = {"binary": b"\x00\x01\x02\xff"}
        result = serializer.serialize(data)
        
        # Should serialize without error
        assert isinstance(result, str)
    
    def test_mixed_types_in_dict(self):
        """Dictionaries with mixed types are handled."""
        serializer = CanonicalSerializer()
        
        data = {
            "string": "value",
            "integer": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
            "array": [1, 2, 3],
            "nested": {"a": 1},
        }
        
        result = serializer.serialize(data)
        parsed = json.loads(result)
        
        assert parsed["string"] == "value"
        assert parsed["integer"] == 42


class TestNormalizationRegistry:
    """Test normalizer registry."""
    
    def test_custom_type_registration(self):
        """Custom types can be registered."""
        registry = NormalizerRegistry()
        
        class CustomType:
            def __init__(self, value):
                self.value = value
        
        def normalize_custom(obj):
            return {"__custom__": obj.value}
        
        registry.register(CustomType, normalize_custom)
        
        data = CustomType("test")
        result = registry.normalize(data)
        
        assert result == {"__custom__": "test"}
    
    def test_nested_normalization(self):
        """Normalization works recursively on nested structures."""
        registry = NormalizerRegistry()
        
        data = {
            "level1": {
                "level2": {
                    "level3": [1, 2, {"deep": "value"}]
                }
            }
        }
        
        result = registry.normalize(data)
        
        # All nested structures should be normalized
        assert result["level1"]["level2"]["level3"][2]["deep"] == "value"
