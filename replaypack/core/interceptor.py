"""Function interception for recording."""

from __future__ import annotations

import functools
from typing import Any, Callable, Dict, TypeVar

from .recorder import Recorder

F = TypeVar('F', bound=Callable[..., Any])


def recordable(name: str = None) -> Callable[[F], F]:
    """Decorator to make a function recordable.
    
    When recording is active, calls to the decorated function
    are captured with args, kwargs, and results.
    
    Args:
        name: Optional override for function name in recording.
        
    Returns:
        Decorator function.
        
    Example:
        @recordable()
        def my_function(x, y):
            return x + y
            
        @recordable("custom_name")
        def another_function():
            pass
    """
    def decorator(func: F) -> F:
        func_name = name or func.__qualname__
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if Recorder.is_recording():
                try:
                    result = func(*args, **kwargs)
                    Recorder.record(func_name, args, kwargs, result=result)
                    return result
                except Exception as e:
                    Recorder.record(func_name, args, kwargs, exception=e)
                    raise
            else:
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


class Interceptor:
    """Generic function interceptor using monkeypatching.
    
    Allows interception of method calls on objects by replacing
    them with recording wrappers.
    """
    
    def __init__(self):
        self._originals: Dict[str, Callable] = {}
    
    def patch(self, obj: Any, attr: str, replacement: Callable) -> None:
        """Monkeypatch an object's method.
        
        Args:
            obj: Object to patch.
            attr: Attribute name to replace.
            replacement: New function to use.
        """
        key = f"{obj.__class__.__name__}.{attr}"
        self._originals[key] = getattr(obj, attr)
        setattr(obj, attr, replacement)
    
    def unpatch(self, obj: Any, attr: str) -> None:
        """Restore original method.
        
        Args:
            obj: Object that was patched.
            attr: Attribute name to restore.
        """
        key = f"{obj.__class__.__name__}.{attr}"
        if key in self._originals:
            setattr(obj, attr, self._originals[key])
            del self._originals[key]
    
    def unpatch_all(self) -> None:
        """Restore all patched methods."""
        # This would need to track (obj, attr) pairs
        # For now, just clear the cache
        self._originals.clear()
