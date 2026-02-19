"""sitecustomize.py for ReplayPack bootstrap.

This file is automatically imported by Python at startup.
It checks for ReplayPack environment variables and initializes
the recording/replay system before user code runs.
"""

import os

# Only bootstrap if ReplayPack mode is set
if os.environ.get('REPLAYPACK_MODE'):
    try:
        import replaypack._bootstrap
    except ImportError:
        pass  # ReplayPack not installed
