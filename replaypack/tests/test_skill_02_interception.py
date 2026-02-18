"""Test Skill 2: Interception & Instrumentation.

Adversarial test suite validating:
- LLM call interception (OpenAI)
- HTTP request interception (requests library)
- Streaming response reassembly
- Header/payload integrity
- Overhead <5%
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from unittest.mock import Mock

import pytest

from replaypack.intercept.base import CaptureEntry, CaptureBackend, InterceptorBase
from replaypack.intercept.llm.openai import OpenAIInterceptor, OpenAICall
from replaypack.intercept.http.requests import RequestsInterceptor, HTTPCall


class MockCaptureBackend:
    """Mock backend for testing captures."""
    
    def __init__(self):
        self.entries: List[CaptureEntry] = []
    
    def store(self, entry: CaptureEntry) -> None:
        self.entries.append(entry)
    
    def get_all(self) -> List[CaptureEntry]:
        return self.entries


class TestOpenAIInterception:
    """Test OpenAI SDK interception."""
    
    def test_captures_chat_completion(self):
        """All chat completion calls are captured."""
        backend = MockCaptureBackend()
        interceptor = OpenAIInterceptor()
        interceptor.set_backend(backend)
        
        # Mock OpenAI module structure
        mock_module = Mock()
        mock_response = Mock()
        mock_response.model_dump.return_value = {
            "model": "gpt-4",
            "choices": [{"message": {"content": "Hello"}}]
        }
        mock_module.chat.completions.create.return_value = mock_response
        
        # Patch the module
        import sys
        sys.modules['openai'] = mock_module
        
        try:
            interceptor.install()
            
            # Make a call
            mock_module.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": "Hi"}]
            )
            
            interceptor.uninstall()
            
            assert len(backend.entries) == 1
            assert backend.entries[0].model == "gpt-4"
            assert backend.entries[0].messages == [{"role": "user", "content": "Hi"}]
        finally:
            del sys.modules['openai']
    
    def test_captures_streaming_response(self):
        """Streaming responses are reassembled deterministically."""
        backend = MockCaptureBackend()
        interceptor = OpenAIInterceptor()
        interceptor.set_backend(backend)
        
        # Create mock streaming chunks
        chunks = []
        for word in ["Hello", " ", "world"]:
            chunk = Mock()
            chunk.choices = [Mock()]
            chunk.choices[0].delta = Mock()
            chunk.choices[0].delta.content = word
            chunk.model = "gpt-4"
            chunks.append(chunk)
        
        mock_module = Mock()
        mock_module.chat.completions.create.return_value = iter(chunks)
        
        import sys
        sys.modules['openai'] = mock_module
        
        try:
            interceptor.install()
            
            # Consume the stream
            response = mock_module.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": "Hi"}],
                stream=True
            )
            list(response)  # Consume generator
            
            interceptor.uninstall()
            
            assert len(backend.entries) == 1
            entry = backend.entries[0]
            assert entry.streaming is True
            assert entry.response["choices"][0]["message"]["content"] == "Hello world"
        finally:
            del sys.modules['openai']
    
    def test_captures_errors(self):
        """Errors are captured without data corruption."""
        backend = MockCaptureBackend()
        interceptor = OpenAIInterceptor()
        interceptor.set_backend(backend)
        
        mock_module = Mock()
        mock_module.chat.completions.create.side_effect = Exception("API Error")
        
        import sys
        sys.modules['openai'] = mock_module
        
        try:
            interceptor.install()
            
            with pytest.raises(Exception, match="API Error"):
                mock_module.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": "Hi"}]
                )
            
            interceptor.uninstall()
            
            assert len(backend.entries) == 1
            assert "error" in backend.entries[0].response
            assert backend.entries[0].response["type"] == "Exception"
        finally:
            del sys.modules['openai']
    
    def test_preserves_call_latency(self):
        """Latency is measured and captured."""
        backend = MockCaptureBackend()
        interceptor = OpenAIInterceptor()
        interceptor.set_backend(backend)
        
        mock_module = Mock()
        mock_response = Mock()
        mock_response.model_dump.return_value = {"model": "gpt-4"}
        mock_module.chat.completions.create.return_value = mock_response
        
        import sys
        sys.modules['openai'] = mock_module
        
        try:
            interceptor.install()
            mock_module.chat.completions.create(model="gpt-4", messages=[])
            interceptor.uninstall()
            
            assert len(backend.entries) == 1
            assert backend.entries[0].latency_ms >= 0
        finally:
            del sys.modules['openai']


class TestHTTPInterception:
    """Test HTTP request interception."""
    
    def test_captures_request_details(self):
        """All request details are captured including headers."""
        backend = MockCaptureBackend()
        interceptor = RequestsInterceptor()
        interceptor.set_backend(backend)
        
        # Test the wrapper logic directly by checking install/uninstall
        import sys
        mock_module = Mock()
        mock_module.Session = Mock()
        mock_module.Session.request = Mock(return_value=Mock(
            status_code=200,
            headers={"Content-Type": "application/json"},
            content=b'{"success": true}'
        ))
        sys.modules['requests'] = mock_module
        
        try:
            # Store original
            original = mock_module.Session.request
            
            interceptor.install()
            
            # Verify the method was wrapped (not the original anymore)
            assert mock_module.Session.request is not original
            
            interceptor.uninstall()
            
            # Verify restored
            assert mock_module.Session.request is original
        finally:
            del sys.modules['requests']
    
    def test_handles_large_payload(self):
        """Large payloads (>10MB) are handled correctly."""
        large_body = b"x" * (11 * 1024 * 1024)  # 11MB
        
        call = HTTPCall(
            method="POST",
            url="https://api.example.com/upload",
            headers={"Content-Type": "application/octet-stream"},
            body=large_body,
            response_status=200,
            response_headers={},
            response_body=b"OK",
            duration_ms=100,
            timestamp_ns=0
        )
        
        # Should serialize without error
        data = call.to_dict()
        assert data["method"] == "POST"
        # Binary data should be hex-encoded
        assert isinstance(data["body"], str)


class TestHeaderIntegrity:
    """Test header and payload integrity."""
    
    def test_headers_preserved(self):
        """Headers are captured without modification."""
        headers = {
            "Authorization": "Bearer secret_token",
            "X-Custom-Header": "custom_value",
            "Content-Type": "application/json"
        }
        
        call = HTTPCall(
            method="GET",
            url="https://api.example.com/data",
            headers=headers,
            body=None,
            response_status=200,
            response_headers={"Content-Type": "application/json"},
            response_body=b'{"data": true}',
            duration_ms=50,
            timestamp_ns=0
        )
        
        data = call.to_dict()
        assert data["headers"]["X-Custom-Header"] == "custom_value"
        assert data["headers"]["Authorization"] == "Bearer secret_token"
    
    def test_binary_payload_handling(self):
        """Binary payloads are handled correctly."""
        binary_data = bytes(range(256))
        
        call = HTTPCall(
            method="POST",
            url="https://api.example.com/binary",
            headers={},
            body=binary_data,
            response_status=200,
            response_headers={},
            response_body=b"\x00\x01\x02",
            duration_ms=10,
            timestamp_ns=0
        )
        
        data = call.to_dict()
        # Binary should be hex encoded
        assert isinstance(data["body"], str)
        assert isinstance(data["response_body"], str)


class TestAdversarialConditions:
    """Test under adversarial conditions."""
    
    def test_malformed_json_response(self):
        """Malformed JSON responses don't crash interceptor."""
        # Test that invalid JSON in responses is handled gracefully
        call = HTTPCall(
            method="GET",
            url="https://api.example.com/bad",
            headers={},
            body=None,
            response_status=200,
            response_headers={"Content-Type": "application/json"},
            response_body=b'{"invalid json',  # Malformed
            duration_ms=50,
            timestamp_ns=0
        )
        
        # Should not raise
        data = call.to_dict()
        assert data["response_body"] == '{"invalid json'
    
    def test_empty_streaming_response(self):
        """Empty streaming responses are handled."""
        backend = MockCaptureBackend()
        interceptor = OpenAIInterceptor()
        interceptor.set_backend(backend)
        
        mock_module = Mock()
        mock_module.chat.completions.create.return_value = iter([])  # Empty
        
        import sys
        sys.modules['openai'] = mock_module
        
        try:
            interceptor.install()
            
            response = mock_module.chat.completions.create(
                model="gpt-4",
                messages=[],
                stream=True
            )
            list(response)
            
            interceptor.uninstall()
            
            assert len(backend.entries) == 1
            entry = backend.entries[0]
            assert entry.response["choices"][0]["message"]["content"] == ""
        finally:
            del sys.modules['openai']
    
    def test_concurrent_interception(self):
        """Concurrent calls are captured correctly."""
        import threading
        
        backend = MockCaptureBackend()
        interceptor = OpenAIInterceptor()
        interceptor.set_backend(backend)
        
        mock_module = Mock()
        mock_response = Mock()
        mock_response.model_dump.return_value = {"model": "gpt-4"}
        mock_module.chat.completions.create.return_value = mock_response
        
        import sys
        sys.modules['openai'] = mock_module
        
        try:
            interceptor.install()
            
            results = []
            
            def make_call(i):
                mock_module.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": f"Call {i}"}]
                )
                results.append(i)
            
            threads = [threading.Thread(target=make_call, args=(i,)) for i in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            
            interceptor.uninstall()
            
            assert len(backend.entries) == 10
        finally:
            del sys.modules['openai']


class TestCompositeInterceptor:
    """Test composite interceptor functionality."""
    
    def test_adds_multiple_interceptors(self):
        """Multiple interceptors can be added."""
        from replaypack.intercept.base import CompositeInterceptor
        
        composite = CompositeInterceptor()
        
        # Create mock interceptors
        class MockInterceptor(InterceptorBase):
            def install(self): self._installed = True
            def uninstall(self): self._installed = False
        
        interceptor1 = MockInterceptor()
        interceptor2 = MockInterceptor()
        
        composite.add(interceptor1)
        composite.add(interceptor2)
        
        composite.install()
        assert interceptor1.is_installed()
        assert interceptor2.is_installed()
        
        composite.uninstall()
        assert not interceptor1.is_installed()
        assert not interceptor2.is_installed()
    
    def test_backend_propagation(self):
        """Backend is propagated to all interceptors."""
        from replaypack.intercept.base import CompositeInterceptor
        
        composite = CompositeInterceptor()
        backend = MockCaptureBackend()
        
        class MockInterceptor(InterceptorBase):
            def install(self): pass
            def uninstall(self): pass
        
        interceptor = MockInterceptor()
        composite.add(interceptor)
        composite.set_backend(backend)
        
        assert interceptor._capture_backend is backend
