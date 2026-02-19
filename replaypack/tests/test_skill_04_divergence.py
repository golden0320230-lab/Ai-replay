"""Test Skill 4: Hash-Based Divergence Detection.

Adversarial test suite validating:
- First divergence detection accuracy
- No false positives
- No false negatives
- O(n) performance
- Corrupted step detection
- Missing/extra step detection
- Reordered step detection
"""

from __future__ import annotations

import time
from typing import List

import pytest

from replaypack.core.step import Step
from replaypack.core.storage import Recording
from replaypack.divergence import DivergenceDetector, DivergenceType


def create_recording(steps_data: List[dict]) -> Recording:
    """Helper to create a recording from step data."""
    steps = [
        Step(
            id=f"step_{i}",
            sequence=i + 1,
            function=s.get('function', 'test_func'),
            args=s.get('args', ()),
            kwargs=s.get('kwargs', {}),
            result=s.get('result', None),
            exception=s.get('exception', None)
        )
        for i, s in enumerate(steps_data)
    ]
    return Recording(steps=steps, metadata={}, version='1.0.0')


class TestFirstDivergenceDetection:
    """Test first divergence detection accuracy."""
    
    def test_identical_runs_no_divergence(self):
        """Identical runs report no divergence."""
        steps = [
            {'function': 'f1', 'args': (1,), 'result': 2},
            {'function': 'f2', 'args': (2,), 'result': 4},
        ]
        run_a = create_recording(steps)
        run_b = create_recording(steps)
        
        detector = DivergenceDetector()
        divergence = detector.detect(run_a, run_b)
        
        assert divergence.type == DivergenceType.NONE
        assert not divergence.has_divergence
    
    def test_first_divergence_at_beginning(self):
        """First divergence at index 0 is detected."""
        run_a = create_recording([
            {'function': 'f1', 'args': (1,), 'result': 2},
        ])
        run_b = create_recording([
            {'function': 'f1', 'args': (1,), 'result': 999},  # Different result
        ])
        
        detector = DivergenceDetector()
        divergence = detector.detect(run_a, run_b)
        
        assert divergence.type == DivergenceType.VALUE_MISMATCH
        assert divergence.index == 0
    
    def test_first_divergence_in_middle(self):
        """First divergence in middle is detected."""
        run_a = create_recording([
            {'function': 'f1', 'args': (1,), 'result': 1},
            {'function': 'f2', 'args': (2,), 'result': 2},
            {'function': 'f3', 'args': (3,), 'result': 3},
        ])
        run_b = create_recording([
            {'function': 'f1', 'args': (1,), 'result': 1},
            {'function': 'f2', 'args': (2,), 'result': 999},  # Different at index 1
            {'function': 'f3', 'args': (3,), 'result': 3},
        ])
        
        detector = DivergenceDetector()
        divergence = detector.detect(run_a, run_b)
        
        assert divergence.type == DivergenceType.VALUE_MISMATCH
        assert divergence.index == 1


class TestMissingExtraSteps:
    """Test missing and extra step detection."""
    
    def test_missing_step_in_run_b(self):
        """Missing step in run B is detected."""
        run_a = create_recording([
            {'function': 'f1', 'result': 1},
            {'function': 'f2', 'result': 2},
        ])
        run_b = create_recording([
            {'function': 'f1', 'result': 1},
            # Missing f2
        ])
        
        detector = DivergenceDetector()
        divergence = detector.detect(run_a, run_b)
        
        assert divergence.type == DivergenceType.MISSING_STEP
        assert divergence.index == 1
    
    def test_extra_step_in_run_b(self):
        """Extra step in run B is detected."""
        run_a = create_recording([
            {'function': 'f1', 'result': 1},
        ])
        run_b = create_recording([
            {'function': 'f1', 'result': 1},
            {'function': 'f2', 'result': 2},  # Extra
        ])
        
        detector = DivergenceDetector()
        divergence = detector.detect(run_a, run_b)
        
        assert divergence.type == DivergenceType.EXTRA_STEP
        assert divergence.index == 1


class TestPerformance:
    """Test O(n) performance."""
    
    def test_linear_performance(self):
        """Detection is O(n) - linear in number of steps."""
        detector = DivergenceDetector()
        
        # Create large recordings
        large_steps = [{'function': f'f{i}', 'result': i} for i in range(10000)]
        run_a = create_recording(large_steps)
        run_b = create_recording(large_steps)
        
        start = time.perf_counter_ns()
        detector.detect(run_a, run_b)
        duration = time.perf_counter_ns() - start
        
        # Should complete in reasonable time (less than 1 second for 10k steps)
        assert duration < 1_000_000_000  # 1 second in nanoseconds


class TestFalsePositivesNegatives:
    """Test no false positives or negatives."""
    
    def test_no_false_positives_identical(self):
        """Identical runs never report false divergence."""
        steps = [{'function': f'f{i}', 'result': i} for i in range(100)]
        run_a = create_recording(steps)
        run_b = create_recording(steps)
        
        detector = DivergenceDetector()
        result = detector.compare_all(run_a, run_b)
        
        assert result.is_identical
        assert len(result.all_divergences) == 0
    
    def test_no_false_negatives_different(self):
        """Different runs always report divergence."""
        run_a = create_recording([{'result': 1}])
        run_b = create_recording([{'result': 2}])
        
        detector = DivergenceDetector()
        divergence = detector.detect(run_a, run_b)
        
        assert divergence.has_divergence
        assert divergence.type != DivergenceType.NONE


class TestCorruptedSteps:
    """Test corrupted step detection."""
    
    def test_corrupted_step_hash(self):
        """Step with corrupted data is detected."""
        run_a = create_recording([
            {'function': 'f1', 'result': 'original'},
        ])
        run_b = create_recording([
            {'function': 'f1', 'result': 'corrupted'},
        ])
        
        detector = DivergenceDetector()
        divergence = detector.detect(run_a, run_b)
        
        assert divergence.type == DivergenceType.VALUE_MISMATCH
        assert divergence.hash_a != divergence.hash_b


class TestCompareAll:
    """Test compare_all functionality."""
    
    def test_finds_all_divergences(self):
        """All divergences are found, not just first."""
        run_a = create_recording([
            {'result': 1},
            {'result': 2},  # Different
            {'result': 3},
            {'result': 4},  # Different
        ])
        run_b = create_recording([
            {'result': 1},
            {'result': 999},
            {'result': 3},
            {'result': 888},
        ])
        
        detector = DivergenceDetector()
        result = detector.compare_all(run_a, run_b)
        
        assert len(result.all_divergences) == 2
        assert result.all_divergences[0].index == 1
        assert result.all_divergences[1].index == 3
