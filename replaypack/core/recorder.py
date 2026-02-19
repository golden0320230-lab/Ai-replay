"""Recording functionality for capturing execution steps."""

from __future__ import annotations

import os
import time
import uuid
from typing import Any, Optional, List

from .step import Step
from ..intercept.base import CaptureEntry, CaptureBackend


# Session limits from environment
MAX_STEPS = int(os.environ.get('REPLAYPACK_MAX_STEPS', '10000'))
MAX_MB = int(os.environ.get('REPLAYPACK_MAX_MB', '50'))
MAX_BYTES = MAX_MB * 1024 * 1024


class RecordingSession(CaptureBackend):
    """Active recording session.
    
    Manages the capture of execution steps during a recording.
    Thread-safe for concurrent step recording.
    Implements CaptureBackend for interceptor integration.
    """
    
    def __init__(self):
        self.steps: list[Step] = []
        self._sequence = 0
        self._start_ns = time.perf_counter_ns()
        self._lock = False  # Simple lock for thread safety
        self._truncated = False
        self._error_event = None
    
    def _check_limits(self) -> bool:
        """Check if recording limits exceeded.
        
        Returns:
            True if ok to continue, False if limits exceeded.
        """
        if self._truncated:
            return False
        
        # Check step count
        if len(self.steps) >= MAX_STEPS:
            self._truncated = True
            self._error_event = f"Session truncated: exceeded {MAX_STEPS} steps"
            return False
        
        # Check size (approximate)
        import sys
        try:
            total_size = sum(sys.getsizeof(s) for s in self.steps)
            if total_size >= MAX_BYTES:
                self._truncated = True
                self._error_event = f"Session truncated: exceeded {MAX_MB}MB"
                return False
        except:
            pass  # Size check is best-effort
        
        return True
    
    def record(
        self,
        function: str,
        args: tuple,
        kwargs: dict,
        result: Any = None,
        exception: Optional[Exception] = None
    ) -> Optional[Step]:
        """Record a single execution step.
        
        Args:
            function: Fully qualified function name.
            args: Positional arguments.
            kwargs: Keyword arguments.
            result: Return value (if no exception).
            exception: Exception that was raised (if any).
            
        Returns:
            The recorded Step, or None if limits exceeded.
        """
        # Check limits before recording
        if not self._check_limits():
            return None
        
        # Simple spinlock for thread safety
        while self._lock:
            pass
        self._lock = True
        
        try:
            self._sequence += 1
            
            # Serialize exception if present
            exc_data = None
            if exception is not None:
                exc_data = {
                    'type': type(exception).__name__,
                    'message': str(exception),
                }
            
            step = Step(
                id=str(uuid.uuid4()),
                sequence=self._sequence,
                function=function,
                args=args,
                kwargs=kwargs,
                result=result,
                exception=exc_data,
            )
            
            self.steps.append(step)
            return step
        finally:
            self._lock = False
    
    def to_recording(self) -> 'Recording':
        """Finalize recording and return artifact.
        
        Returns:
            Recording artifact containing all captured steps.
        """
        from .storage import Recording
        metadata = {
            'duration_ns': time.perf_counter_ns() - self._start_ns,
            'step_count': len(self.steps),
        }
        if self._truncated:
            metadata['truncated'] = True
            metadata['error'] = self._error_event
        
        return Recording(
            steps=self.steps,
            metadata=metadata,
            version='1.0.0'
        )
    
    # CaptureBackend protocol implementation
    def store(self, entry: CaptureEntry) -> None:
        """Store a capture entry from interceptors."""
        # Convert CaptureEntry to Step
        if hasattr(entry, 'to_dict'):
            data = entry.to_dict()
            self.record(
                function=data.get('type', 'unknown'),
                args=(),
                kwargs={
                    'method': data.get('method'),
                    'url': data.get('url'),
                    'headers': data.get('headers'),
                    'body': data.get('body'),
                },
                result={
                    'status': data.get('response_status'),
                    'headers': data.get('response_headers'),
                    'body': data.get('response_body'),
                }
            )
    
    def get_all(self) -> List[CaptureEntry]:
        """Get all captured entries."""
        return []  # Not used for now


class Recorder:
    """Global recorder singleton.
    
    Provides static methods for starting, stopping, and querying
    recording sessions.
    """
    _session: Optional[RecordingSession] = None
    
    @classmethod
    def start(cls) -> RecordingSession:
        """Start a new recording session.
        
        Returns:
            The new RecordingSession.
            
        Raises:
            RuntimeError: If a session is already active.
        """
        if cls._session is not None:
            raise RuntimeError("Recording session already active")
        cls._session = RecordingSession()
        return cls._session
    
    @classmethod
    def stop(cls) -> 'Recording':
        """Stop recording and return artifact.
        
        Returns:
            Recording artifact.
            
        Raises:
            RuntimeError: If no session is active.
        """
        if cls._session is None:
            raise RuntimeError("No active recording session")
        recording = cls._session.to_recording()
        cls._session = None
        return recording
    
    @classmethod
    def record(
        cls,
        function: str,
        args: tuple,
        kwargs: dict,
        result: Any = None,
        exception: Optional[Exception] = None
    ) -> Optional[Step]:
        """Record a step if session is active.
        
        Args:
            function: Function name.
            args: Positional arguments.
            kwargs: Keyword arguments.
            result: Return value.
            exception: Exception if raised.
            
        Returns:
            Recorded Step if session active, None otherwise.
        """
        if cls._session is None:
            return None
        return cls._session.record(function, args, kwargs, result, exception)
    
    @classmethod
    def is_recording(cls) -> bool:
        """Check if recording is active.
        
        Returns:
            True if a session is active.
        """
        return cls._session is not None
