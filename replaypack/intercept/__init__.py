"""Interception module for capturing LLM and HTTP calls."""

from .base import CaptureEntry, InterceptorBase, CompositeInterceptor
from .llm.openai import OpenAIInterceptor, OpenAICall
from .llm.anthropic import AnthropicInterceptor, AnthropicCall
from .llm.gemini import GeminiInterceptor, GeminiCall
from .llm.mistral import MistralInterceptor, MistralCall
from .llm.ollama import OllamaInterceptor, OllamaCall
from .http.requests import RequestsInterceptor, HTTPCall

__all__ = [
    'CaptureEntry',
    'InterceptorBase',
    'CompositeInterceptor',
    'OpenAIInterceptor',
    'OpenAICall',
    'AnthropicInterceptor',
    'AnthropicCall',
    'GeminiInterceptor',
    'GeminiCall',
    'MistralInterceptor',
    'MistralCall',
    'OllamaInterceptor',
    'OllamaCall',
    'RequestsInterceptor',
    'HTTPCall',
]


def create_default_interceptor() -> CompositeInterceptor:
    """Create interceptor with all available adapters."""
    composite = CompositeInterceptor()
    
    # Add LLM interceptors
    try:
        import openai  # noqa: F401
        composite.add(OpenAIInterceptor())
    except ImportError:
        pass
    
    try:
        import anthropic  # noqa: F401
        composite.add(AnthropicInterceptor())
    except ImportError:
        pass
    
    try:
        import google.generativeai  # noqa: F401
        composite.add(GeminiInterceptor())
    except ImportError:
        pass
    
    try:
        from mistralai.client import MistralClient  # noqa: F401
        composite.add(MistralInterceptor())
    except ImportError:
        pass
    
    # Add HTTP interceptors (covers Ollama)
    try:
        import requests  # noqa: F401
        composite.add(RequestsInterceptor())
    except ImportError:
        pass
    
    return composite
