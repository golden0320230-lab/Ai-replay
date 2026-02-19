"""Test HTTP capture integration."""

import replaypack
from replaypack.intercept import create_default_interceptor

# Install interceptor BEFORE importing requests
interceptor = create_default_interceptor()
if interceptor:
    interceptor.install()

import requests

print("=" * 50)
print("HTTP Capture Test")
print("=" * 50)

# Start recording
replaypack.init(output_dir='./http_test_runs')

try:
    print("\n[Step 1] HTTP GET request...")
    response = requests.get('https://httpbin.org/get', timeout=10)
    print(f"  Status: {response.status_code}")
    print(f"  Content length: {len(response.text)} bytes")
    
    print("\n[Step 2] HTTP POST request...")
    response = requests.post(
        'https://httpbin.org/post',
        json={'key': 'value', 'test': True},
        timeout=10
    )
    print(f"  Status: {response.status_code}")
    
except Exception as e:
    print(f"  Error: {e}")

# Stop and save
path = replaypack.stop()
print(f"\nSaved to: {path}")

# Uninstall
if interceptor:
    interceptor.uninstall()

# Inspect what was captured
print("\n" + "=" * 50)
print("Inspecting captured data...")
print("=" * 50)

from replaypack.artifact import Artifact
a = Artifact.load(path)
print(f"\nTotal steps captured: {len(a.recording.steps)}")

for i, step in enumerate(a.recording.steps, 1):
    print(f"\nStep {i}: {step.function}")
    if hasattr(step, 'kwargs') and step.kwargs:
        url = step.kwargs.get('url', 'N/A')
        print(f"  URL: {url}")
    if hasattr(step, 'result') and step.result:
        print(f"  Result type: {type(step.result).__name__}")

print("\n" + "=" * 50)
print("Test complete!")
print("=" * 50)
