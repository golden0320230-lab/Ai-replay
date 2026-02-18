"""Storage module for recording persistence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, List

from .step import Step


@dataclass(frozen=True)
class Recording:
    """Immutable recording artifact.
    
    The core data structure for storing and transporting
    recorded execution traces.
    """
    steps: List[Step]
    metadata: Dict[str, Any]
    version: str
    
    def hash(self) -> str:
        """Deterministic hash of entire recording.
        
        Used for integrity verification and deduplication.
        
        Returns:
            64-character hex SHA256 hash.
        """
        step_hashes = [step.canonical_hash() for step in self.steps]
        data = {
            'version': self.version,
            'metadata': self.metadata,
            'step_hashes': step_hashes,
        }
        canonical = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode()).hexdigest()
    
    def to_json(self) -> str:
        """Serialize to JSON.
        
        Returns:
            JSON string with stable ordering.
        """
        data = {
            'version': self.version,
            'metadata': self.metadata,
            'steps': [
                {
                    'id': step.id,
                    'sequence': step.sequence,
                    'function': step.function,
                    'args': step.args,
                    'kwargs': step.kwargs,
                    'result': step.result,
                    'exception': step.exception,
                    'hash': step.canonical_hash(),
                }
                for step in self.steps
            ],
        }
        return json.dumps(data, indent=2, sort_keys=True)
    
    @classmethod
    def from_json(cls, data: str) -> Recording:
        """Deserialize from JSON.
        
        Args:
            data: JSON string.
            
        Returns:
            Reconstructed Recording.
        """
        parsed = json.loads(data)
        steps = [
            Step(
                id=s['id'],
                sequence=s['sequence'],
                function=s['function'],
                args=tuple(s['args']),
                kwargs=s['kwargs'],
                result=s['result'],
                exception=s.get('exception'),
            )
            for s in parsed['steps']
        ]
        return cls(
            steps=steps,
            metadata=parsed['metadata'],
            version=parsed['version'],
        )
