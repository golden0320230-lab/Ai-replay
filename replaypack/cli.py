"""CLI interface for ReplayPack.

Commands: record, replay, diff, assert, bundle, ui
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from .core.recorder import Recorder
from .core.replayer import Replayer
from .core.storage import Recording
from .divergence import DivergenceDetector
from .diff_engine import DiffEngine
from .artifact import Artifact, ArtifactBundle


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog='replaypack',
        description='Deterministic replay and Git-diff debugging for AI workflows'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # record command
    record_parser = subparsers.add_parser('record', help='Record a new replay')
    record_parser.add_argument('script', help='Python script to record')
    record_parser.add_argument('-o', '--output', default='./runs', help='Output directory (default: ./runs)')
    
    # replay command
    replay_parser = subparsers.add_parser('replay', help='Replay a recording')
    replay_parser.add_argument('artifact', help='Input .rpk file')
    replay_parser.add_argument('--verify', action='store_true', help='Verify determinism')
    
    # diff command
    diff_parser = subparsers.add_parser('diff', help='Compare two recordings')
    diff_parser.add_argument('artifact_a', help='First .rpk file')
    diff_parser.add_argument('artifact_b', help='Second .rpk file')
    diff_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # assert command
    assert_parser = subparsers.add_parser('assert', help='Assert recordings match')
    assert_parser.add_argument('artifact_a', help='First .rpk file')
    assert_parser.add_argument('artifact_b', help='Second .rpk file')
    
    # bundle command
    bundle_parser = subparsers.add_parser('bundle', help='Bundle multiple recordings')
    bundle_parser.add_argument('artifacts', nargs='+', help='Input .rpk files')
    bundle_parser.add_argument('-o', '--output', required=True, help='Output bundle file')
    
    return parser


def cmd_record(args) -> int:
    """Record command."""
    import subprocess
    import os
    
    # Set up environment to enable recording
    env = os.environ.copy()
    env['REPLAYPACK_RECORD'] = '1'
    
    # Create output directory
    Path(args.output).mkdir(parents=True, exist_ok=True)
    env['REPLAYPACK_OUTPUT_DIR'] = args.output
    
    print(f"Recording {args.script}...")
    
    # Run the script with replaypack imported
    # For now, just run it directly
    result = subprocess.run([sys.executable, args.script], env=env)
    
    if result.returncode == 0:
        print(f"Recording complete. Check {args.output}/ for .rpk file")
    
    return result.returncode


def cmd_replay(args) -> int:
    """Replay command."""
    artifact = Artifact.load(args.artifact)
    replayer = Replayer()
    replayer.load(artifact.recording)
    
    print(f"Replaying {args.artifact}...")
    result = replayer.replay()
    
    if args.verify:
        print("Verifying determinism...")
        if replayer.verify_determinism():
            print("✓ Determinism verified (100 runs)")
        else:
            print("✗ Determinism check failed")
            return 1
    
    print(f"Steps executed: {result.steps_executed}")
    return 0


def cmd_diff(args) -> int:
    """Diff command."""
    artifact_a = Artifact.load(args.artifact_a)
    artifact_b = Artifact.load(args.artifact_b)
    
    detector = DivergenceDetector()
    divergence = detector.detect(artifact_a.recording, artifact_b.recording)
    
    if divergence.has_divergence:
        print(f"Divergence detected at step {divergence.index}")
        print(f"Type: {divergence.type.value}")
        return 1
    else:
        print("Recordings are identical")
        return 0


def cmd_assert(args) -> int:
    """Assert command - fails if recordings differ."""
    artifact_a = Artifact.load(args.artifact_a)
    artifact_b = Artifact.load(args.artifact_b)
    
    detector = DivergenceDetector()
    divergence = detector.detect(artifact_a.recording, artifact_b.recording)
    
    if divergence.has_divergence:
        print(f"ASSERTION FAILED: Divergence at step {divergence.index}")
        return 1
    else:
        print("ASSERTION PASSED: Recordings match")
        return 0


def cmd_bundle(args) -> int:
    """Bundle command."""
    artifacts = [Artifact.load(a) for a in args.artifacts]
    bundle = ArtifactBundle(artifacts)
    bundle.save(args.output)
    print(f"Bundle saved to {args.output}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point.
    
    Args:
        argv: Command line arguments.
        
    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    parser = create_parser()
    args = parser.parse_args(argv)
    
    if not args.command:
        parser.print_help()
        return 0
    
    commands = {
        'record': cmd_record,
        'replay': cmd_replay,
        'diff': cmd_diff,
        'assert': cmd_assert,
        'bundle': cmd_bundle,
    }
    
    try:
        return commands[args.command](args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
