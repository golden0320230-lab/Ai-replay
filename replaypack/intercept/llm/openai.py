"""OpenAI SDK interception."""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional
from types import ModuleType

from ..base import CaptureEntry, InterceptorBase


class OpenAICall(CaptureEntry):
    """Captured OpenAI API call."""
    
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
        super().__init__("llm.openai", timestamp_ns)
        self.provider = "openai"
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


class OpenAIInterceptor(InterceptorBase):
    """Intercepts OpenAI SDK calls."""
    
    def __init__(self):
        super().__init__()
        self._openai_module: Optional[ModuleType] = None
        self._original_chat_completion: Optional[Callable] = None
    
    def install(self) -> None:
        """Install OpenAI interception."""
        import openai
        self._openai_module = openai
        
        # Intercept chat completions
        if hasattr(openai, 'chat') and hasattr(openai.chat, 'completions'):
            self._original_chat_completion = openai.chat.completions.create
            openai.chat.completions.create = self._wrap_chat_completion(
                self._original_chat_completion
            )
        elif hasattr(openai, 'ChatCompletion'):
            # Legacy API
            self._original_chat_completion = openai.ChatCompletion.create
            openai.ChatCompletion.create = self._wrap_chat_completion(
                self._original_chat_completion
            )
        
        self._installed = True
    
    def uninstall(self) -> None:
        """Remove OpenAI interception."""
        if self._openai_module is None:
            return
        
        if self._original_chat_completion:
            if hasattr(self._openai_module, 'chat'):
                self._openai_module.chat.completions.create = self._original_chat_completion
            elif hasattr(self._openai_module, 'ChatCompletion'):
                self._openai_module.ChatCompletion.create = self._original_chat_completion
        
        self._installed = False
    
    def _wrap_chat_completion(self, original: Callable) -> Callable:
        """Wrap chat completion method."""
        
        def wrapped(*args, **kwargs):
            start_ns = time.perf_counter_ns()
            
            # Extract call parameters
            model = kwargs.get('model', args[0] if args else 'unknown')
            messages = kwargs.get('messages', [])
            params = {k: v for k, v in kwargs.items() 
                     if k not in ('model', 'messages')}
            streaming = kwargs.get('stream', False)
            
            try:
                response = original(*args, **kwargs)
                
                # Handle streaming responses
                if streaming:
                    return self._wrap_streaming_response(
                        response, model, messages, params, start_ns
                    )
                
                # Non-streaming: capture immediately
                latency_ms = (time.perf_counter_ns() - start_ns) // 1_000_000
                
                # Serialize response
                response_dict = self._serialize_response(response)
                
                call = OpenAICall(
                    model=model,
                    messages=messages,
                    params=params,
                    response=response_dict,
                    streaming=False,
                    latency_ms=latency_ms,
                    timestamp_ns=start_ns
                )
                self._capture(call)
                
                return response
                
            except Exception as e:
                # Capture error
                latency_ms = (time.perf_counter_ns() - start_ns) // 1_000_000
                call = OpenAICall(
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
        """Wrap streaming response to capture chunks."""
        chunks = []
        
        def chunk_generator():
            for chunk in response:
                chunks.append(chunk)
                yield chunk
            
            # After stream completes, capture
            latency_ms = (time.perf_counter_ns() - start_ns) // 1_000_000
            
            # Reassemble chunks into full response
            full_response = self._reassemble_streaming_chunks(chunks)
            
            call = OpenAICall(
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
        """Serialize OpenAI response to dict."""
        if hasattr(response, 'model_dump'):
            return response.model_dump()
        elif hasattr(response, 'to_dict'):
            return response.to_dict()
        else:
            return {"content": str(response)}
    
    def _reassemble_streaming_chunks(self, chunks: List[Any]) -> Dict[str, Any]:
        """Reassemble streaming chunks into full response."""
        content_parts = []
        model = None
        
        for chunk in chunks:
            if hasattr(chunk, 'choices') and chunk.choices:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content:
                    content_parts.append(delta.content)
                if hasattr(chunk, 'model'):
                    model = chunk.model
        
        return {
            "model": model,
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "".join(content_parts)
                }
            }]
        }
