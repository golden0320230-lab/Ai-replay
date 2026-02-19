"""Ollama/local model HTTP interception."""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from ..base import CaptureEntry, InterceptorBase


class OllamaCall(CaptureEntry):
    """Captured Ollama API call."""
    
    def __init__(
        self,
        model: str,
        prompt: str,
        params: Dict[str, Any],
        response: Optional[Dict[str, Any]],
        streaming: bool,
        latency_ms: int,
        timestamp_ns: int
    ):
        super().__init__("llm.ollama", timestamp_ns)
        self.provider = "ollama"
        self.model = model
        self.prompt = prompt
        self.params = params
        self.response = response
        self.streaming = streaming
        self.latency_ms = latency_ms
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.entry_type,
            "provider": self.provider,
            "model": self.model,
            "prompt": self.prompt,
            "params": self.params,
            "response": self.response,
            "streaming": self.streaming,
            "latency_ms": self.latency_ms,
            "timestamp_ns": self.timestamp_ns,
        }


class OllamaInterceptor(InterceptorBase):
    """Intercepts Ollama API calls via HTTP."""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        super().__init__()
        self.base_url = base_url
    
    def install(self) -> None:
        """Install Ollama interception via HTTP capture."""
        # Ollama uses HTTP, so we rely on the HTTP interceptor
        # This is a marker for future enhancement
        self._installed = True
    
    def uninstall(self) -> None:
        """Remove Ollama interception."""
        self._installed = False
