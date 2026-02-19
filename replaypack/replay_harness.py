"""Replay harness for executing recorded sessions with stubbed calls."""

from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, List

from .artifact import Artifact
from .core.replayer import Replayer


class ReplayHarness:
    """Harness for replaying recorded sessions.
    
    Sets up the environment so that interceptors return recorded
    data instead of making live calls.
    """
    
    def __init__(self, artifact_path: Path):
        """Initialize harness with artifact.
        
        Args:
            artifact_path: Path to .rpk file.
        """
        self.artifact_path = Path(artifact_path)
        self.artifact = Artifact.load(self.artifact_path)
        self.replayer = Replayer()
        self.replayer.load(self.artifact.recording)
    
    def run(self, command: Optional[List[str]] = None) -> int:
        """Run replay harness.
        
        If command is provided, runs that command with replay environment.
        Otherwise, just validates the recording.
        
        Args:
            command: Optional command to run with stubs.
            
        Returns:
            Exit code.
        """
        # Set up environment for replay mode
        env = os.environ.copy()
        env['REPLAYPACK_MODE'] = 'replay'
        env['REPLAYPACK_ARTIFACT'] = str(self.artifact_path.absolute())
        
        # Add sitecustomize.py directory to PYTHONPATH
        repo_root = Path(__file__).parent.parent.absolute()
        pythonpath = env.get('PYTHONPATH', '')
        env['PYTHONPATH'] = f"{repo_root}{os.pathsep}{pythonpath}" if pythonpath else str(repo_root)
        
        if command:
            print(f"Replaying with stubs: {' '.join(command)}")
            print("[ReplayPack] Replay mode active - network calls will be stubbed")
            result = subprocess.run(command, env=env)
            return result.returncode
        else:
            # Just validate the recording
            print(f"Validating recording: {self.artifact_path}")
            result = self.replayer.replay()
            print(f"Steps: {result.steps_executed}")
            return 0
    
    def get_stub(self, function_name: str):
        """Get stub for a function.
        
        Args:
            function_name: Name of function to stub.
            
        Returns:
            Stubbed function or None.
        """
        return self.replayer.get_stub(function_name)


def replay_main():
    """Main entry point for replay mode."""
    artifact_path = os.environ.get('REPLAYPACK_ARTIFACT')
    if not artifact_path:
        print("Error: REPLAYPACK_ARTIFACT not set", file=sys.stderr)
        return 1
    
    harness = ReplayHarness(Path(artifact_path))
    
    # For now, just validate
    return harness.run()


if __name__ == '__main__':
    sys.exit(replay_main())
