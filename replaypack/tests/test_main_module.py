"""Test main replaypack module.

Tests for init(), stop(), record(), tool() decorators.
"""

import os
import tempfile
from pathlib import Path

import pytest

import replaypack
from replaypack.core.recorder import Recorder


class TestInit:
    """Test init() function."""
    
    def test_init_creates_output_dir(self):
        """init() creates output directory."""
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "runs"
            replaypack.init(output_dir=str(output_dir))
            
            assert output_dir.exists()
            
            replaypack.stop()
    
    def test_init_starts_recording(self):
        """init() starts recording session."""
        replaypack.init()
        
        assert Recorder.is_recording()
        
        replaypack.stop()


class TestStop:
    """Test stop() function."""
    
    def test_stop_saves_artifact(self):
        """stop() saves artifact to file."""
        with tempfile.TemporaryDirectory() as tmp:
            replaypack.init(output_dir=str(tmp))
            path = replaypack.stop()
            
            assert path.exists()
            assert path.suffix == ".rpk"


class TestRecordContextManager:
    """Test record() context manager."""
    
    def test_record_context_manager(self):
        """record() works as context manager."""
        with tempfile.TemporaryDirectory() as tmp:
            with replaypack.record(output_dir=str(tmp)):
                assert Recorder.is_recording()
            
            # Check artifact was saved
            files = list(Path(tmp).glob("*.rpk"))
            assert len(files) >= 1


class TestToolDecorator:
    """Test @replaypack.tool() decorator."""
    
    def test_tool_decorator_records_calls(self):
        """Tool decorator records function calls."""
        
        @replaypack.tool()
        def my_tool(query: str) -> str:
            return f"Result: {query}"
        
        replaypack.init()
        
        result = my_tool("test")
        
        assert result == "Result: test"
        
        recording = replaypack.stop()
        assert recording.exists()
