"""Mistral AI SDK interception."""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from ..base import CaptureEntry, InterceptorBase


class MistralCall(CaptureEntry):
    """Captured Mistral API call."""
    
    def __init__(
        self,
        model: str,
        messages: List[Dict[str, str]],
        params: Dict[str, Any],
        response: Optional[Dict[str, Any]],
        streaming: bool,
        latency_ms: int,
        timestamp_ns: int
    ):
        super().__init__("llm.mistral", timestamp_ns)
        self.provider = "mistral"
        self.model = model
        self.messages = messages
        self.params = params
        self.response = response
        self.streaming = streaming
        self.latency_ms = latency_ms
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.entry_type,
            "provider": self.provider,
            "model": self.model,
            "messages": self.messages,
            "params": self.params,
            "response": self.response,
            "streaming": self.streaming,
            "latency_ms": self.latency_ms,
            "timestamp_ns": self.timestamp_ns,
        }


class MistralInterceptor(InterceptorBase):
    """Intercepts Mistral SDK calls."""
    
    def __init__(self):
        super().__init__()
    
    def install(self) -> None:
        """Install Mistral interception."""
        try:
            from mistralai.client import MistralClient
        except ImportError:
            return
        
        original_chat = MistralClient.chat
        
        def patched_chat(self, *args, **kwargs):
            return self._wrap_chat(original_chat, self, *args, **kwargs)
        
        MistralClient.chat = patched_chat
        self._installed = True
    
    def uninstall(self) -> None:
        """Remove Mistral interception."""
        self._installed = False
    
    def _wrap_chat(self, original: Callable, client_self, *args, **kwargs) -> Any:
        """Wrap chat method."""
        start_ns = time.perf_counter_ns()
        
        model = kwargs.get('model', 'unknown')
        messages = kwargs.get('messages', [])
        params = {k: v for k, v in kwargs.items() if k not in ('model', 'messages')}
        
        try:
            response = original(client_self, *args, **kwargs)
            
            latency_ms = (time.perf_counter_ns() - start_ns) // 1_000_000
            
            call = MistralCall(
                model=model,
                messages=messages,
                params=params,
                response=self._serialize_response(response),
                streaming=False,
                latency_ms=latency_ms,
                timestamp_ns=start_ns
            )
            self._capture(call)
            
            return response
            
        except Exception as e:
            latency_ms = (time.perf_counter_ns() - start_ns) // 1_000_000
            call = MistralCall(
                model=model,
                messages=messages,
                params=params,
                response={"error": str(e), "type": type(e).__name__},
                streaming=False,
                latency_ms=latency_ms,
                timestamp_ns=start_ns
            )
            self._capture(call)
            raise
    
    def _serialize_response(self, response) -> Dict[str, Any]:
        """Serialize Mistral response."""
        if hasattr(response, 'model_dump'):
            return response.model_dump()
        elif hasattr(response, 'choices'):
            return {
                "choices": [
                    {"message": {"content": c.message.content}}
                    for c in response.choices
                ]
            }
        else:
            return {"content": str(response)}
