"""ReplayPack bootstrap module.

This module is imported early via sitecustomize.py to initialize
ReplayPack before user code runs.
"""

import os
import sys
import atexit

_atexit_registered = False

def _stop_recording():
    """Stop recording on process exit."""
    import replaypack
    try:
        path = replaypack.stop()
        sys.stderr.write(f"[ReplayPack] Recording saved to: {path}\n")
        sys.stderr.flush()
    except Exception as e:
        sys.stderr.write(f"[ReplayPack] Error saving: {e}\n")
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
        # Replay mode - interceptors will return recorded data
        os.environ['REPLAYPACK_REPLAY'] = '1'
        sys.stderr.write("[ReplayPack] Replay mode initialized\n")
        sys.stderr.flush()


# Auto-bootstrap when imported
bootstrap()
