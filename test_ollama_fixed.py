"""Test Ollama capture with proper setup."""

import replaypack
from replaypack.intercept import create_default_interceptor

# Ensure interceptors are installed BEFORE importing requests
interceptor = create_default_interceptor()
if interceptor:
    interceptor.install()

import requests

# Start recording
replaypack.init(output_dir='./ollama_runs')

try:
    print("Calling Ollama...")
    response = requests.post(
        'http://localhost:11434/api/generate',
        json={
            'model': 'qwen',
            'prompt': 'What is 2+2? Answer in one word.',
            'stream': False
        },
        timeout=30
    )
    
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {result.get('response', 'No response')}")
    
except Exception as e:
    print(f"Error: {e}")

# Stop and save
path = replaypack.stop()
print(f"Saved to: {path}")

# Uninstall interceptors
if interceptor:
    interceptor.uninstall()
