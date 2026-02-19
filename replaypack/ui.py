"""Local web UI for ReplayPack.

Git-diff style interface for comparing runs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .artifact import Artifact
from .divergence import DivergenceDetector
from .diff_engine import DiffEngine


class UI:
    """Local web UI for replay diff viewing."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8080):
        """Initialize UI server.
        
        Args:
            host: Host to bind to.
            port: Port to listen on.
        """
        self.host = host
        self.port = port
        self.artifact_a: Optional[Artifact] = None
        self.artifact_b: Optional[Artifact] = None
    
    def load_artifacts(self, path_a: Path, path_b: Path) -> None:
        """Load two artifacts for comparison.
        
        Args:
            path_a: Path to first artifact.
            path_b: Path to second artifact.
        """
        self.artifact_a = Artifact.load(path_a)
        self.artifact_b = Artifact.load(path_b)
    
    def get_step_list(self) -> list[dict]:
        """Get list of steps with status indicators.
        
        Returns:
            List of step info dicts.
        """
        if not self.artifact_a or not self.artifact_b:
            return []
        
        detector = DivergenceDetector()
        result = detector.compare_all(self.artifact_a.recording, self.artifact_b.recording)
        
        steps = []
        max_steps = max(
            len(self.artifact_a.recording.steps),
            len(self.artifact_b.recording.steps)
        )
        
        for i in range(max_steps):
            # Find divergence at this index
            div = next((d for d in result.all_divergences if d.index == i), None)
            
            if div is None:
                status = "identical"
            elif div.type.value == "value_mismatch":
                status = "changed"
            else:
                status = "changed"
            
            step_a = self.artifact_a.recording.steps[i] if i < len(self.artifact_a.recording.steps) else None
            step_b = self.artifact_b.recording.steps[i] if i < len(self.artifact_b.recording.steps) else None
            
            steps.append({
                "index": i,
                "status": status,
                "function_a": step_a.function if step_a else None,
                "function_b": step_b.function if step_b else None,
                "is_first_divergence": result.first_divergence and result.first_divergence.index == i
            })
        
        return steps
    
    def get_diff(self, step_index: int) -> dict:
        """Get diff for a specific step.
        
        Args:
            step_index: Index of step to diff.
            
        Returns:
            Diff information.
        """
        if not self.artifact_a or not self.artifact_b:
            return {}
        
        step_a = self.artifact_a.recording.steps[step_index] if step_index < len(self.artifact_a.recording.steps) else None
        step_b = self.artifact_b.recording.steps[step_index] if step_index < len(self.artifact_b.recording.steps) else None
        
        if not step_a or not step_b:
            return {"error": "Step not found in one of the recordings"}
        
        # Generate diff
        engine = DiffEngine()
        
        # Diff the results
        result_a = json.dumps(step_a.result, indent=2, sort_keys=True) if step_a.result else ""
        result_b = json.dumps(step_b.result, indent=2, sort_keys=True) if step_b.result else ""
        
        hunks = engine.line_diff(result_a, result_b)
        
        return {
            "step_index": step_index,
            "function": step_a.function,
            "hunks": [h.to_dict() for h in hunks],
            "old_result": step_a.result,
            "new_result": step_b.result
        }
    
    def get_metadata(self) -> dict:
        """Get metadata summary for comparison.
        
        Returns:
            Metadata dict.
        """
        if not self.artifact_a or not self.artifact_b:
            return {}
        
        detector = DivergenceDetector()
        divergence = detector.detect(self.artifact_a.recording, self.artifact_b.recording)
        
        return {
            "first_divergence": {
                "index": divergence.index,
                "type": divergence.type.value,
                "has_divergence": divergence.has_divergence
            } if divergence.has_divergence else None,
            "steps_a": len(self.artifact_a.recording.steps),
            "steps_b": len(self.artifact_b.recording.steps),
            "version_a": self.artifact_a.recording.version,
            "version_b": self.artifact_b.recording.version
        }
    
    def start(self) -> None:
        """Start the UI server."""
        print(f"Starting ReplayPack UI at http://{self.host}:{self.port}")
        print("Press Ctrl+C to stop")
        
        # Simple HTTP server for MVP
        # In production, this would use FastAPI/Flask
        import http.server
        import socketserver
        
        handler = http.server.SimpleHTTPRequestHandler
        
        with socketserver.TCPServer((self.host, self.port), handler) as httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\nShutting down...")
