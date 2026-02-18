"""Interception module for capturing LLM and HTTP calls."""

from .base import CaptureEntry, InterceptorBase, CompositeInterceptor

__all__ = [
    'CaptureEntry',
    'InterceptorBase',
    'CompositeInterceptor',
]


def create_default_interceptor() -> CompositeInterceptor:
    """Create interceptor with all available adapters."""
    from .llm.openai import OpenAIInterceptor
    from .http.requests import RequestsInterceptor
    
    composite = CompositeInterceptor()
    
    # Add LLM interceptors
    try:
        import openai  # noqa: F401
        composite.add(OpenAIInterceptor())
    except ImportError:
        pass
    
    # Add HTTP interceptors
    try:
        import requests  # noqa: F401
        composite.add(RequestsInterceptor())
    except ImportError:
        pass
    
    return composite
