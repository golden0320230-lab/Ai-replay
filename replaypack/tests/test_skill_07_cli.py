"""Test Skill 7: CLI Engineering.

Tests for CLI commands: record, replay, diff, assert, bundle
"""

import tempfile
from pathlib import Path

import pytest

from replaypack.cli import main, create_parser
from replaypack.artifact import Artifact
from replaypack.core.storage import Recording
from replaypack.core.step import Step


def create_test_artifact(path: Path) -> None:
    """Create a test artifact file."""
    steps = [Step(
        id="s1", sequence=1, function="test", args=(), kwargs={}, result=1, exception=None
    )]
    recording = Recording(steps=steps, metadata={}, version="1.0.0")
    artifact = Artifact(recording)
    artifact.save(path)


class TestCLIExitCodes:
    """Test CLI exit codes."""
    
    def test_diff_identical_returns_0(self):
        """diff of identical artifacts returns 0."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            create_test_artifact(tmp / "a.rpk")
            create_test_artifact(tmp / "b.rpk")
            
            exit_code = main(["diff", str(tmp / "a.rpk"), str(tmp / "b.rpk")])
            
            assert exit_code == 0
    
    def test_diff_different_returns_1(self):
        """diff of different artifacts returns 1."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            
            # Create different artifacts
            steps_a = [Step(id="s1", sequence=1, function="test", args=(), kwargs={}, result=1, exception=None)]
            steps_b = [Step(id="s1", sequence=1, function="test", args=(), kwargs={}, result=2, exception=None)]
            
            Artifact(Recording(steps=steps_a, metadata={}, version="1.0.0")).save(tmp / "a.rpk")
            Artifact(Recording(steps=steps_b, metadata={}, version="1.0.0")).save(tmp / "b.rpk")
            
            exit_code = main(["diff", str(tmp / "a.rpk"), str(tmp / "b.rpk")])
            
            assert exit_code == 1
    
    def test_assert_identical_returns_0(self):
        """assert of identical artifacts returns 0."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            create_test_artifact(tmp / "a.rpk")
            create_test_artifact(tmp / "b.rpk")
            
            exit_code = main(["assert", str(tmp / "a.rpk"), str(tmp / "b.rpk")])
            
            assert exit_code == 0
    
    def test_assert_different_returns_1(self):
        """assert of different artifacts returns 1."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            
            steps_a = [Step(id="s1", sequence=1, function="test", args=(), kwargs={}, result=1, exception=None)]
            steps_b = [Step(id="s1", sequence=1, function="test", args=(), kwargs={}, result=2, exception=None)]
            
            Artifact(Recording(steps=steps_a, metadata={}, version="1.0.0")).save(tmp / "a.rpk")
            Artifact(Recording(steps=steps_b, metadata={}, version="1.0.0")).save(tmp / "b.rpk")
            
            exit_code = main(["assert", str(tmp / "a.rpk"), str(tmp / "b.rpk")])
            
            assert exit_code == 1


class TestCLIBundle:
    """Test bundle command."""
    
    def test_bundle_creates_file(self):
        """bundle command creates output file."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            create_test_artifact(tmp / "a.rpk")
            create_test_artifact(tmp / "b.rpk")
            
            exit_code = main([
                "bundle",
                str(tmp / "a.rpk"),
                str(tmp / "b.rpk"),
                "-o", str(tmp / "bundle.rpk")
            ])
            
            assert exit_code == 0
            assert (tmp / "bundle.rpk").exists()


class TestCLIReplay:
    """Test replay command."""
    
    def test_replay_runs_recording(self):
        """replay command executes recording."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            create_test_artifact(tmp / "test.rpk")
            
            exit_code = main(["replay", str(tmp / "test.rpk")])
            
            assert exit_code == 0
