# SRT Processor Issues and Fixes

## Overview

This note documents the issues found in the SRT processor and how they were fixed.

---

## Issue 1: Incomplete Output (Truncated at Middle)

### What Happened

The original code used a hardcoded `max_tokens=4000` in the `process()` method:

```python
def process(self, prompt: str, temperature: float = 0.7, max_tokens: int = 4000) -> str:
    # ...
```

The AI model would stop generating after 4000 tokens, cutting off the output mid-sentence.

### Additional Problem

Alibaba API has a strict limit: `max_tokens` must be ≤ 8192. When increased to 16000:

```
Error: Range of max_tokens should be [1, 8192]
```

### How Fixed

#### 1. Per-Provider Configuration

Made `max_tokens` configurable per-provider in `config.yaml`:

```yaml
providers:
  - name: alibaba
    base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
    model: qwen3-8b
    max_tokens: 8000      # Alibaba's limit

  - name: openrouter
    base_url: https://openrouter.ai/api/v1
    model: qwen/qwen3-8b
    max_tokens: 16000    # Higher limit for other providers
```

#### 2. Chunked Processing for Large Files

For files >12KB, implemented sentence-boundary chunking:

```python
MAX_CHUNK_SIZE = 12000

def split_text_into_chunks(text: str, max_size: int = MAX_CHUNK_SIZE) -> list[str]:
    # Split at sentence boundaries (.!?)
    sentences = re.split(r'(?<=[。.!?])\s*', text)
    chunks = []
    current_chunk = []
    current_size = 0
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        sent_size = len(sentence)
        if current_size + sent_size + 1 > max_size and current_chunk:
            chunks.append(' '.join(current_chunk))
            current_chunk = []
            current_size = 0
        current_chunk.append(sentence)
        current_size += sent_size + 1
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks
```

Processing flow:

```python
def process_large_text(providers, raw_text: str, config: dict) -> tuple[str, str]:
    if len(raw_text) <= MAX_CHUNK_SIZE:
        # Single request for small files
        return process_with_fallback(providers, prompt, config)
    
    # Split and process each chunk
    chunks = split_text_into_chunks(raw_text)
    results = []
    
    for i, chunk in enumerate(chunks):
        result, provider = process_with_fallback(providers, prompt, config)
        results.append(result)
        # Rate limiting between chunks
        time.sleep(delay)
    
    return '\n\n'.join(results), provider
```

---

## Issue 2: Connection Pool Leak

### What Happened

Commit `3d87055` attempted to fix pool leaks but was incomplete:

1. `__del__` is unreliable - Python doesn't guarantee when it runs
2. No explicit cleanup when program ends or encounters errors
3. `close()` could be called multiple times (no idempotency check)

### Original Broken Code

```python
class BaseProvider(ABC):
    def __init__(self, config: dict, ...):
        http_client = httpx.Client(...)  # Not stored as instance var!
        self.client = OpenAI(..., http_client=http_client)
    
    def __del__(self):
        try:
            self.close()  # But self.http_client doesn't exist!
        except:
            pass
```

### How Fixed

#### 1. Store http_client as Instance Variable

```python
self.http_client = httpx.Client(
    limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
    timeout=httpx.Timeout(timeout),
    ...
)
self.client = OpenAI(..., http_client=self.http_client)
```

#### 2. Made close() Idempotent

```python
def close(self):
    if hasattr(self, 'http_client') and self.http_client:
        self.http_client.close()
        self.http_client = None  # Prevent double-close
```

#### 3. Added Context Manager Support

```python
def __enter__(self):
    return self

def __exit__(self, exc_type, exc_val, exc_tb):
    self.close()
    return False
```

Usage:
```python
with AlibabaProvider(config, timeout) as provider:
    result = provider.process(prompt)
```

#### 4. Explicit Cleanup in main()

```python
def main():
    providers = get_enabled_providers(config)
    
    try:
        for srt_file in srt_files:
            # process files...
    finally:
        for provider in providers:
            try:
                provider.close()
            except Exception:
                pass
```

---

## Issue 3: Large Files Timing Out

### What Happened

The largest file `10A_Comp_Light_Probes.srt` (31KB raw text) would timeout after 10 minutes because:
- API takes longer to process more tokens
- Single request with 31KB input + expected output exceeded reasonable timeout

### How Fixed

Same chunked processing solution as Issue 1.

Example transformation:
```
Before: 31KB single request → Timeout

After:  
  Chunk 1: 12KB (11,917 chars) → 42s via alibaba
  Chunk 2: 12KB (11,979 chars) → 45s via alibaba
  Chunk 3:  8KB ( 7,548 chars) → 24s via alibaba
  Total: 31KB combined output, complete
```

---

## Visual Summary

```
Before:
┌─────────────────────────────────────────────┐
│ Input: 31KB text                            │
│                                             │
│ Request (max_tokens=4000)                   │
│      ↓                                      │
│ API returns 4KB... STOPS MID-SENTENCE       │
│      ↓                                      │
│ Output: Incomplete (truncated)              │
│                                             │
│ Also: http_client never closed → pool leak  │
└─────────────────────────────────────────────┘

After:
┌─────────────────────────────────────────────┐
│ Input: 31KB text                            │
│      ↓                                      │
│ Split: [12KB] [12KB] [7KB]                  │
│      ↓          ↓         ↓                 │
│ API1       API2       API3                  │
│ (8000tok)  (8000tok)  (8000tok)             │
│      ↓          ↓         ↓                 │
│ Result1    Result2    Result3               │
│      ↓          ↓         ↓                 │
│ Combined: Complete 31KB output              │
│                                             │
│ Finally: provider.close() → no leak         │
└─────────────────────────────────────────────┘
```

---

## Key Takeaways

1. **Always configure limits per-provider** - Different APIs have different constraints
2. **Chunk large inputs** - Prevents timeouts and ensures completeness
3. **Never rely on `__del__` alone** - Use explicit cleanup with `finally` or context managers
4. **Make cleanup idempotent** - Prevent errors from double-close
