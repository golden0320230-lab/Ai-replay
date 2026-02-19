"""CLI interface for ReplayPack.

Commands: record, replay, diff, assert, bundle, ui
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from .core.recorder import Recorder
from .core.replayer import Replayer
from .core.storage import Recording
from .divergence import DivergenceDetector
from .diff_engine import DiffEngine
from .artifact import Artifact, ArtifactBundle
from .ui import UI


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog='replaypack',
        description='Deterministic replay and Git-diff debugging for AI workflows'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # record command - supports: replaypack record -- python script.py
    record_parser = subparsers.add_parser('record', help='Record a new replay')
    record_parser.add_argument('command_args', nargs='*', help='Command to record (e.g., -- python script.py)')
    record_parser.add_argument('-o', '--output', default='./runs', help='Output directory (default: ./runs)')
    
    # replay command
    replay_parser = subparsers.add_parser('replay', help='Replay a recording')
    replay_parser.add_argument('artifact', help='Input .rpk file')
    replay_parser.add_argument('--verify', action='store_true', help='Verify determinism')
    
    # diff command
    diff_parser = subparsers.add_parser('diff', help='Compare two recordings')
    diff_parser.add_argument('artifact_a', help='First .rpk file')
    diff_parser.add_argument('artifact_b', help='Second .rpk file')
    diff_parser.add_argument('--first-divergence', action='store_true', help='Show only first divergence')
    diff_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # assert command
    assert_parser = subparsers.add_parser('assert', help='Assert recordings match')
    assert_parser.add_argument('artifact_a', help='First .rpk file')
    assert_parser.add_argument('artifact_b', help='Second .rpk file')
    
    # bundle command
    bundle_parser = subparsers.add_parser('bundle', help='Bundle recordings with redaction')
    bundle_parser.add_argument('artifacts', nargs='+', help='Input .rpk files')
    bundle_parser.add_argument('-o', '--output', required=True, help='Output bundle file')
    bundle_parser.add_argument('--redact', default='default', choices=['none', 'default', 'strict'], 
                               help='Redaction level (default: default)')
    
    # ui command
    ui_parser = subparsers.add_parser('ui', help='Launch local Git-diff UI')
    ui_parser.add_argument('--host', default='127.0.0.1', help='Host to bind to (default: 127.0.0.1)')
    ui_parser.add_argument('--port', type=int, default=8080, help='Port to listen on (default: 8080)')
    ui_parser.add_argument('--artifact-a', help='First artifact to load')
    ui_parser.add_argument('--artifact-b', help='Second artifact to load')
    
    return parser


def cmd_record(args) -> int:
    """Record command with bootstrap support."""
    import replaypack
    
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine what to run
    if args.command_args:
        # Handle -- separator
        cmd_args = args.command_args
        if cmd_args[0] == '--':
            cmd_args = cmd_args[1:]
        
        if not cmd_args:
            print("Error: No command specified after 'record'", file=sys.stderr)
            return 1
        
        # Set up environment for bootstrap
        env = os.environ.copy()
        env['REPLAYPACK_MODE'] = 'record'
        env['REPLAYPACK_OUTPUT_DIR'] = str(output_dir.absolute())
        
        # Add sitecustomize.py directory to PYTHONPATH for bootstrap
        repo_root = Path(__file__).parent.parent.absolute()
        pythonpath = env.get('PYTHONPATH', '')
        env['PYTHONPATH'] = f"{repo_root}{os.pathsep}{pythonpath}" if pythonpath else str(repo_root)
        
        # Run the specified command
        print(f"Recording: {' '.join(cmd_args)}")
        result = subprocess.run(cmd_args, env=env)
        
        # Note: When using bootstrap, the subprocess handles its own recording lifecycle
        # If not using bootstrap (no env var), we would init here
    else:
        # No command specified - use direct recording mode
        print("Recording in current process...")
        replaypack.init(output_dir=str(output_dir))
        try:
            # Interactive mode or no command
            print("Press Ctrl+D (Unix) or Ctrl+Z (Windows) to stop recording")
            # Wait for interrupt
            import signal
            signal.pause()
        except KeyboardInterrupt:
            pass
        finally:
            path = replaypack.stop()
            print(f"\nRecording saved to: {path}")
        return 0
    
    # Find and report created artifacts
    rpk_files = sorted(output_dir.glob('*.rpk'))
    if rpk_files:
        print(f"\nRecording complete. Artifacts in {output_dir}:")
        for f in rpk_files[-5:]:  # Show last 5
            print(f"  - {f.name}")
    else:
        print(f"\nWarning: No .rpk files found in {output_dir}")
    
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
    """Diff command with git-style output."""
    artifact_a = Artifact.load(args.artifact_a)
    artifact_b = Artifact.load(args.artifact_b)
    
    detector = DivergenceDetector()
    
    if args.first_divergence:
        # Show only first divergence
        divergence = detector.detect(artifact_a.recording, artifact_b.recording)
        
        if not divergence.has_divergence:
            print("✓ Recordings are identical")
            return 0
        
        print(f"✗ First divergence at step {divergence.index}")
        print(f"  Type: {divergence.type.value}")
        
        if divergence.step_a and divergence.step_b:
            print(f"  Function: {divergence.step_a.function}")
            print(f"  Hash A: {divergence.hash_a[:16] if divergence.hash_a else 'N/A'}...")
            print(f"  Hash B: {divergence.hash_b[:16] if divergence.hash_b else 'N/A'}...")
        
        # Show git-style diff for the divergent step
        if divergence.step_a and divergence.step_b:
            print("\n--- Step A ---")
            print(f"{divergence.step_a.result}")
            print("\n+++ Step B +++")
            print(f"{divergence.step_b.result}")
        
        return 1
    else:
        # Full comparison
        result = detector.compare_all(artifact_a.recording, artifact_b.recording)
        
        print(f"Steps compared: {result.steps_compared}")
        print(f"Steps matched: {result.steps_matched}")
        
        if result.first_divergence:
            print(f"✗ First divergence at step {result.first_divergence.index}")
            print(f"  Type: {result.first_divergence.type.value}")
            return 1
        else:
            print("✓ Recordings are identical")
            return 0


def cmd_assert(args) -> int:
    """Assert command - fails if recordings differ."""
    artifact_a = Artifact.load(args.artifact_a)
    artifact_b = Artifact.load(args.artifact_b)
    
    detector = DivergenceDetector()
    divergence = detector.detect(artifact_a.recording, artifact_b.recording)
    
    if divergence.has_divergence:
        print(f"ASSERTION FAILED: Divergence at step {divergence.index}")
        print(f"  Type: {divergence.type.value}")
        return 1
    else:
        print("ASSERTION PASSED: Recordings match")
        return 0


def cmd_bundle(args) -> int:
    """Bundle command with redaction."""
    from .security import RedactionEngine
    from .core.step import Step
    from .core.storage import Recording
    
    artifacts = [Artifact.load(a) for a in args.artifacts]
    
    # Apply redaction if requested
    if args.redact != 'none':
        engine = RedactionEngine()
        
        # Redact by creating new artifacts (steps are immutable)
        redacted_artifacts = []
        for artifact in artifacts:
            # Create redacted copy of recording
            redacted_steps = []
            for step in artifact.recording.steps:
                redacted_kwargs = engine.redact_dict(step.kwargs) if step.kwargs else step.kwargs
                redacted_result = engine.redact_dict(step.result) if step.result and isinstance(step.result, dict) else step.result
                
                # Create new step with redacted data
                redacted_step = Step(
                    id=step.id,
                    sequence=step.sequence,
                    function=step.function,
                    args=step.args,
                    kwargs=redacted_kwargs,
                    result=redacted_result,
                    exception=step.exception
                )
                redacted_steps.append(redacted_step)
            
            # Create new recording with redacted steps
            redacted_recording = Recording(
                steps=redacted_steps,
                metadata=artifact.recording.metadata,
                version=artifact.recording.version
            )
            
            # Create new artifact
            redacted_artifact = Artifact(redacted_recording)
            redacted_artifacts.append(redacted_artifact)
        
        artifacts = redacted_artifacts
    
    bundle = ArtifactBundle(artifacts)
    bundle.save(args.output)
    print(f"Bundle saved to {args.output}")
    print(f"  Artifacts: {len(artifacts)}")
    print(f"  Redaction: {args.redact}")
    return 0


def cmd_ui(args) -> int:
    """Launch local UI."""
    ui = UI(host=args.host, port=args.port)
    
    # Load artifacts if specified
    if args.artifact_a and args.artifact_b:
        ui.load_artifacts(Path(args.artifact_a), Path(args.artifact_b))
        print(f"Loaded artifacts for comparison")
    
    print(f"Starting ReplayPack UI at http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop")
    
    try:
        ui.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
    
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point."""
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
        'ui': cmd_ui,
    }
    
    try:
        return commands[args.command](args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
