"""Recording functionality for capturing execution steps."""

from __future__ import annotations

import time
import uuid
from typing import Any, Optional

from .step import Step


class RecordingSession:
    """Active recording session.
    
    Manages the capture of execution steps during a recording.
    Thread-safe for concurrent step recording.
    """
    
    def __init__(self):
        self.steps: list[Step] = []
        self._sequence = 0
        self._start_ns = time.perf_counter_ns()
        self._lock = False  # Simple lock for thread safety
    
    def record(
        self,
        function: str,
        args: tuple,
        kwargs: dict,
        result: Any = None,
        exception: Optional[Exception] = None
    ) -> Step:
        """Record a single execution step.
        
        Args:
            function: Fully qualified function name.
            args: Positional arguments.
            kwargs: Keyword arguments.
            result: Return value (if no exception).
            exception: Exception that was raised (if any).
            
        Returns:
            The recorded Step.
        """
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
        return Recording(
            steps=self.steps,
            metadata={
                'duration_ns': time.perf_counter_ns() - self._start_ns,
                'step_count': len(self.steps),
            },
            version='1.0.0'
        )


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
