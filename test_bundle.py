"""Test bundle export with redaction."""

import replaypack
from replaypack.artifact import Artifact
from replaypack.security import RedactionEngine

print("=" * 60)
print("Bundle + Redaction Test")
print("=" * 60)

# Load the baseline recording
artifact = Artifact.load('multi_call_runs/run_20260219_163446.rpk')
print(f"\nLoaded artifact: {len(artifact.recording.steps)} steps")

# Test redaction engine
print("\n" + "=" * 60)
print("Redaction Engine Test")
print("=" * 60)

engine = RedactionEngine()

# Test with sensitive data
test_data = {
    "api_key": "sk-abc123xyz789secretkey",
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user_email": "test@example.com",
    "normal_data": "This is safe to show",
    "password": "supersecret123",
    "nested": {
        "token": "secret_token_here",
        "safe": "This is also safe"
    }
}

print("\nOriginal data:")
for key, value in test_data.items():
    print(f"  {key}: {value}")

redacted = engine.redact_dict(test_data)

print("\nRedacted data:")
for key, value in redacted.items():
    print(f"  {key}: {value}")

# Test bundle creation
print("\n" + "=" * 60)
print("Bundle Creation Test")
print("=" * 60)

from replaypack.artifact import ArtifactBundle

# Create a bundle with multiple artifacts
artifacts = [
    Artifact.load('multi_call_runs/run_20260219_163446.rpk'),
    Artifact.load('divergence_test/run_20260219_163557.rpk'),
]

bundle = ArtifactBundle(artifacts)
bundle_path = 'test_bundle.rpk'
bundle.save(bundle_path)

print(f"Bundle saved to: {bundle_path}")
print(f"Artifacts in bundle: {len(bundle.artifacts)}")

# Load and verify
loaded_bundle = ArtifactBundle.load(bundle_path)
print(f"Loaded bundle: {len(loaded_bundle.artifacts)} artifacts")

for i, art in enumerate(loaded_bundle.artifacts):
    print(f"  Artifact {i+1}: {len(art.recording.steps)} steps")

print("\n" + "=" * 60)
print("Test complete!")
print("=" * 60)
