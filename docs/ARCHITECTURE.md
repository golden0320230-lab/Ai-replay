# ReplayPack Architecture

## Module Boundaries

```
replaypack/
├── capture/          # Interceptors and event emission
│   ├── llm/         # LLM SDK adapters
│   └── http/        # HTTP client interception
├── artifact/        # .rpk format, reader/writer
├── replay/          # Stub/hybrid replay engine
├── diff/            # Comparison and divergence detection
├── cli/             # Command-line interface
└── ui/              # Local web UI
```

## Data Flow

```
User App → Interceptors → RunContext → Steps → Artifact(.rpk)
                                            ↓
Replay ← Stub Interceptors ← ReplayEngine ←┘
                                            ↓
DiffEngine ← Compare Artifacts → Divergence
```

## Core Components

### Capture Layer
- Monkeypatches SDK methods (OpenAI, Anthropic, etc.)
- Wraps HTTP clients (requests, httpx)
- Emits ordered events to RunContext

### Artifact Layer
- Canonical JSON serialization
- Deterministic hashing
- Versioned schema
- Redaction support

### Replay Layer
- Interceptor registry
- Stub mode: returns recorded outputs
- Hybrid mode: selective rerun

### Diff Layer
- Step-level hash comparison
- Text diff (line/word)
- JSON diff (pointer paths)
- First divergence detection

## Interfaces

### Step
```python
class Step:
    id: str
    type: str  # model.request, tool.call, etc.
    input: CanonicalJSON
    output: CanonicalJSON
    hash: str  # sha256 of canonical form
```

### Artifact
```python
class Artifact:
    version: str
    steps: List[Step]
    metadata: Dict
    
    def save(path)
    def load(path) -> Artifact
```

## Extension Points

- Custom LLM adapters
- Custom redaction rules
- Custom diff renderers
