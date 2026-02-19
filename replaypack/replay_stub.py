"""Replay stub system for returning recorded data."""

from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class ReplayCursor:
    """Cursor for iterating through recorded steps during replay.
    
    Maintains position in the recording and returns the next matching
    step when a function is called.
    """
    
    def __init__(self, artifact_path: Path):
        """Initialize cursor with artifact.
        
        Args:
            artifact_path: Path to .rpk file.
        """
        self.artifact_path = artifact_path
        self.steps: List[Dict[str, Any]] = []
        self._index = 0
        self._load()
    
    def _load(self):
        """Load steps from artifact."""
        with open(self.artifact_path, 'r') as f:
            data = json.load(f)
        self.steps = data.get('recording', {}).get('steps', [])
    
    def next_step(self, function_name: str) -> Optional[Dict[str, Any]]:
        """Get next step matching the function name.
        
        Args:
            function_name: Name of function to match.
            
        Returns:
            Step dict or None if no match.
        """
        # Look for next step with matching function
        for i in range(self._index, len(self.steps)):
            step = self.steps[i]
            if step.get('function') == function_name:
                self._index = i + 1
                return step
        return None
    
    def reset(self):
        """Reset cursor to beginning."""
        self._index = 0


# Global cursor instance
_cursor: Optional[ReplayCursor] = None


def get_cursor() -> Optional[ReplayCursor]:
    """Get the global replay cursor.
    
    Returns:
        Cursor if in replay mode, None otherwise.
    """
    global _cursor
    
    if _cursor is not None:
        return _cursor
    
    # Check if we should initialize
    if os.environ.get('REPLAYPACK_MODE') == 'replay':
        artifact_path = os.environ.get('REPLAYPACK_ARTIFACT')
        if artifact_path:
            _cursor = ReplayCursor(Path(artifact_path))
            return _cursor
    
    return None


def get_stub_response(function_name: str) -> Optional[Any]:
    """Get stubbed response for a function call.
    
    Args:
        function_name: Name of function being called.
        
    Returns:
        Recorded result or None if not found.
    """
    cursor = get_cursor()
    if cursor is None:
        return None
    
    step = cursor.next_step(function_name)
    if step is None:
        return None
    
    # Check for exception
    if step.get('exception'):
        exc_data = step['exception']
        raise Exception(f"{exc_data.get('type', 'Exception')}: {exc_data.get('message', '')}")
    
    return step.get('result')


def is_replay_mode() -> bool:
    """Check if running in replay mode.
    
    Returns:
        True if replay mode is active.
    """
    return os.environ.get('REPLAYPACK_MODE') == 'replay'
