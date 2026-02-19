"""Divergence detection engine."""

from __future__ import annotations

from typing import Optional

from ..core.step import Step
from ..core.storage import Recording
from ..canonical import CanonicalHasher
from .types import DivergencePoint, DivergenceType, ComparisonResult


class DivergenceDetector:
    """Detects divergence between two recordings.
    
    Uses step-level hashing for O(n) comparison with
    early termination on first mismatch.
    """
    
    def __init__(self, hasher: Optional[CanonicalHasher] = None):
        """Initialize detector.
        
        Args:
            hasher: Canonical hasher for step hashing.
        """
        self._hasher = hasher or CanonicalHasher()
    
    def detect(self, run_a: Recording, run_b: Recording) -> DivergencePoint:
        """Detect first divergence between two runs.
        
        Args:
            run_a: First recording.
            run_b: Second recording.
            
        Returns:
            DivergencePoint with first mismatch details.
            Returns NONE type if runs are identical.
        """
        result = self._compare_runs(run_a, run_b, stop_on_first=True)
        
        if result.first_divergence:
            return result.first_divergence
        
        # Check if runs have different lengths
        len_a = len(run_a.steps)
        len_b = len(run_b.steps)
        
        if len_a > len_b:
            return DivergencePoint(
                index=len_b,
                type=DivergenceType.MISSING_STEP,
                step_a=run_a.steps[len_b] if len_b < len_a else None,
                step_b=None,
                hash_a=self._hash_step(run_a.steps[len_b]) if len_b < len_a else None,
                hash_b=None,
                context={"reason": "Run A has extra steps"}
            )
        elif len_b > len_a:
            return DivergencePoint(
                index=len_a,
                type=DivergenceType.EXTRA_STEP,
                step_a=None,
                step_b=run_b.steps[len_a] if len_a < len_b else None,
                hash_a=None,
                hash_b=self._hash_step(run_b.steps[len_a]) if len_a < len_b else None,
                context={"reason": "Run B has extra steps"}
            )
        
        # No divergence found
        return DivergencePoint(
            index=-1,
            type=DivergenceType.NONE,
            step_a=None,
            step_b=None,
            hash_a=None,
            hash_b=None,
            context={}
        )
    
    def compare_all(self, run_a: Recording, run_b: Recording) -> ComparisonResult:
        """Compare all steps and return detailed result.
        
        Args:
            run_a: First recording.
            run_b: Second recording.
            
        Returns:
            ComparisonResult with all divergences.
        """
        return self._compare_runs(run_a, run_b, stop_on_first=False)
    
    def _compare_runs(
        self,
        run_a: Recording,
        run_b: Recording,
        stop_on_first: bool
    ) -> ComparisonResult:
        """Internal comparison method.
        
        Args:
            run_a: First recording.
            run_b: Second recording.
            stop_on_first: If True, stop at first divergence.
            
        Returns:
            ComparisonResult.
        """
        result = ComparisonResult()
        
        # Get step iterators
        steps_a = iter(run_a.steps)
        steps_b = iter(run_b.steps)
        
        index = 0
        while True:
            try:
                step_a = next(steps_a)
            except StopIteration:
                step_a = None
            
            try:
                step_b = next(steps_b)
            except StopIteration:
                step_b = None
            
            # Both exhausted - comparison complete
            if step_a is None and step_b is None:
                break
            
            result.steps_compared += 1
            
            # Compare steps
            divergence = self._compare_steps(index, step_a, step_b)
            
            if divergence.type != DivergenceType.NONE:
                result.all_divergences.append(divergence)
                
                if result.first_divergence is None:
                    result.first_divergence = divergence
                
                if stop_on_first:
                    return result
            else:
                result.steps_matched += 1
            
            index += 1
        
        return result
    
    def _compare_steps(
        self,
        index: int,
        step_a: Optional[Step],
        step_b: Optional[Step]
    ) -> DivergencePoint:
        """Compare two steps.
        
        Args:
            index: Step index.
            step_a: Step from run A (may be None).
            step_b: Step from run B (may be None).
            
        Returns:
            DivergencePoint.
        """
        # Handle missing steps
        if step_a is None and step_b is not None:
            return DivergencePoint(
                index=index,
                type=DivergenceType.EXTRA_STEP,
                step_a=None,
                step_b=step_b,
                hash_a=None,
                hash_b=self._hash_step(step_b),
                context={"reason": "Step missing in run A"}
            )
        
        if step_a is not None and step_b is None:
            return DivergencePoint(
                index=index,
                type=DivergenceType.MISSING_STEP,
                step_a=step_a,
                step_b=None,
                hash_a=self._hash_step(step_a),
                hash_b=None,
                context={"reason": "Step missing in run B"}
            )
        
        # Both steps present - compare hashes
        hash_a = self._hash_step(step_a)
        hash_b = self._hash_step(step_b)
        
        if hash_a == hash_b:
            return DivergencePoint(
                index=index,
                type=DivergenceType.NONE,
                step_a=step_a,
                step_b=step_b,
                hash_a=hash_a,
                hash_b=hash_b,
                context={}
            )
        
        # Hashes differ - this is a value mismatch
        # (Removed the reordered check as it was incorrectly flagging result differences)
        return DivergencePoint(
            index=index,
            type=DivergenceType.VALUE_MISMATCH,
            step_a=step_a,
            step_b=step_b,
            hash_a=hash_a,
            hash_b=hash_b,
            context={
                "reason": "Step values differ",
                "function_a": step_a.function if step_a else None,
                "function_b": step_b.function if step_b else None,
            }
        )
    
    def _hash_step(self, step: Optional[Step]) -> Optional[str]:
        """Hash a step using canonical hasher.
        
        Args:
            step: Step to hash.
            
        Returns:
            Hash string or None.
        """
        if step is None:
            return None
        
        # Use step's canonical hash if available
        if hasattr(step, 'canonical_hash'):
            return step.canonical_hash()
        
        # Fallback: hash the step dict
        step_dict = {
            'sequence': step.sequence,
            'function': step.function,
            'args': step.args,
            'kwargs': step.kwargs,
            'result': step.result,
            'exception': step.exception,
        }
        return self._hasher.hash(step_dict)
    
    def _steps_functionally_equivalent(self, step_a: Step, step_b: Step) -> bool:
        """Check if steps are functionally equivalent (same function/args).
        
        Args:
            step_a: First step.
            step_b: Second step.
            
        Returns:
            True if steps are functionally equivalent.
        """
        # Check function name
        if step_a.function != step_b.function:
            return False
        
        # Check args (simplified - could be more sophisticated)
        if step_a.args != step_b.args:
            return False
        
        return True
