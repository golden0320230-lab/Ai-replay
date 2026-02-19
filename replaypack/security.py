"""Security and redaction module.

Protects sensitive data in artifacts.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Pattern


class SecretDetector:
    """Detects secrets in data using regex patterns."""
    
    # Default patterns for common secrets
    DEFAULT_PATTERNS = {
        'api_key': re.compile(r'sk_[a-zA-Z0-9_]{10,}|[a-zA-Z0-9]{32,}', re.IGNORECASE),
        'bearer_token': re.compile(r'Bearer\s+([a-zA-Z0-9\-_\.]+)', re.IGNORECASE),
        'private_key': re.compile(r'-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----'),
        'password': re.compile(r'password[\s=:]+([^\s]+)', re.IGNORECASE),
        'email': re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
    }
    
    def __init__(self, custom_patterns: Optional[Dict[str, Pattern]] = None):
        """Initialize detector.
        
        Args:
            custom_patterns: Additional regex patterns to use.
        """
        self.patterns = {**self.DEFAULT_PATTERNS}
        if custom_patterns:
            self.patterns.update(custom_patterns)
    
    def detect(self, text: str) -> List[Dict[str, any]]:
        """Detect secrets in text.
        
        Args:
            text: Text to scan.
            
        Returns:
            List of detected secrets with type and position.
        """
        findings = []
        for secret_type, pattern in self.patterns.items():
            for match in pattern.finditer(text):
                findings.append({
                    'type': secret_type,
                    'start': match.start(),
                    'end': match.end(),
                    'value': match.group(),
                })
        return findings


class RedactionEngine:
    """Redacts secrets from data."""
    
    def __init__(self, detector: Optional[SecretDetector] = None):
        """Initialize engine.
        
        Args:
            detector: Secret detector to use.
        """
        self.detector = detector or SecretDetector()
    
    def redact(self, text: str, replacement: str = '[REDACTED]') -> str:
        """Redact secrets from text.
        
        Args:
            text: Text to redact.
            replacement: Replacement string.
            
        Returns:
            Redacted text.
        """
        findings = self.detector.detect(text)
        # Sort by position in reverse to avoid offset issues
        findings.sort(key=lambda x: x['start'], reverse=True)
        
        result = text
        for finding in findings:
            result = result[:finding['start']] + replacement + result[finding['end']:]
        
        return result
    
    def redact_dict(self, data: Dict, replacement: str = '[REDACTED]') -> Dict:
        """Redact secrets from dictionary recursively.
        
        Args:
            data: Dictionary to redact.
            replacement: Replacement string.
            
        Returns:
            Redacted dictionary.
        """
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self.redact(value, replacement)
            elif isinstance(value, dict):
                result[key] = self.redact_dict(value, replacement)
            elif isinstance(value, list):
                result[key] = [
                    self.redact(item, replacement) if isinstance(item, str)
                    else self.redact_dict(item, replacement) if isinstance(item, dict)
                    else item
                    for item in value
                ]
            else:
                result[key] = value
        return result
