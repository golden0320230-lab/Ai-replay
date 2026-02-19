"""Test divergence detection between two runs."""

import replaypack
from replaypack.artifact import Artifact
from replaypack.divergence.detector import DivergenceDetector
from replaypack.divergence.types import DivergenceType

print("=" * 60)
print("Divergence Detection Test")
print("=" * 60)

# Load the baseline recording
baseline = Artifact.load('multi_call_runs/run_20260219_163446.rpk')
print(f"\nBaseline: {len(baseline.recording.steps)} steps")

# Create a modified version (simulate a change)
print("\nCreating modified recording...")

# Record a new run with different data
@replaypack.tool()
def search_knowledge_base(query: str) -> list:
    # Changed: returns different results
    return [
        {"id": 99, "title": f"CHANGED Article about {query}"},  # Different!
        {"id": 2, "title": f"Guide to {query}"}
    ]

@replaypack.tool()
def calculate_price(items: list) -> dict:
    total = sum(item.get('price', 0) for item in items)
    return {"total": total, "count": len(items)}

import requests
from replaypack.intercept import create_default_interceptor

interceptor = create_default_interceptor()
if interceptor:
    interceptor.install()

replaypack.init(output_dir='./divergence_test')

# Simulate similar workflow but with changes
try:
    # HTTP call (same)
    requests.post('https://httpbin.org/post', json={"prompt": "test"}, timeout=10)
    
    # Tool call (CHANGED - different result)
    results = search_knowledge_base("machine learning")
    
    # Another HTTP
    requests.post('https://httpbin.org/post', json={"prompt": "test2"}, timeout=10)
    
    # Tool call (same)
    items = [{"price": 10}, {"price": 25}, {"price": 15}]
    price_info = calculate_price(items)
    
    # Final HTTP
    requests.post('https://httpbin.org/post', json={"prompt": "test3"}, timeout=10)
    
finally:
    path = replaypack.stop()
    if interceptor:
        interceptor.uninstall()

print(f"Modified run saved to: {path}")

# Load modified recording
modified = Artifact.load(path)
print(f"Modified: {len(modified.recording.steps)} steps")

# Detect divergence
detector = DivergenceDetector()
divergence = detector.detect(baseline.recording, modified.recording)

print("\n" + "=" * 60)
print("Divergence Analysis:")
print("=" * 60)

if divergence.type == DivergenceType.NONE:
    print("\n✓ No divergence detected - runs are identical")
else:
    print(f"\n✗ First divergence at step {divergence.index}")
    print(f"  Type: {divergence.type.value}")
    print(f"  Hash A: {divergence.hash_a[:16] if divergence.hash_a else 'N/A'}...")
    print(f"  Hash B: {divergence.hash_b[:16] if divergence.hash_b else 'N/A'}...")
    if divergence.context:
        print(f"  Context: {divergence.context}")

# Also do full comparison
print("\n" + "=" * 60)
print("Full Comparison:")
print("=" * 60)

result = detector.compare_all(baseline.recording, modified.recording)
print(f"Steps compared: {result.steps_compared}")
print(f"Steps matched: {result.steps_matched}")
print(f"Total divergences: {len(result.all_divergences)}")

for div in result.all_divergences:
    print(f"  - Step {div.index}: {div.type.value}")

print("\n" + "=" * 60)
print("Test complete!")
print("=" * 60)
