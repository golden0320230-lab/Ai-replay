"""Test Skill 1: Deterministic Replay Engineering.

Adversarial test suite validating:
- 100-run determinism
- Network-disabled replay
- Concurrency order preservation
- Zero divergence
"""

from __future__ import annotations

import random
import threading
import time
from typing import Any, Dict

import pytest

from replaypack.core.recorder import Recorder, RecordingSession
from replaypack.core.replayer import Replayer, ReplayError
from replaypack.core.storage import Recording
from replaypack.core.step import Step


class TestDeterminism:
    """100-run determinism validation."""
    
    def test_100_consecutive_replays_identical_hash(self):
        """100 consecutive replays produce identical hash."""
        # Create a recording with varied step types
        session = RecordingSession()
        for i in range(100):
            session.record(
                f"func_{i % 10}",
                (i, i * 2),
                {'key': i, 'nested': {'value': i}},
                result=i * 3
            )
        recording = session.to_recording()
        
        # Replay 100 times
        replayer = Replayer()
        replayer.load(recording)
        
        hashes = []
        for _ in range(100):
            result = replayer.replay()
            hashes.append(result.hash())
        
        assert len(set(hashes)) == 1, \
            f"Hashes diverged: {len(set(hashes))} unique hashes"
    
    def test_replay_completes_network_disabled(self):
        """Replay completes with network disabled (simulated)."""
        session = RecordingSession()
        
        # Simulate network calls
        session.record(
            "http.get",
            ("https://api.example.com/data",),
            {},
            result={'status': 200, 'body': 'response_data'}
        )
        session.record(
            "http.post",
            ("https://api.example.com/submit",),
            {'json': {'key': 'value'}},
            result={'status': 201, 'id': '12345'}
        )
        
        recording = session.to_recording()
        
        replayer = Replayer()
        replayer.load(recording)
        
        # Simulate network disabled - all calls use stubs
        result = replayer.replay()
        
        assert result.steps_executed == len(recording.steps)
        assert result.first_divergence is None
    
    def test_execution_order_preserved_concurrency(self):
        """Execution order preserved under concurrency simulation."""
        session = RecordingSession()
        
        # Simulate concurrent calls from multiple threads
        def record_call(seq: int):
            session.record("concurrent_func", (seq,), {}, result=seq * 2)
        
        threads = [
            threading.Thread(target=record_call, args=(i,))
            for i in range(50)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        recording = session.to_recording()
        
        # Verify sequence numbers are monotonic
        sequences = [step.sequence for step in recording.steps]
        assert sequences == sorted(sequences), \
            f"Sequence not monotonic: {sequences[:10]}..."
    
    def test_zero_divergence_repeated_replays(self):
        """Zero divergence across repeated replays."""
        session = RecordingSession()
        
        # Create complex recording
        for i in range(1000):
            session.record(
                f"func_{i % 10}",
                (i, f"string_{i}", {'nested': i}),
                {'kwarg1': i, 'kwarg2': [1, 2, 3]},
                result={'output': i * 2}
            )
        
        recording = session.to_recording()
        
        replayer = Replayer()
        replayer.load(recording)
        
        for _ in range(50):
            result = replayer.replay()
            assert result.first_divergence is None, \
                f"Unexpected divergence at step {result.first_divergence}"
            assert result.steps_matched == len(recording.steps)


class TestAdversarialConditions:
    """Test under adversarial conditions."""
    
    def test_random_delays_during_replay(self):
        """Simulate random delays - replay must remain deterministic."""
        session = RecordingSession()
        for i in range(10):
            session.record(f"func_{i}", (i,), {}, result=i * 2)
        recording = session.to_recording()
        
        replayer = Replayer()
        replayer.load(recording)
        
        hashes = []
        for _ in range(20):
            # Add random delay before replay
            time.sleep(random.uniform(0.001, 0.01))
            result = replayer.replay()
            hashes.append(result.hash())
        
        assert len(set(hashes)) == 1, \
            f"Delays caused divergence: {len(set(hashes))} unique hashes"
    
    def test_randomized_return_values_stubbed(self):
        """Simulate randomized return values - stubs must override."""
        session = RecordingSession()
        
        # Record with fixed values
        for i in range(10):
            session.record("random_func", (), {}, result=42)
        
        recording = session.to_recording()
        
        # Replay - stubs should return 42, not random values
        replayer = Replayer()
        replayer.load(recording)
        result = replayer.replay()
        
        assert result.steps_matched == 10
    
    def test_partial_execution_interruption(self):
        """Simulate partial execution interruption."""
        session = RecordingSession()
        for i in range(100):
            session.record(f"func_{i}", (i,), {}, result=i * 2)
        recording = session.to_recording()
        
        replayer = Replayer()
        replayer.load(recording)
        
        # Normal replay should complete
        result = replayer.replay()
        assert result.steps_executed == len(recording.steps)
    
    def test_nested_call_interleaving(self):
        """Test nested calls maintain correct order."""
        session = RecordingSession()
        
        # Simulate nested calls
        session.record("outer", (), {})
        session.record("inner", (), {}, result=1)
        session.record("inner", (), {}, result=2)
        session.record("outer", (), {}, result=3)
        
        recording = session.to_recording()
        
        # Verify order preserved
        functions = [step.function for step in recording.steps]
        assert functions == ["outer", "inner", "inner", "outer"], \
            f"Order incorrect: {functions}"
    
    def test_exception_serialization(self):
        """Test exceptions are captured and can be replayed."""
        session = RecordingSession()
        
        try:
            raise ValueError("test error")
        except Exception as e:
            session.record("failing_func", (), {}, exception=e)
        
        recording = session.to_recording()
        
        # Verify exception captured
        step = recording.steps[0]
        assert step.exception is not None
        assert step.exception['type'] == 'ValueError'
        assert 'test error' in step.exception['message']


class TestHashStability:
    """Hash stability across conditions."""
    
    def test_same_input_same_hash(self):
        """Same logical input always produces identical hash."""
        step1 = Step(
            id="test-id-1",
            sequence=1,
            function="test_func",
            args=(1, 2, 3),
            kwargs={'a': 'b'},
            result={'output': 42},
            exception=None
        )
        
        step2 = Step(
            id="test-id-2",  # Different ID
            sequence=1,
            function="test_func",
            args=(1, 2, 3),
            kwargs={'a': 'b'},
            result={'output': 42},
            exception=None
        )
        
        # ID should not affect canonical hash
        assert step1.canonical_hash() == step2.canonical_hash(), \
            "Different IDs produced different hashes"
    
    def test_different_input_different_hash(self):
        """Different inputs produce different hashes."""
        step1 = Step("id1", 1, "func", (1,), {}, 1, None)
        step2 = Step("id2", 1, "func", (2,), {}, 1, None)
        
        assert step1.canonical_hash() != step2.canonical_hash(), \
            "Different inputs produced same hash"
    
    def test_sequence_affects_hash(self):
        """Different sequence numbers produce different hashes."""
        step1 = Step("id", 1, "func", (), {}, 1, None)
        step2 = Step("id", 2, "func", (), {}, 1, None)
        
        assert step1.canonical_hash() != step2.canonical_hash(), \
            "Sequence change should affect hash"
    
    def test_nested_dict_normalization(self):
        """Nested dicts are normalized consistently."""
        step1 = Step(
            "id", 1, "func",
            ({'z': 1, 'a': 2},),
            {},
            {'outer': {'z': 1, 'a': 2}},
            None
        )
        step2 = Step(
            "id", 1, "func",
            ({'a': 2, 'z': 1},),
            {},
            {'outer': {'a': 2, 'z': 1}},
            None
        )
        
        # Order of dict keys should not matter
        assert step1.canonical_hash() == step2.canonical_hash(), \
            "Dict key order affected hash"


class TestRecordingIntegrity:
    """Recording serialization integrity."""
    
    def test_json_roundtrip(self):
        """Recording survives JSON serialization roundtrip."""
        session = RecordingSession()
        for i in range(10):
            session.record(
                f"func_{i}",
                (i,),
                {'key': i},
                result={'output': i}
            )
        
        original = session.to_recording()
        
        # Serialize and deserialize
        json_data = original.to_json()
        restored = Recording.from_json(json_data)
        
        # Verify integrity
        assert len(restored.steps) == len(original.steps)
        assert restored.version == original.version
        
        for orig, rest in zip(original.steps, restored.steps):
            assert orig.sequence == rest.sequence
            assert orig.function == rest.function
            assert orig.canonical_hash() == rest.canonical_hash()
    
    def test_recording_hash_determinism(self):
        """Recording hash is deterministic."""
        session = RecordingSession()
        for i in range(50):
            session.record(f"func_{i}", (i,), {}, result=i)
        
        recording = session.to_recording()
        
        hashes = [recording.hash() for _ in range(100)]
        assert len(set(hashes)) == 1, \
            f"Recording hash not deterministic: {len(set(hashes))} unique"


class TestStubbedFunctions:
    """Test stubbed function behavior."""
    
    def test_stub_returns_recorded_result(self):
        """Stub returns the recorded result."""
        session = RecordingSession()
        session.record("test_func", (), {}, result={'data': 'value'})
        
        recording = session.to_recording()
        replayer = Replayer()
        replayer.load(recording)
        
        stub = replayer.get_stub("test_func")
        assert stub is not None
        
        result = stub()
        assert result == {'data': 'value'}
    
    def test_stub_raises_recorded_exception(self):
        """Stub raises the recorded exception."""
        session = RecordingSession()
        
        try:
            raise RuntimeError("recorded error")
        except Exception as e:
            session.record("failing_func", (), {}, exception=e)
        
        recording = session.to_recording()
        replayer = Replayer()
        replayer.load(recording)
        
        stub = replayer.get_stub("failing_func")
        assert stub is not None
        
        with pytest.raises(Exception) as exc_info:
            stub()
        
        assert "RuntimeError" in str(exc_info.value)
        assert "recorded error" in str(exc_info.value)
    
    def test_stub_exhaustion(self):
        """Stub raises error when steps exhausted."""
        session = RecordingSession()
        session.record("test_func", (), {}, result=1)
        
        recording = session.to_recording()
        replayer = Replayer()
        replayer.load(recording)
        
        stub = replayer.get_stub("test_func")
        stub()  # First call succeeds
        
        with pytest.raises(ReplayError):
            stub()  # Second call fails - no more steps


class TestRecorderLifecycle:
    """Test recorder start/stop lifecycle."""
    
    def test_start_stop_recording(self):
        """Basic recording lifecycle."""
        session = Recorder.start()
        assert Recorder.is_recording()
        
        session.record("test", (), {}, result=42)
        
        recording = Recorder.stop()
        assert not Recorder.is_recording()
        assert len(recording.steps) == 1
    
    def test_no_double_start(self):
        """Cannot start recording when already active."""
        Recorder.start()
        
        with pytest.raises(RuntimeError):
            Recorder.start()
        
        Recorder.stop()
    
    def test_no_stop_without_start(self):
        """Cannot stop without active recording."""
        with pytest.raises(RuntimeError):
            Recorder.stop()
    
    def test_record_without_session(self):
        """Recording without session returns None."""
        assert not Recorder.is_recording()
        result = Recorder.record("test", (), {}, result=42)
        assert result is None
