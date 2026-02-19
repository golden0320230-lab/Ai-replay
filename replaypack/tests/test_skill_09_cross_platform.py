"""Test Skill 9: Cross-Platform Robustness.

Tests for path normalization, encoding safety, hash stability.
"""

import sys

import pytest

from replaypack.cross_platform import normalize_path, safe_encode, safe_decode
from replaypack.canonical import CanonicalHasher


class TestPathNormalization:
    """Test path normalization."""
    
    def test_normalizes_backslashes(self):
        """Backslashes are converted to forward slashes."""
        path = "dir\\subdir\\file.txt"
        result = normalize_path(path)
        assert result == "dir/subdir/file.txt"
    
    def test_removes_redundant_slashes(self):
        """Redundant slashes are removed."""
        path = "dir//subdir///file.txt"
        result = normalize_path(path)
        assert result == "dir/subdir/file.txt"


class TestEncodingSafety:
    """Test encoding safety."""
    
    def test_safe_encode_utf8(self):
        """UTF-8 encoding works."""
        text = "Hello 世界"
        result = safe_encode(text)
        assert isinstance(result, bytes)
    
    def test_safe_decode_utf8(self):
        """UTF-8 decoding works."""
        data = "Hello 世界".encode('utf-8')
        result = safe_decode(data)
        assert result == "Hello 世界"
    
    def test_handles_invalid_bytes(self):
        """Invalid bytes are handled gracefully."""
        data = b"\xff\xfe invalid"
        result = safe_decode(data)
        assert isinstance(result, str)


class TestHashStability:
    """Test hash stability across platforms."""
    
    def test_hash_identical_for_same_data(self):
        """Same data produces identical hash."""
        hasher = CanonicalHasher()
        data = {"key": "value", "number": 42}
        
        hash1 = hasher.hash(data)
        hash2 = hasher.hash(data)
        
        assert hash1 == hash2
    
    def test_hash_stable_with_different_key_order(self):
        """Hash is stable regardless of dict key order."""
        hasher = CanonicalHasher()
        
        data1 = {"a": 1, "b": 2}
        data2 = {"b": 2, "a": 1}
        
        hash1 = hasher.hash(data1)
        hash2 = hasher.hash(data2)
        
        assert hash1 == hash2
