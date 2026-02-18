"""Step data structures for deterministic replay."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, NamedTuple, Optional, Tuple


class Step(NamedTuple):
    """Immutable execution step.
    
    A Step represents a single function call execution with all inputs
    and outputs captured for deterministic replay.
    """
    id: str
    sequence: int  # strict ordering, monotonic
    function: str
    args: Tuple[Any, ...]
    kwargs: Dict[str, Any]
    result: Any
    exception: Optional[Dict[str, Any]]  # serialized exception
    
    def canonical_hash(self) -> str:
        """Deterministic hash of this step.
        
        The hash is computed from canonical JSON representation,
        ensuring identical logical steps produce identical hashes
        regardless of ID or other non-deterministic fields.
        
        Returns:
            32-character hex string hash.
        """
        data = {
            'sequence': self.sequence,
            'function': self.function,
            'args': self._normalize(self.args),
            'kwargs': self._normalize(self.kwargs),
            'result': self._normalize(self.result),
            'exception': self.exception,
        }
        canonical = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode()).hexdigest()[:32]
    
    @staticmethod
    def _normalize(obj: Any) -> Any:
        """Normalize object for deterministic hashing.
        
        Recursively normalizes data structures to ensure:
        - Dicts are sorted by key
        - Lists are preserved (order matters)
        - Basic types pass through
        - Other types converted to string
        
        Args:
            obj: Any object to normalize.
            
        Returns:
            Normalized representation suitable for hashing.
        """
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        if isinstance(obj, (list, tuple)):
            return [Step._normalize(x) for x in obj]
        if isinstance(obj, dict):
            return {k: Step._normalize(v) for k, v in sorted(obj.items())}
        # Convert other types to string representation
        return str(obj)
