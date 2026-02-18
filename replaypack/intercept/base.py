"""Base classes for interception."""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, Protocol, TypeVar, Union


class CaptureEntry:
    """Base class for captured entries."""
    
    def __init__(self, entry_type: str, timestamp_ns: int):
        self.entry_type = entry_type
        self.timestamp_ns = timestamp_ns
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        raise NotImplementedError


class CaptureBackend(Protocol):
    """Protocol for capture backends."""
    
    def store(self, entry: CaptureEntry) -> None:
        """Store a capture entry."""
        ...
    
    def get_all(self) -> List[CaptureEntry]:
        """Get all captured entries."""
        ...


class InterceptorBase(ABC):
    """Base class for all interceptors."""
    
    def __init__(self):
        self._installed = False
        self._originals: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._capture_backend: Optional[CaptureBackend] = None
    
    def set_backend(self, backend: CaptureBackend) -> None:
        """Set the capture backend."""
        self._capture_backend = backend
    
    @abstractmethod
    def install(self) -> None:
        """Install interception hooks."""
        pass
    
    @abstractmethod
    def uninstall(self) -> None:
        """Remove interception hooks."""
        pass
    
    def is_installed(self) -> bool:
        """Check if hooks are active."""
        with self._lock:
            return self._installed
    
    def _capture(self, entry: CaptureEntry) -> None:
        """Send capture to backend."""
        if self._capture_backend is not None:
            self._capture_backend.store(entry)


class CompositeInterceptor(InterceptorBase):
    """Combines multiple interceptors."""
    
    def __init__(self):
        super().__init__()
        self._interceptors: List[InterceptorBase] = []
    
    def add(self, interceptor: InterceptorBase) -> None:
        """Add an interceptor."""
        self._interceptors.append(interceptor)
        if self._capture_backend:
            interceptor.set_backend(self._capture_backend)
    
    def install(self) -> None:
        for interceptor in self._interceptors:
            interceptor.install()
        self._installed = True
    
    def uninstall(self) -> None:
        for interceptor in reversed(self._interceptors):
            interceptor.uninstall()
        self._installed = False
    
    def set_backend(self, backend: CaptureBackend) -> None:
        super().set_backend(backend)
        for interceptor in self._interceptors:
            interceptor.set_backend(backend)
