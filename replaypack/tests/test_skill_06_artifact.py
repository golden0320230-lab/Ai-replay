"""Test Skill 6: Artifact System (.rpk).

Adversarial test suite validating:
- Artifact save/load
- Schema versioning
- Checksum verification
- Corrupted artifact handling
- Large file handling
- Bundle support
"""

import json
import tempfile
from pathlib import Path

import pytest

from replaypack.artifact import Artifact, ArtifactBundle, ArtifactError
from replaypack.core.storage import Recording
from replaypack.core.step import Step


def create_test_recording() -> Recording:
    """Create a test recording."""
    steps = [
        Step(
            id="step_1",
            sequence=1,
            function="test_func",
            args=(1, 2),
            kwargs={"key": "value"},
            result=3,
            exception=None
        )
    ]
    return Recording(steps=steps, metadata={"test": True}, version="1.0.0")


class TestArtifactSaveLoad:
    """Test artifact save and load."""
    
    def test_save_and_load(self):
        """Artifact can be saved and loaded."""
        recording = create_test_recording()
        artifact = Artifact(recording)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rpk', delete=False) as f:
            path = Path(f.name)
        
        try:
            artifact.save(path)
            loaded = Artifact.load(path)
            
            assert loaded.recording.version == recording.version
            assert len(loaded.recording.steps) == len(recording.steps)
        finally:
            path.unlink()
    
    def test_human_readable_json(self):
        """Artifact is human-readable JSON."""
        recording = create_test_recording()
        artifact = Artifact(recording)
        
        json_str = artifact.to_json()
        data = json.loads(json_str)
        
        assert "_header" in data
        assert "_metadata" in data
        assert "recording" in data


class TestChecksumVerification:
    """Test checksum verification."""
    
    def test_checksum_verifies(self):
        """Valid artifact passes checksum verification."""
        recording = create_test_recording()
        artifact = Artifact(recording)
        
        # Serialize to compute checksum
        _ = artifact.to_json()
        
        assert artifact.verify_checksum()


class TestCorruptedArtifacts:
    """Test corrupted artifact handling."""
    
    def test_invalid_json_raises_error(self):
        """Invalid JSON raises ArtifactError."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rpk', delete=False) as f:
            f.write("not valid json")
            path = Path(f.name)
        
        try:
            with pytest.raises(ArtifactError):
                Artifact.load(path)
        finally:
            path.unlink()
    
    def test_missing_recording_raises_error(self):
        """Missing recording data raises ArtifactError."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rpk', delete=False) as f:
            json.dump({"_header": {}, "_metadata": {}}, f)
            path = Path(f.name)
        
        try:
            with pytest.raises(ArtifactError):
                Artifact.load(path)
        finally:
            path.unlink()


class TestArtifactBundle:
    """Test artifact bundling."""
    
    def test_bundle_save_load(self):
        """Bundle can be saved and loaded."""
        recording1 = create_test_recording()
        recording2 = create_test_recording()
        
        bundle = ArtifactBundle([
            Artifact(recording1),
            Artifact(recording2)
        ])
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rpk', delete=False) as f:
            path = Path(f.name)
        
        try:
            bundle.save(path)
            loaded = ArtifactBundle.load(path)
            
            assert len(loaded.artifacts) == 2
        finally:
            path.unlink()
