from replaypack.artifact import Artifact
import glob

files = glob.glob('ollama_runs/*.rpk')
if files:
    a = Artifact.load(files[0])
    print(f'Steps: {len(a.recording.steps)}')
    for step in a.recording.steps:
        print(f'Function: {step.function}')
        if 'http' in step.function:
            print(f'  URL: {step.kwargs.get(\"url\", \"N/A\")}')
            print(f'  Response: {str(step.result)[:200]}...')
