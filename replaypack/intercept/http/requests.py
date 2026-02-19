"""requests library interception."""

from __future__ import annotations

import time
import os
from typing import Any, Callable, Dict, Optional
from types import ModuleType

from ..base import CaptureEntry, InterceptorBase


class HTTPCall(CaptureEntry):
    """Captured HTTP request/response."""
    
    def __init__(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[bytes],
        response_status: int,
        response_headers: Dict[str, str],
        response_body: bytes,
        duration_ms: int,
        timestamp_ns: int
    ):
        super().__init__("http.request", timestamp_ns)
        self.method = method
        self.url = url
        self.headers = headers
        self.body = body
        self.response_status = response_status
        self.response_headers = response_headers
        self.response_body = response_body
        self.duration_ms = duration_ms
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.entry_type,
            "method": self.method,
            "url": self.url,
            "headers": self.headers,
            "body": self._safe_decode(self.body),
            "response_status": self.response_status,
            "response_headers": self.response_headers,
            "response_body": self._safe_decode(self.response_body),
            "duration_ms": self.duration_ms,
            "timestamp_ns": self.timestamp_ns,
        }
    
    @staticmethod
    def _safe_decode(data: Optional[bytes]) -> Optional[str]:
        if data is None:
            return None
        try:
            return data.decode('utf-8')
        except UnicodeDecodeError:
            return data.hex()[:1000]  # Truncated hex for binary


class StubbedResponse:
    """Mock response object for replay."""
    
    def __init__(self, status_code: int, headers: Dict[str, str], content: bytes):
        self.status_code = status_code
        self.headers = headers
        self._content = content
        self.text = content.decode('utf-8', errors='replace')
    
    def json(self) -> Any:
        import json
        return json.loads(self.text)
    
    @property
    def content(self) -> bytes:
        return self._content


class RequestsInterceptor(InterceptorBase):
    """Intercepts requests library calls."""
    
    def __init__(self):
        super().__init__()
        self._requests_module: Optional[ModuleType] = None
        self._original_request: Optional[Callable] = None
    
    def install(self) -> None:
        """Install requests interception."""
        import requests
        self._requests_module = requests
        
        # Intercept Session.request
        self._original_request = requests.Session.request
        requests.Session.request = self._wrap_request(self._original_request)
        
        self._installed = True
    
    def uninstall(self) -> None:
        """Remove requests interception."""
        if self._requests_module and self._original_request:
            self._requests_module.Session.request = self._original_request
        self._installed = False
    
    def _is_replay_mode(self) -> bool:
        """Check if running in replay mode."""
        return os.environ.get('REPLAYPACK_MODE') == 'replay'
    
    def _get_stub_response(self, method: str, url: str) -> Optional[StubbedResponse]:
        """Get stubbed response from replay cursor."""
        from ...replay_stub import get_cursor
        
        cursor = get_cursor()
        if cursor is None:
            return None
        
        # Find matching http.request step
        step = cursor.next_step('http.request')
        if step is None:
            return None
        
        # Verify this is the right request (optional, could be smarter)
        result = step.get('result', {})
        return StubbedResponse(
            status_code=result.get('status', 200),
            headers=result.get('headers', {}),
            content=result.get('body', '').encode('utf-8') if result.get('body') else b''
        )
    
    def _wrap_request(self, original: Callable) -> Callable:
        """Wrap Session.request method."""
        
        def wrapped(session, method, url, **kwargs):
            # Check for replay mode first
            if self._is_replay_mode():
                stub = self._get_stub_response(method, url)
                if stub is not None:
                    return stub
                # If no stub found, fall through to live (or could raise error)
            
            start_ns = time.perf_counter_ns()
            
            # Capture request details
            headers = dict(kwargs.get('headers', {}))
            body = kwargs.get('data') or kwargs.get('json')
            if body is not None and isinstance(body, str):
                body = body.encode('utf-8')
            elif kwargs.get('json') is not None:
                import json
                body = json.dumps(kwargs['json']).encode('utf-8')
            
            try:
                response = original(session, method, url, **kwargs)
                
                duration_ms = (time.perf_counter_ns() - start_ns) // 1_000_000
                
                # Capture response
                response_body = response.content
                response_headers = dict(response.headers)
                
                call = HTTPCall(
                    method=method,
                    url=url,
                    headers=headers,
                    body=body if isinstance(body, bytes) else None,
                    response_status=response.status_code,
                    response_headers=response_headers,
                    response_body=response_body,
                    duration_ms=duration_ms,
                    timestamp_ns=start_ns
                )
                self._capture(call)
                
                return response
                
            except Exception as e:
                duration_ms = (time.perf_counter_ns() - start_ns) // 1_000_000
                
                call = HTTPCall(
                    method=method,
                    url=url,
                    headers=headers,
                    body=body if isinstance(body, bytes) else None,
                    response_status=0,
                    response_headers={},
                    response_body=str(e).encode(),
                    duration_ms=duration_ms,
                    timestamp_ns=start_ns
                )
                self._capture(call)
                raise
        
        return wrapped
