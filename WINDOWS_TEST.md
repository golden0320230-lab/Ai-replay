# ReplayPack Windows Test Instructions

## Step 1: Navigate to repo and activate environment
```powershell
cd C:\Users\elasm\OneDrive\Desktop\Ai-replay
.venv\Scripts\activate
```

## Step 2: Create a test script
Create file `test_capture.py` with this content:
```python
import replaypack

@replaypack.tool()
def my_tool(x, y):
    """A simple tool function"""
    return x * y

print("=== Starting Recording ===")
with replaypack.record(output_dir='./my_runs'):
    # This will be captured
    result = my_tool(5, 10)
    print(f"Tool result: {result}")
    
    # Regular Python code
    data = [1, 2, 3]
    print(f"Data: {data}")

print("=== Recording Complete ===")
```

## Step 3: Run the test
```powershell
python test_capture.py
```

## Step 4: See what was captured
```powershell
dir my_runs\
```

## Step 5: Load and inspect the artifact
```powershell
python -c "
from replaypack.artifact import Artifact
import glob

files = glob.glob('my_runs/*.rpk')
if files:
    artifact = Artifact.load(files[0])
    print(f'Artifact loaded: {files[0]}')
    print(f'Steps captured: {len(artifact.recording.steps)}')
    for step in artifact.recording.steps:
        print(f'  - Function: {step.function}')
        print(f'    Result: {step.result}')
"
```

## Step 6: Replay the recording
```powershell
python -c "
from replaypack.artifact import Artifact
from replaypack.core.replayer import Replayer
import glob

files = glob.glob('my_runs/*.rpk')
artifact = Artifact.load(files[0])

replayer = Replayer()
replayer.load(artifact.recording)
result = replayer.replay()

print(f'Replayed {result.steps_executed} steps')
print(f'Hash: {result.hash()}')
"
```

## Step 7: Clean up
```powershell
Remove-Item -Recurse -Force my_runs
Remove-Item test_capture.py
```
