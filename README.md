# ReplayPack

**Git-diff debugging + deterministic replay for AI workflows.**

ReplayPack records LLM + tool executions into a portable `.rpk` file, lets you **replay runs offline**, and shows a **GitHub-style diff** to pinpoint the **first divergence** when behavior changes.

> If you've ever asked: "Why did my AI output change?"  
> ReplayPack answers: **"It changed here."**

---

## Why ReplayPack exists

AI workflows break in ways that normal logs can't solve:
- model/provider drift
- prompt rendering changes
- tool/API responses changing
- retrieval context changing
- retries/streaming edge cases
- dependency upgrades changing behavior

Most tooling can tell you *what happened*.  
ReplayPack lets you **reproduce it**, **diff it**, and **gate it in CI**.

---

## Key features (debugging-first)

- **One-line install** and start recording
- **Portable `.rpk` replay artifact** (human-readable JSON)
- **Offline stub replay** (no API calls)
- **Hybrid replay** (rerun model or tools selectively)
- **Git-diff UI** for:
  - rendered prompts
  - model outputs
  - tool args/results (JSON)
  - model params
- **First divergence detection**
- **Shareable redacted bundles**
- **CI assertions** (fail builds on behavior drift)

---

## Install

```bash
pip install replaypack
```

## Quickstart

### 1) Record a run

```python
import replaypack

with replaypack.record():
    # Your AI workflow here
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "Hello"}]
    )
    print(response.choices[0].message.content)
```

Or use the CLI:
```bash
replaypack record app.py
```

### 2) Replay offline (stubbed)

```bash
replaypack replay runs/20240219_120000.rpk
```

### 3) Diff two runs (find first divergence)

```bash
replaypack diff runs/a.rpk runs/b.rpk --first-divergence
```

### 4) Export a shareable repro bundle (redacted)

```bash
replaypack bundle runs/a.rpk --redact default --out incident.bundle
replaypack replay incident.bundle
```

### 5) Local Git-diff UI

```bash
replaypack ui
```

- **Left:** step list ✅ 🟡 🔴
- **Center:** Git-style diff viewer
- **Right:** "What changed?" summary + jump to first divergence

---

## Works with any LLM

ReplayPack supports:

**Hosted APIs:**
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Google Gemini
- Mistral AI
- Azure OpenAI
- Any OpenAI-compatible API

**Local models:**
- Ollama
- Any HTTP-based local server

**Frameworks:**
- Raw SDK usage
- LangChain (via interceptors)
- LlamaIndex (via interceptors)
- Custom agents

If it can be called, it can be recorded.

---

## Python API

```python
import replaypack

# Start recording
replaypack.init()

# Your code here
response = openai.chat.completions.create(...)

# Stop and save
replaypack.stop()

# Or use context manager
with replaypack.record():
    # Your code here
    pass

# Mark functions as tools
@replaypack.tool()
def search_database(query: str):
    return db.search(query)
```

---

## CLI usage

```bash
# Record (plug-and-play, no code changes needed)
replaypack record -- python app.py

# Replay offline
replaypack replay run.rpk

# Diff with first divergence
replaypack diff run1.rpk run2.rpk --first-divergence

# Assert (CI - non-zero exit on divergence)
replaypack assert baseline.rpk current.rpk

# Bundle with redaction
replaypack bundle run.rpk --redact default --out repro.rpk

# Launch local UI
replaypack ui --host 127.0.0.1 --port 8080
```

### Environment variables

- `REPLAYPACK_OUTPUT_DIR` - Default output directory (default: `./runs`)
- `REPLAYPACK_MAX_STEPS` - Maximum steps per session (default: 10000)
- `REPLAYPACK_MAX_MB` - Maximum artifact size in MB (default: 50)

---

## CI usage (behavior regression gate)

```yaml
# .github/workflows/replaypack.yml
- name: Check for behavior drift
  run: |
    pip install replaypack
    replaypack record -- python test_workflow.py
    replaypack assert baseline.rpk runs/latest.rpk
```

Non-zero exit code if behavior diverges.

---

## Artifact format (.rpk)

Replay artifacts are human-readable JSON:

```json
{
  "_schema_version": "1.0.0",
  "_header": {
    "schema_version": "1.0.0",
    "created_at": "2024-02-19T12:00:00Z",
    "generator": "replaypack/0.1.0"
  },
  "recording": {
    "steps": [
      {
        "sequence": 1,
        "function": "llm.openai",
        "args": [],
        "kwargs": {"model": "gpt-4", "messages": [...]},
        "result": {...},
        "hash": "abc123..."
      }
    ]
  }
}
```

---

## Privacy & Security

Redaction modes:
- `none` - No redaction
- `default` - Mask PII, API keys, tokens
- `custom` - User-defined rules

```python
# Redact before sharing
replaypack bundle run.rpk --redact default --out safe.rpk
```

---

## What ReplayPack is NOT

- Not an agent framework
- Not a prompt manager
- Not an observability SaaS
- Not a wrapper UI

ReplayPack is a **debugger for AI behavior**.

---

## License

MIT
