# .rpk Format Specification

## Overview

.rpk (ReplayPack) files are JSON-based artifacts containing recorded execution traces.

## Schema Version

Current: `1.0.0`

## File Structure

```json
{
  "_schema_version": "1.0.0",
  "_header": {
    "schema_version": "1.0.0",
    "created_at": "2024-02-19T12:00:00Z",
    "generator": "replaypack/0.1.0",
    "checksum": "sha256:..."
  },
  "_metadata": {
    "step_count": 5,
    "recording_count": 1
  },
  "recording": {
    "version": "1.0.0",
    "metadata": {},
    "steps": [
      {
        "id": "step_1",
        "sequence": 1,
        "function": "llm.openai",
        "args": [],
        "kwargs": {
          "model": "gpt-4",
          "messages": [...]
        },
        "result": {...},
        "exception": null,
        "hash": "abc123..."
      }
    ]
  }
}
```

## Step Types

- `llm.openai` - OpenAI API call
- `llm.anthropic` - Anthropic API call
- `llm.gemini` - Gemini API call
- `llm.mistral` - Mistral API call
- `llm.ollama` - Ollama/local model call
- `tool.*` - Tool/function call
- `http.request` - HTTP request

## Canonicalization Rules

1. **Key ordering**: All dict keys sorted alphabetically (recursive)
2. **Floats**: Normalized to 15 decimal places
3. **Timestamps**: ISO 8601 format, UTC
4. **Bytes**: Base64 encoded with prefix
5. **Nulls**: Preserved as `null`

## Hash Computation

```
hash = sha256(
  type + 
  canonical(input) + 
  canonical(output) + 
  stable_metadata
)
```

## Version Compatibility

- Forward compatibility: newer readers can read older artifacts
- Backward compatibility: explicit migration required

## Redaction

Sensitive fields are replaced with `[REDACTED]`:
- `Authorization` headers
- `api_key`, `token`, `secret` fields
- Email addresses
- Phone numbers
