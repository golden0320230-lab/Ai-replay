"""Divergence type definitions."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, NamedTuple, Optional

from ..core.step import Step


class DivergenceType(Enum):
    """Types of divergence between runs."""
    NONE = "none"
    VALUE_MISMATCH = "value_mismatch"
    MISSING_STEP = "missing_step"
    EXTRA_STEP = "extra_step"
    REORDERED = "reordered"


class DivergencePoint(NamedTuple):
    """First point of divergence between two runs."""
    index: int
    type: DivergenceType
    step_a: Optional[Step]
    step_b: Optional[Step]
    hash_a: Optional[str]
    hash_b: Optional[str]
    context: Dict[str, Any]
    
    @property
    def has_divergence(self) -> bool:
        """Check if this represents an actual divergence."""
        return self.type != DivergenceType.NONE


class ComparisonResult:
    """Result of comparing two recordings."""
    
    def __init__(self):
        self.first_divergence: Optional[DivergencePoint] = None
        self.all_divergences: list[DivergencePoint] = []
        self.steps_compared = 0
        self.steps_matched = 0
    
    @property
    def is_identical(self) -> bool:
        """Check if recordings are identical."""
        return self.first_divergence is None
