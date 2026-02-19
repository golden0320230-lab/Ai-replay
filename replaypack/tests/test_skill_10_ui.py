"""Test Skill 10: Git-Diff UI (Local).

Tests for web UI components.
"""

import tempfile
from pathlib import Path

import pytest

from replaypack.ui import UI
from replaypack.artifact import Artifact
from replaypack.core.storage import Recording
from replaypack.core.step import Step


def create_test_artifact(path: Path, result_value: int = 1) -> None:
    """Create a test artifact."""
    steps = [Step(
        id="s1", sequence=1, function="test_func", args=(), kwargs={},
        result={"value": result_value}, exception=None
    )]
    recording = Recording(steps=steps, metadata={}, version="1.0.0")
    artifact = Artifact(recording)
    artifact.save(path)


class TestUILoading:
    """Test UI artifact loading."""
    
    def test_load_artifacts(self):
        """UI can load two artifacts."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            create_test_artifact(tmp / "a.rpk", result_value=1)
            create_test_artifact(tmp / "b.rpk", result_value=2)
            
            ui = UI()
            ui.load_artifacts(tmp / "a.rpk", tmp / "b.rpk")
            
            assert ui.artifact_a is not None
            assert ui.artifact_b is not None


class TestStepList:
    """Test step list generation."""
    
    def test_step_list_with_status(self):
        """Step list includes status indicators."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            create_test_artifact(tmp / "a.rpk", result_value=1)
            create_test_artifact(tmp / "b.rpk", result_value=2)
            
            ui = UI()
            ui.load_artifacts(tmp / "a.rpk", tmp / "b.rpk")
            steps = ui.get_step_list()
            
            assert len(steps) >= 1
            assert steps[0]["status"] in ["identical", "changed"]
    
    def test_first_divergence_marked(self):
        """First divergence is marked in step list."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            create_test_artifact(tmp / "a.rpk", result_value=1)
            create_test_artifact(tmp / "b.rpk", result_value=2)
            
            ui = UI()
            ui.load_artifacts(tmp / "a.rpk", tmp / "b.rpk")
            steps = ui.get_step_list()
            
            # First step should be marked as first divergence
            assert steps[0]["is_first_divergence"] is True


class TestDiffGeneration:
    """Test diff generation."""
    
    def test_get_diff_for_step(self):
        """Diff can be generated for a step."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            create_test_artifact(tmp / "a.rpk", result_value=1)
            create_test_artifact(tmp / "b.rpk", result_value=2)
            
            ui = UI()
            ui.load_artifacts(tmp / "a.rpk", tmp / "b.rpk")
            diff = ui.get_diff(0)
            
            assert "step_index" in diff
            assert "hunks" in diff


class TestMetadata:
    """Test metadata summary."""
    
    def test_metadata_includes_divergence(self):
        """Metadata includes first divergence info."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            create_test_artifact(tmp / "a.rpk", result_value=1)
            create_test_artifact(tmp / "b.rpk", result_value=2)
            
            ui = UI()
            ui.load_artifacts(tmp / "a.rpk", tmp / "b.rpk")
            metadata = ui.get_metadata()
            
            assert metadata["first_divergence"] is not None
            assert metadata["first_divergence"]["has_divergence"] is True
