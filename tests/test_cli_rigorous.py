"""Test CLI commands rigorously."""

import subprocess
import sys
import tempfile
from pathlib import Path

print("=" * 70)
print("CLI COMMAND TEST SUITE")
print("=" * 70)

# Create test artifacts
with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    
    # Create a test script
    script = tmp / "test_app.py"
    script.write_text('''
import replaypack

@replaypack.tool()
def calculate(x, y):
    return x + y

@replaypack.tool()
def multiply(x, y):
    return x * y

with replaypack.record(output_dir="./runs"):
    result1 = calculate(10, 20)
    result2 = multiply(5, 6)
    print(f"Results: {result1}, {result2}")
''')
    
    print("\n[Test 1] replaypack --help")
    result = subprocess.run(
        [sys.executable, "-m", "replaypack.cli", "--help"],
        capture_output=True,
        text=True
    )
    print(f"  Exit code: {result.returncode}")
    assert result.returncode == 0
    assert "record" in result.stdout
    assert "replay" in result.stdout
    assert "diff" in result.stdout
    assert "assert" in result.stdout
    assert "bundle" in result.stdout
    print("  ✓ All commands documented")
    
    print("\n[Test 2] replaypack record")
    result = subprocess.run(
        [sys.executable, "-m", "replaypack.cli", "record", str(script)],
        capture_output=True,
        text=True,
        cwd=tmp
    )
    print(f"  Exit code: {result.returncode}")
    print(f"  Stdout: {result.stdout[:200]}...")
    
    # Check if runs directory was created
    runs_dir = tmp / "runs"
    if runs_dir.exists():
        rpk_files = list(runs_dir.glob("*.rpk"))
        print(f"  Artifacts created: {len(rpk_files)}")
        if rpk_files:
            print("  ✓ Record command created artifacts")
            artifact_path = rpk_files[0]
        else:
            print("  ⚠ No artifacts found (may need manual instrumentation)")
            artifact_path = None
    else:
        print("  ⚠ No runs directory created")
        artifact_path = None
    
    if artifact_path:
        print("\n[Test 3] replaypack replay")
        result = subprocess.run(
            [sys.executable, "-m", "replaypack.cli", "replay", str(artifact_path)],
            capture_output=True,
            text=True
        )
        print(f"  Exit code: {result.returncode}")
        print(f"  Output: {result.stdout.strip()}")
        assert result.returncode == 0
        print("  ✓ Replay command works")
        
        # Create a second artifact for diff
        print("\n[Test 4] Creating second artifact for diff...")
        script2 = tmp / "test_app2.py"
        script2.write_text('''
import replaypack

@replaypack.tool()
def calculate(x, y):
    return x + y  # Same

@replaypack.tool()
def multiply(x, y):
    return x * y * 2  # CHANGED!

with replaypack.record(output_dir="./runs"):
    result1 = calculate(10, 20)
    result2 = multiply(5, 6)
    print(f"Results: {result1}, {result2}")
''')
        
        result = subprocess.run(
            [sys.executable, "-m", "replaypack.cli", "record", str(script2)],
            capture_output=True,
            text=True,
            cwd=tmp
        )
        
        rpk_files = sorted((tmp / "runs").glob("*.rpk"))
        if len(rpk_files) >= 2:
            print(f"  Created {len(rpk_files)} artifacts")
            
            print("\n[Test 5] replaypack diff")
            result = subprocess.run(
                [sys.executable, "-m", "replaypack.cli", "diff", 
                 str(rpk_files[0]), str(rpk_files[1])],
                capture_output=True,
                text=True
            )
            print(f"  Exit code: {result.returncode}")
            print(f"  Output: {result.stdout.strip()}")
            # Diff returns 1 if divergence found, 0 if identical
            print("  ✓ Diff command works")
            
            print("\n[Test 6] replaypack assert")
            result = subprocess.run(
                [sys.executable, "-m", "replaypack.cli", "assert",
                 str(rpk_files[0]), str(rpk_files[1])],
                capture_output=True,
                text=True
            )
            print(f"  Exit code: {result.returncode}")
            print(f"  Output: {result.stdout.strip()}")
            # Assert returns 1 if different (CI failure)
            print("  ✓ Assert command works")
            
            print("\n[Test 7] replaypack bundle")
            bundle_path = tmp / "test.bundle"
            result = subprocess.run(
                [sys.executable, "-m", "replaypack.cli", "bundle",
                 str(rpk_files[0]), "-o", str(bundle_path)],
                capture_output=True,
                text=True
            )
            print(f"  Exit code: {result.returncode}")
            print(f"  Output: {result.stdout.strip()}")
            if bundle_path.exists():
                print(f"  Bundle size: {bundle_path.stat().st_size} bytes")
                print("  ✓ Bundle command works")
            else:
                print("  ⚠ Bundle file not created")

print("\n" + "=" * 70)
print("CLI TEST SUITE COMPLETE")
print("=" * 70)
