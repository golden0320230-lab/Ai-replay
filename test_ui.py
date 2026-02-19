"""Test local UI functionality."""

from replaypack.ui import UI
from pathlib import Path

print("=" * 60)
print("Local UI Test")
print("=" * 60)

# Create UI instance
ui = UI(host="127.0.0.1", port=8080)

# Load two artifacts for comparison
ui.load_artifacts(
    Path('multi_call_runs/run_20260219_163446.rpk'),
    Path('divergence_test/run_20260219_163557.rpk')
)

print("\nArtifacts loaded successfully")

# Get metadata
print("\n" + "=" * 60)
print("Metadata:")
print("=" * 60)
metadata = ui.get_metadata()
print(f"Steps in A: {metadata['steps_a']}")
print(f"Steps in B: {metadata['steps_b']}")
if metadata['first_divergence']:
    print(f"First divergence at: Step {metadata['first_divergence']['index']}")
    print(f"Type: {metadata['first_divergence']['type']}")
else:
    print("No divergence detected")

# Get step list
print("\n" + "=" * 60)
print("Step List (Git-style):")
print("=" * 60)
steps = ui.get_step_list()
for step in steps:
    icon = "✅" if step['status'] == 'identical' else "🟡" if step['status'] == 'changed' else "🔴"
    first = " ← FIRST" if step['is_first_divergence'] else ""
    func = step['function_a'] or step['function_b'] or 'unknown'
    print(f"{icon} Step {step['index']}: {func}{first}")

# Get diff for first divergence
print("\n" + "=" * 60)
print("Diff for Step 1 (first tool call):")
print("=" * 60)
diff = ui.get_diff(1)
if 'hunks' in diff:
    print(f"Function: {diff['function']}")
    print(f"Hunks: {len(diff['hunks'])}")
    for hunk in diff['hunks'][:2]:  # Show first 2 hunks
        print(f"\n  Hunk: {hunk}")

print("\n" + "=" * 60)
print("UI test complete!")
print("\nTo start the web server, run:")
print("  replaypack ui")
print("=" * 60)
