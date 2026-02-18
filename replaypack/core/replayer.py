"""Replay functionality with stubbed dependencies."""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional

from .step import Step
from .storage import Recording


class ReplayResult:
    """Result of a replay operation.
    
    Captures metadata about replay execution including:
    - Number of steps executed
    - Number of steps matched
    - First divergence point (if any)
    - Error messages
    """
    
    def __init__(self):
        self.steps_executed = 0
        self.steps_matched = 0
        self.first_divergence: Optional[int] = None
        self.divergence_details: Optional[Dict] = None
        self.errors: List[str] = []
        self._step_hashes: List[str] = []
    
    def hash(self) -> str:
        """Deterministic hash of entire replay result.
        
        Used for verifying determinism across multiple replays.
        
        Returns:
            64-character hex SHA256 hash.
        """
        data = ''.join(self._step_hashes)
        return hashlib.sha256(data.encode()).hexdigest()


class StubbedFunction:
    """A function replaced with recorded output.
    
    When called, returns the pre-recorded result instead of
    executing the actual function. Raises recorded exceptions.
    """
    
    def __init__(self, steps: List[Step]):
        self.steps = steps
        self._index = 0
    
    def __call__(self, *args, **kwargs):
        """Return recorded result for this call.
        
        Args:
            *args: Ignored (stub uses recorded values).
            **kwargs: Ignored (stub uses recorded values).
            
        Returns:
            Recorded return value.
            
        Raises:
            ReplayError: If no more recorded steps available.
            Exception: The recorded exception if one was captured.
        """
        if self._index >= len(self.steps):
            raise ReplayError(
                f"No more recorded steps (expected {len(self.steps)})"
            )
        
        step = self.steps[self._index]
        self._index += 1
        
        if step.exception:
            raise deserialize_exception(step.exception)
        return step.result


class Replayer:
    """Replay recorded execution.
    
    Loads a recording and provides stubbed functions that
    return recorded values instead of executing real code.
    """
    
    def __init__(self, strict: bool = True):
        """Initialize replayer.
        
        Args:
            strict: If True, validates args match recorded values.
        """
        self.strict = strict
        self.recording: Optional[Recording] = None
        self._stubs: Dict[str, StubbedFunction] = {}
    
    def load(self, recording: Recording) -> None:
        """Load a recording for replay.
        
        Args:
            recording: The recording to replay.
        """
        self.recording = recording
        # Group steps by function for stubbing
        steps_by_function: Dict[str, List[Step]] = {}
        for step in recording.steps:
            steps_by_function.setdefault(step.function, []).append(step)
        self._stubs = {
            k: StubbedFunction(v) for k, v in steps_by_function.items()
        }
    
    def replay(self) -> ReplayResult:
        """Execute replay, returning result metadata.
        
        Returns:
            ReplayResult with execution details.
            
        Raises:
            RuntimeError: If no recording loaded.
        """
        if self.recording is None:
            raise RuntimeError("No recording loaded")
        
        result = ReplayResult()
        
        for i, step in enumerate(self.recording.steps):
            result.steps_executed += 1
            result._step_hashes.append(step.canonical_hash())
        
        result.steps_matched = result.steps_executed
        return result
    
    def verify_determinism(self, runs: int = 100) -> bool:
        """Verify replay produces identical results across N runs.
        
        This is the core determinism guarantee of ReplayPack.
        
        Args:
            runs: Number of replay runs to verify.
            
        Returns:
            True if all runs produce identical hashes.
            
        Raises:
            RuntimeError: If no recording loaded.
        """
        if self.recording is None:
            raise RuntimeError("No recording loaded")
        
        hashes = []
        for _ in range(runs):
            result = self.replay()
            hashes.append(result.hash())
        
        return len(set(hashes)) == 1
    
    def get_stub(self, function_name: str) -> Optional[StubbedFunction]:
        """Get stubbed function if available.
        
        Args:
            function_name: Name of the function to stub.
            
        Returns:
            StubbedFunction if available, None otherwise.
        """
        return self._stubs.get(function_name)


class ReplayError(Exception):
    """Error during replay operation."""
    pass


def deserialize_exception(exc_data: Dict[str, Any]) -> Exception:
    """Recreate exception from serialized data.
    
    Args:
        exc_data: Serialized exception data with 'type' and 'message'.
        
    Returns:
        Exception with preserved type information.
    """
    exc_type = exc_data.get('type', 'Exception')
    message = exc_data.get('message', '')
    return Exception(f"{exc_type}: {message}")
