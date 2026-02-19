"""Cross-platform utilities for path normalization and encoding."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Union


def normalize_path(path: Union[str, Path]) -> str:
    """Normalize path for cross-platform compatibility.
    
    Args:
        path: Path to normalize.
        
    Returns:
        Normalized path string with forward slashes.
    """
    path_str = str(path)
    # Convert backslashes to forward slashes
    path_str = path_str.replace("\\", "/")
    # Remove redundant slashes
    while "//" in path_str:
        path_str = path_str.replace("//", "/")
    return path_str


def safe_encode(text: str, encoding: str = "utf-8") -> bytes:
    """Safely encode text to bytes.
    
    Args:
        text: Text to encode.
        encoding: Encoding to use.
        
    Returns:
        Encoded bytes.
    """
    return text.encode(encoding, errors="replace")


def safe_decode(data: bytes, encoding: str = "utf-8") -> str:
    """Safely decode bytes to text.
    
    Args:
        data: Bytes to decode.
        encoding: Encoding to use.
        
    Returns:
        Decoded string.
    """
    return data.decode(encoding, errors="replace")
