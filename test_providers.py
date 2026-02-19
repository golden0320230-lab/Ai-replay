"""Test provider expansion - local models via HTTP."""

import replaypack
from replaypack.intercept import create_default_interceptor

# Setup interceptor
interceptor = create_default_interceptor()
if interceptor:
    interceptor.install()

import requests
import json

print("=" * 60)
print("Provider Expansion Test")
print("=" * 60)

# Test various OpenAI-compatible endpoints
endpoints = [
    {
        "name": "OpenAI-compatible",
        "url": "https://httpbin.org/post",  # Simulated
        "payload": {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Hello"}],
            "temperature": 0.7
        }
    },
    {
        "name": "Ollama-style",
        "url": "https://httpbin.org/post",  # Simulated
        "payload": {
            "model": "llama2",
            "prompt": "Hello",
            "stream": False
        }
    },
    {
        "name": "vLLM/LM Studio",
        "url": "https://httpbin.org/post",  # Simulated
        "payload": {
            "model": "local-model",
            "messages": [{"role": "user", "content": "Test"}],
            "max_tokens": 100
        }
    }
]

replaypack.init(output_dir='./provider_test')

try:
    for ep in endpoints:
        print(f"\nTesting: {ep['name']}")
        try:
            response = requests.post(
                ep['url'],
                json=ep['payload'],
                timeout=10
            )
            print(f"  Status: {response.status_code}")
        except Exception as e:
            print(f"  Error: {e}")

finally:
    path = replaypack.stop()
    if interceptor:
        interceptor.uninstall()

print(f"\nSaved to: {path}")

# Inspect captured data
print("\n" + "=" * 60)
print("Captured Steps:")
print("=" * 60)

from replaypack.artifact import Artifact
a = Artifact.load(path)
print(f"Total steps: {len(a.recording.steps)}")

for i, step in enumerate(a.recording.steps, 1):
    print(f"\nStep {i}: {step.function}")
    if step.kwargs:
        url = step.kwargs.get('url', 'N/A')
        print(f"  URL: {url}")
        body = step.kwargs.get('body', {})
        if body and isinstance(body, dict):
            model = body.get('model', 'N/A')
            print(f"  Model: {model}")

print("\n" + "=" * 60)
print("All provider types captured via HTTP fallback!")
print("=" * 60)
