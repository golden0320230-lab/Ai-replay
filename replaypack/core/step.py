"""Step data structures for deterministic replay."""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, NamedTuple, Optional, Tuple


# Volatile fields that should be ignored in non-strict mode
VOLATILE_HTTP_HEADERS = {
    'date', 'server', 'set-cookie',
    'x-request-id', 'x-amzn-trace-id', 'x-amz-request-id',
    'x-amzn-requestid', 'x-correlation-id', 'traceparent', 'tracestate',
    'x-b3-traceid', 'x-b3-spanid', 'x-b3-parentspanid',
    'cf-ray', 'cf-request-id',
}

VOLATILE_BODY_FIELDS = {
    'X-Amzn-Trace-Id',  # httpbin echo
    'x-amzn-trace-id',
}


def is_strict_mode() -> bool:
    """Check if strict mode is enabled."""
    return os.environ.get('REPLAYPACK_STRICT') == '1'


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
        
        In non-strict mode, volatile HTTP fields are normalized
        to prevent false divergences.
        
        Returns:
            32-character hex string hash.
        """
        result = self._normalize(self.result)
        
        # Apply volatility normalization for HTTP requests
        if not is_strict_mode() and self.function == 'http.request':
            result = self._normalize_http_response(result)
        
        data = {
            'sequence': self.sequence,
            'function': self.function,
            'args': self._normalize(self.args),
            'kwargs': self._normalize(self.kwargs),
            'result': result,
            'exception': self.exception,
        }
        canonical = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode()).hexdigest()[:32]
    
    def _normalize_http_response(self, result: Any) -> Any:
        """Normalize HTTP response to remove volatile fields.
        
        Args:
            result: The HTTP response result dict.
            
        Returns:
            Normalized result with volatile fields removed/blanked.
        """
        if not isinstance(result, dict):
            return result
        
        # Create a copy to avoid modifying original
        normalized = dict(result)
        
        # Normalize headers (case-insensitive)
        if 'headers' in normalized and isinstance(normalized['headers'], dict):
            headers = dict(normalized['headers'])
            for key in list(headers.keys()):
                if key.lower() in VOLATILE_HTTP_HEADERS:
                    headers[key] = '[REDACTED-VOLATILE]'
            normalized['headers'] = headers
        
        # Normalize body if it's JSON with volatile fields
        if 'body' in normalized and isinstance(normalized['body'], str):
            try:
                body_json = json.loads(normalized['body'])
                if isinstance(body_json, dict):
                    # Remove volatile fields from body
                    for key in list(body_json.keys()):
                        if key in VOLATILE_BODY_FIELDS:
                            body_json[key] = '[REDACTED-VOLATILE]'
                    # Also check nested headers
                    if 'headers' in body_json and isinstance(body_json['headers'], dict):
                        for key in list(body_json['headers'].keys()):
                            if key in VOLATILE_BODY_FIELDS:
                                body_json['headers'][key] = '[REDACTED-VOLATILE]'
                    normalized['body'] = json.dumps(body_json, sort_keys=True)
            except json.JSONDecodeError:
                pass  # Not JSON, leave as-is
        
        return normalized
    
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
