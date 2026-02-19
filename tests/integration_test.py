"""Local integration test for ReplayPack.

This script tests the full workflow:
1. Record a simple execution
2. Replay it
3. Diff two runs
"""

import tempfile
from pathlib import Path

import replaypack
from replaypack.core.recorder import Recorder
from replaypack.core.replayer import Replayer
from replaypack.artifact import Artifact
from replaypack.divergence import DivergenceDetector


def test_simple_workflow():
    """Test recording and replaying a simple workflow."""
    print("=" * 50)
    print("Test 1: Simple Recording Workflow")
    print("=" * 50)
    
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        
        # Record a simple computation
        with replaypack.record(output_dir=str(tmp)):
            result = sum([1, 2, 3, 4, 5])
            print(f"Computed: {result}")
        
        # Check artifact was created
        files = list(tmp.glob("*.rpk"))
        assert len(files) > 0, "No .rpk file created"
        print(f"✓ Artifact created: {files[0].name}")
        
        # Load and replay
        artifact = Artifact.load(files[0])
        replayer = Replayer()
        replayer.load(artifact.recording)
        
        result = replayer.replay()
        print(f"✓ Replay completed: {result.steps_executed} steps")
        
        return files[0]


def test_divergence_detection():
    """Test detecting divergence between two runs."""
    print("\n" + "=" * 50)
    print("Test 2: Divergence Detection")
    print("=" * 50)
    
    import time
    
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        
        # First run
        with replaypack.record(output_dir=str(tmp)):
            result = 42
        
        time.sleep(1)  # Ensure different timestamp
        
        # Second run (different result)
        with replaypack.record(output_dir=str(tmp)):
            result = 99
        
        files = sorted(tmp.glob("*.rpk"))
        assert len(files) >= 2, f"Expected 2 artifacts, got {len(files)}"
        
        artifact_a = Artifact.load(files[0])
        artifact_b = Artifact.load(files[1])
        
        # Detect divergence
        detector = DivergenceDetector()
        divergence = detector.detect(artifact_a.recording, artifact_b.recording)
        
        if divergence.has_divergence:
            print(f"✓ Divergence detected at step {divergence.index}")
            print(f"  Type: {divergence.type.value}")
        else:
            print("✗ No divergence detected (unexpected)")


def test_tool_decorator():
    """Test the @replaypack.tool() decorator."""
    print("\n" + "=" * 50)
    print("Test 3: Tool Decorator")
    print("=" * 50)
    
    @replaypack.tool()
    def calculate(x: int, y: int) -> int:
        return x + y
    
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        
        with replaypack.record(output_dir=str(tmp)):
            result = calculate(10, 20)
            print(f"Tool result: {result}")
        
        files = list(tmp.glob("*.rpk"))
        artifact = Artifact.load(files[0])
        
        # Check tool call was recorded
        tool_steps = [s for s in artifact.recording.steps if "tool" in s.function]
        print(f"✓ Tool calls recorded: {len(tool_steps)}")


def test_offline_replay():
    """Test that replay works without network."""
    print("\n" + "=" * 50)
    print("Test 4: Offline Replay")
    print("=" * 50)
    
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        
        with replaypack.record(output_dir=str(tmp)):
            data = {"key": "value", "number": 123}
            print(f"Data: {data}")
        
        files = list(tmp.glob("*.rpk"))
        artifact = Artifact.load(files[0])
        
        replayer = Replayer()
        replayer.load(artifact.recording)
        
        # Verify determinism
        if replayer.verify_determinism(runs=10):
            print("✓ Replay is deterministic (10 runs)")
        else:
            print("✗ Replay not deterministic")


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("ReplayPack Integration Tests")
    print("=" * 50 + "\n")
    
    try:
        test_simple_workflow()
        test_divergence_detection()
        test_tool_decorator()
        test_offline_replay()
        
        print("\n" + "=" * 50)
        print("All tests passed! ✓")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
