"""Anthropic SDK interception."""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional
from types import ModuleType

from ..base import CaptureEntry, InterceptorBase


class AnthropicCall(CaptureEntry):
    """Captured Anthropic API call."""
    
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
        super().__init__("llm.anthropic", timestamp_ns)
        self.provider = "anthropic"
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


class AnthropicInterceptor(InterceptorBase):
    """Intercepts Anthropic SDK calls."""
    
    def __init__(self):
        super().__init__()
        self._anthropic_module: Optional[ModuleType] = None
        self._original_create: Optional[Callable] = None
    
    def install(self) -> None:
        """Install Anthropic interception."""
        try:
            import anthropic
        except ImportError:
            return  # Anthropic not installed
        
        self._anthropic_module = anthropic
        
        # Intercept messages.create
        if hasattr(anthropic, 'Anthropic'):
            original_init = anthropic.Anthropic.__init__
            
            def patched_init(client_self, *args, **kwargs):
                original_init(client_self, *args, **kwargs)
                # Patch the messages.create method on this instance
                original_create = client_self.messages.create
                client_self.messages.create = self._wrap_create(original_create)
            
            anthropic.Anthropic.__init__ = patched_init
        
        self._installed = True
    
    def uninstall(self) -> None:
        """Remove Anthropic interception."""
        # Restoration is complex due to instance patching
        # For MVP, we rely on process restart for cleanup
        self._installed = False
    
    def _wrap_create(self, original: Callable) -> Callable:
        """Wrap messages.create method."""
        
        def wrapped(*args, **kwargs):
            start_ns = time.perf_counter_ns()
            
            model = kwargs.get('model', 'unknown')
            messages = kwargs.get('messages', [])
            params = {k: v for k, v in kwargs.items() 
                     if k not in ('model', 'messages')}
            streaming = kwargs.get('stream', False)
            
            try:
                response = original(*args, **kwargs)
                
                if streaming:
                    return self._wrap_streaming_response(
                        response, model, messages, params, start_ns
                    )
                
                latency_ms = (time.perf_counter_ns() - start_ns) // 1_000_000
                
                call = AnthropicCall(
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
                call = AnthropicCall(
                    model=model,
                    messages=messages,
                    params=params,
                    response={"error": str(e), "type": type(e).__name__},
                    streaming=streaming,
                    latency_ms=latency_ms,
                    timestamp_ns=start_ns
                )
                self._capture(call)
                raise
        
        return wrapped
    
    def _wrap_streaming_response(self, response, model, messages, params, start_ns):
        """Wrap streaming response."""
        chunks = []
        
        def chunk_generator():
            for chunk in response:
                chunks.append(chunk)
                yield chunk
            
            latency_ms = (time.perf_counter_ns() - start_ns) // 1_000_000
            full_response = self._reassemble_streaming_chunks(chunks)
            
            call = AnthropicCall(
                model=model,
                messages=messages,
                params=params,
                response=full_response,
                streaming=True,
                latency_ms=latency_ms,
                timestamp_ns=start_ns
            )
            self._capture(call)
        
        return chunk_generator()
    
    def _serialize_response(self, response) -> Dict[str, Any]:
        """Serialize Anthropic response."""
        if hasattr(response, 'model_dump'):
            return response.model_dump()
        elif hasattr(response, 'to_dict'):
            return response.to_dict()
        else:
            return {
                "content": str(response),
                "type": getattr(response, 'type', 'unknown')
            }
    
    def _reassemble_streaming_chunks(self, chunks: List[Any]) -> Dict[str, Any]:
        """Reassemble streaming chunks."""
        content_parts = []
        
        for chunk in chunks:
            if hasattr(chunk, 'delta') and hasattr(chunk.delta, 'text'):
                content_parts.append(chunk.delta.text)
            elif hasattr(chunk, 'text'):
                content_parts.append(chunk.text)
        
        return {
            "content": "".join(content_parts),
            "role": "assistant"
        }
