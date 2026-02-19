"""ReplayPack - Deterministic Replay & Git-Diff Debugger for AI Workflows.

Main entry point for the replaypack package.
"""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar

from .core.recorder import Recorder
from .core.replayer import Replayer
from .intercept import create_default_interceptor
from .artifact import Artifact

F = TypeVar('F', bound=Callable[..., Any])

# Global state
_current_recorder: Optional[Recorder] = None
_interceptor = None


def init(
    output_dir: Optional[str] = None,
    capture_llm: bool = True,
    capture_http: bool = True,
    redact_secrets: bool = True
) -> None:
    """Initialize ReplayPack capture.
    
    Args:
        output_dir: Directory to save .rpk files (default: ./runs)
        capture_llm: Whether to capture LLM calls
        capture_http: Whether to capture HTTP requests
        redact_secrets: Whether to redact secrets in output
    """
    global _interceptor
    
    # Create output directory
    if output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        os.environ['REPLAYPACK_OUTPUT_DIR'] = str(output_dir)
    
    # Start recording first (creates session)
    session = Recorder.start()
    
    # Install interceptors with session as backend
    _interceptor = create_default_interceptor()
    if _interceptor:
        _interceptor.set_backend(session)
        _interceptor.install()
    
    return session


def stop() -> Path:
    """Stop recording and save artifact.
    
    Returns:
        Path to saved .rpk file.
    """
    global _interceptor
    
    # Stop recording
    recording = Recorder.stop()
    
    # Uninstall interceptors
    if _interceptor:
        _interceptor.uninstall()
        _interceptor = None
    
    # Create artifact
    artifact = Artifact(recording)
    
    # Save to output directory
    output_dir = Path(os.environ.get('REPLAYPACK_OUTPUT_DIR', './runs'))
    output_dir.mkdir(parents=True, exist_ok=True)
    
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = output_dir / f"run_{timestamp}.rpk"
    
    artifact.save(output_path)
    return output_path


@contextmanager
def record(output_dir: Optional[str] = None):
    """Context manager for recording a run.
    
    Args:
        output_dir: Directory to save .rpk files.
        
    Example:
        with replaypack.record() as rec:
            # Your code here
            pass
        # .rpk file saved automatically
    """
    init(output_dir=output_dir)
    try:
        yield
    finally:
        path = stop()
        print(f"Replay saved to: {path}")


def tool(name: Optional[str] = None) -> Callable[[F], F]:
    """Decorator to mark a function as a tool for capture.
    
    Args:
        name: Optional override for tool name.
        
    Example:
        @replaypack.tool()
        def my_tool(query: str) -> str:
            return f"Result for {query}"
    """
    def decorator(func: F) -> F:
        tool_name = name or func.__name__
        
        def wrapper(*args, **kwargs):
            if Recorder.is_recording():
                try:
                    result = func(*args, **kwargs)
                    Recorder.record(
                        function=f"tool.{tool_name}",
                        args=args,
                        kwargs=kwargs,
                        result=result
                    )
                    return result
                except Exception as e:
                    Recorder.record(
                        function=f"tool.{tool_name}",
                        args=args,
                        kwargs=kwargs,
                        exception=e
                    )
                    raise
            else:
                return func(*args, **kwargs)
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator


def capture_http(url_pattern: Optional[str] = None):
    r"""Decorator to capture HTTP requests to specific URLs.
    
    Args:
        url_pattern: URL pattern to capture (regex).
        
    Example:
        @replaypack.capture_http(r"https://api\.example\.com/.*")
        def fetch_data():
            return requests.get("https://api.example.com/data")
    """
    def decorator(func: F) -> F:
        # For now, just mark the function
        # Full implementation would wrap requests
        return func
    return decorator


__all__ = [
    'init',
    'stop',
    'record',
    'tool',
    'capture_http',
    'Recorder',
    'Replayer',
    'Artifact',
]
