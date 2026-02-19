"""Test offline stub replay - no network required."""

import replaypack
from replaypack.artifact import Artifact
from replaypack.core.replayer import Replayer

print("=" * 60)
print("Offline Stub Replay Test")
print("=" * 60)

# Load the previously recorded multi-call session
artifact = Artifact.load('multi_call_runs/run_20260219_163446.rpk')
print(f"\nLoaded artifact with {len(artifact.recording.steps)} steps")

# Create replayer
replayer = Replayer()
replayer.load(artifact.recording)

# Replay (this just walks through steps, not actual stub yet)
result = replayer.replay()
print(f"Replayed {result.steps_executed} steps")
print(f"Hash: {result.hash()}")

# Verify determinism
print("\nVerifying determinism (10 runs)...")
is_deterministic = replayer.verify_determinism(runs=10)
print(f"Deterministic: {is_deterministic}")

# Show step details
print("\n" + "=" * 60)
print("Step Details:")
print("=" * 60)
for i, step in enumerate(artifact.recording.steps, 1):
    print(f"\nStep {i}: {step.function}")
    print(f"  Hash: {step.canonical_hash()[:16]}...")
    if step.kwargs:
        print(f"  Args: {list(step.kwargs.keys())}")
    if step.result:
        result_type = type(step.result).__name__
        print(f"  Result type: {result_type}")

print("\n" + "=" * 60)
print("Test complete!")
print("=" * 60)
