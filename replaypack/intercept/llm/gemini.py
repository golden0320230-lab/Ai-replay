"""Google Gemini SDK interception."""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional
from types import ModuleType

from ..base import CaptureEntry, InterceptorBase


class GeminiCall(CaptureEntry):
    """Captured Gemini API call."""
    
    def __init__(
        self,
        model: str,
        contents: List[Dict[str, Any]],
        params: Dict[str, Any],
        response: Optional[Dict[str, Any]],
        streaming: bool,
        latency_ms: int,
        timestamp_ns: int
    ):
        super().__init__("llm.gemini", timestamp_ns)
        self.provider = "gemini"
        self.model = model
        self.contents = contents
        self.params = params
        self.response = response
        self.streaming = streaming
        self.latency_ms = latency_ms
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.entry_type,
            "provider": self.provider,
            "model": self.model,
            "contents": self.contents,
            "params": self.params,
            "response": self.response,
            "streaming": self.streaming,
            "latency_ms": self.latency_ms,
            "timestamp_ns": self.timestamp_ns,
        }


class GeminiInterceptor(InterceptorBase):
    """Intercepts Google Gemini SDK calls."""
    
    def __init__(self):
        super().__init__()
        self._genai_module: Optional[ModuleType] = None
    
    def install(self) -> None:
        """Install Gemini interception."""
        try:
            import google.generativeai as genai
        except ImportError:
            return  # Gemini not installed
        
        self._genai_module = genai
        
        # Patch GenerativeModel.generate_content
        if hasattr(genai, 'GenerativeModel'):
            original_generate = genai.GenerativeModel.generate_content
            
            def patched_generate(model_self, *args, **kwargs):
                return self._wrap_generate(original_generate, model_self, *args, **kwargs)
            
            genai.GenerativeModel.generate_content = patched_generate
        
        self._installed = True
    
    def uninstall(self) -> None:
        """Remove Gemini interception."""
        self._installed = False
    
    def _wrap_generate(self, original: Callable, model_self, *args, **kwargs) -> Any:
        """Wrap generate_content method."""
        start_ns = time.perf_counter_ns()
        
        model_name = getattr(model_self, 'model_name', 'unknown')
        contents = args[0] if args else kwargs.get('contents', [])
        params = {k: v for k, v in kwargs.items() if k != 'contents'}
        streaming = kwargs.get('stream', False)
        
        try:
            response = original(model_self, *args, **kwargs)
            
            latency_ms = (time.perf_counter_ns() - start_ns) // 1_000_000
            
            call = GeminiCall(
                model=model_name,
                contents=contents if isinstance(contents, list) else [contents],
                params=params,
                response=self._serialize_response(response),
                streaming=streaming,
                latency_ms=latency_ms,
                timestamp_ns=start_ns
            )
            self._capture(call)
            
            return response
            
        except Exception as e:
            latency_ms = (time.perf_counter_ns() - start_ns) // 1_000_000
            call = GeminiCall(
                model=model_name,
                contents=contents if isinstance(contents, list) else [contents],
                params=params,
                response={"error": str(e), "type": type(e).__name__},
                streaming=streaming,
                latency_ms=latency_ms,
                timestamp_ns=start_ns
            )
            self._capture(call)
            raise
    
    def _serialize_response(self, response) -> Dict[str, Any]:
        """Serialize Gemini response."""
        if hasattr(response, 'to_dict'):
            return response.to_dict()
        elif hasattr(response, 'text'):
            return {"text": response.text}
        else:
            return {"content": str(response)}
