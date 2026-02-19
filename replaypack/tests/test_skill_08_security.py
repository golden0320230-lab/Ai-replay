"""Test Skill 8: Security & Redaction.

Tests for API key masking, PII detection, secrets in nested JSON.
"""

import pytest

from replaypack.security import SecretDetector, RedactionEngine


class TestSecretDetection:
    """Test secret detection."""
    
    def test_detects_api_key(self):
        """API keys are detected."""
        detector = SecretDetector()
        text = "api_key=abc123def456ghi789jkl012mno345pqr678stu901vwx234yz"
        
        findings = detector.detect(text)
        
        assert len(findings) >= 1
        assert any(f['type'] == 'api_key' for f in findings)
    
    def test_detects_bearer_token(self):
        """Bearer tokens are detected."""
        detector = SecretDetector()
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        
        findings = detector.detect(text)
        
        assert any(f['type'] == 'bearer_token' for f in findings)
    
    def test_detects_email(self):
        """Email addresses are detected as PII."""
        detector = SecretDetector()
        text = "Contact user@example.com for support"
        
        findings = detector.detect(text)
        
        assert any(f['type'] == 'email' for f in findings)


class TestRedaction:
    """Test redaction."""
    
    def test_redacts_api_key(self):
        """API keys are redacted."""
        engine = RedactionEngine()
        text = "api_key=abc123def456ghi789jkl012mno345pqr678stu901vwx234yz"
        
        result = engine.redact(text)
        
        assert '[REDACTED]' in result
        assert 'abc123def456' not in result
    
    def test_redacts_nested_json(self):
        """Secrets in nested JSON are redacted."""
        engine = RedactionEngine()
        data = {
            "config": {
                "api_key": "sk_live_abc123def456ghi789",
                "nested": {
                    "token": "Bearer eyJhbGciOiJIUzI1NiJ9"
                }
            }
        }
        
        result = engine.redact_dict(data)
        
        assert '[REDACTED]' in result["config"]["api_key"]
        assert '[REDACTED]' in result["config"]["nested"]["token"]
    
    def test_preserves_structure(self):
        """Redaction preserves data structure."""
        engine = RedactionEngine()
        data = {
            "safe_key": "safe_value",
            "secret_key": "sk_live_abc123def456ghi789"
        }
        
        result = engine.redact_dict(data)
        
        assert result["safe_key"] == "safe_value"
        assert '[REDACTED]' in result["secret_key"]


class TestCustomPatterns:
    """Test custom regex patterns."""
    
    def test_custom_pattern(self):
        """Custom patterns can be added."""
        import re
        custom = {'custom_secret': re.compile(r'CUSTOM_[A-Z0-9]+')}
        detector = SecretDetector(custom_patterns=custom)
        
        text = "token=CUSTOM_ABC123"
        findings = detector.detect(text)
        
        assert any(f['type'] == 'custom_secret' for f in findings)
