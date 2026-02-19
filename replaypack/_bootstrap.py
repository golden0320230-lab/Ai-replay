"""ReplayPack bootstrap module.

This module is imported early via sitecustomize.py to initialize
ReplayPack before user code runs.
"""

import os
import sys
import atexit
import json
from pathlib import Path

_atexit_registered = False

def _stop_recording():
    """Stop recording on process exit."""
    import replaypack
    try:
        path = replaypack.stop()
        sys.stderr.write(f"[ReplayPack] Recording saved to: {path}\n")
        sys.stderr.flush()
        
        # Store command metadata in the artifact for later replay
        _store_command_metadata(path)
    except Exception as e:
        sys.stderr.write(f"[ReplayPack] Error saving: {e}\n")
        sys.stderr.flush()

def _store_command_metadata(artifact_path: Path):
    """Store command metadata in the artifact for replay."""
    try:
        cmd_metadata = os.environ.get('REPLAYPACK_CMD_METADATA')
        if cmd_metadata:
            metadata = json.loads(cmd_metadata)
            
            # Load artifact, add metadata, save back
            import json as json_mod
            with open(artifact_path, 'r') as f:
                data = json_mod.load(f)
            
            if 'recording' not in data:
                data['recording'] = {}
            if 'metadata' not in data['recording']:
                data['recording']['metadata'] = {}
            
            data['recording']['metadata']['command'] = metadata
            
            with open(artifact_path, 'w') as f:
                json_mod.dump(data, f, indent=2)
    except Exception as e:
        sys.stderr.write(f"[ReplayPack] Error storing metadata: {e}\n")
        sys.stderr.flush()

def bootstrap():
    """Initialize ReplayPack if environment indicates recording mode."""
    global _atexit_registered
    
    mode = os.environ.get('REPLAYPACK_MODE', '').lower()
    
    if mode == 'record':
        import replaypack
        output_dir = os.environ.get('REPLAYPACK_OUTPUT_DIR', './runs')
        
        # Only init if not already recording
        if not replaypack.Recorder.is_recording():
            replaypack.init(output_dir=output_dir)
            sys.stderr.write(f"[ReplayPack] Recording initialized (output: {output_dir})\n")
            sys.stderr.flush()
            
            # Register cleanup on exit
            if not _atexit_registered:
                atexit.register(_stop_recording)
                _atexit_registered = True
    
    elif mode == 'replay':
        # Replay mode - initialize cursor for stubbing
        os.environ['REPLAYPACK_REPLAY'] = '1'
        
        # Initialize replay cursor
        artifact_path = os.environ.get('REPLAYPACK_ARTIFACT')
        if artifact_path:
            from .replay_stub import ReplayCursor
            try:
                cursor = ReplayCursor(Path(artifact_path))
                sys.stderr.write(f"[ReplayPack] Replay mode initialized ({len(cursor.steps)} steps)\n")
                sys.stderr.flush()
            except Exception as e:
                sys.stderr.write(f"[ReplayPack] Error loading artifact: {e}\n")
                sys.stderr.flush()
        else:
            sys.stderr.write("[ReplayPack] Replay mode: no artifact specified\n")
            sys.stderr.flush()


# Auto-bootstrap when imported
bootstrap()
