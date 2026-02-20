# Code Flow: Token Estimation, Chunking, and Joining

This note explains how the SRT processor estimates token count, splits large text into chunks, and rejoins processed results.

---

## Overall Flow

```
SRT File
    ↓
read_srt()                     # Read raw SRT content
    ↓
extract_text_from_srt()        # Strip timestamps/sequence numbers
    ↓
len(raw_text) > MAX_CHUNK_SIZE?
    ↓                          ↓ (No)
    ↓                      Single prompt → process_with_fallback()
    ↓                                       ↓
split_text_into_chunks()                    ↓
    ↓                                       ↓
For each chunk → process_with_fallback()    ↓
    ↓                                       ↓
Collect results[]                           ↓
    ↓                                       ↓
'\n\n'.join(results)                        ↓
    ↓←──────────────────────────────────────┘
    ↓
Write output .txt
```

---

## 1. Token Estimation

**There is NO actual token estimation function.** The repo uses **character count** as a simple proxy.

### Location

- `run.py:18` - Constant definition
- `run.py:95` - Size check

### Code

```python
MAX_CHUNK_SIZE = 12000  # Characters, NOT tokens

def process_large_text(providers, raw_text: str, config: dict) -> tuple[str, str]:
    if len(raw_text) <= MAX_CHUNK_SIZE:  # Character-based comparison
        # Process as single chunk
        ...
```

### Why This Works (Approximately)

| Language | Approximation | Reason |
|----------|---------------|--------|
| Chinese | 1 char ≈ 1-2 tokens | Hanzi are dense |
| English | 4 chars ≈ 1 token | Spaces, common words compress well |
| Mixed | Varies | Conservative to use char count |

### Limitation

For accurate token counting, you would need a tokenizer library like `tiktoken`:

```python
# Not implemented, but would look like:
import tiktoken
encoder = tiktoken.encoding_for_model("gpt-4")
token_count = len(encoder.encode(text))
```

---

## 2. Chunk Splitting Function

### Function: `split_text_into_chunks()`

**Location:** `run.py:48-69`

### Code

```python
def split_text_into_chunks(text: str, max_size: int = MAX_CHUNK_SIZE) -> list[str]:
    # Step 1: Split at sentence boundaries
    sentences = re.split(r'(?<=[。.!?])\s*', text)
    
    chunks = []
    current_chunk = []
    current_size = 0
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        sent_size = len(sentence)
        
        # Step 2: If adding this sentence exceeds limit, save current chunk
        if current_size + sent_size + 1 > max_size and current_chunk:
            chunks.append(' '.join(current_chunk))  # Join with space
            current_chunk = []
            current_size = 0
        
        # Step 3: Add sentence to current chunk
        current_chunk.append(sentence)
        current_size += sent_size + 1
    
    # Step 4: Don't forget the last chunk
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks
```

### Breakdown

| Step | Description |
|------|-------------|
| Split | `re.split(r'(?<=[。.!?])\s*', text)` - Splits after `。`, `.`, `!`, `?` |
| Accumulate | Build up sentences until `current_size + sentence > max_size` |
| Join chunk | `' '.join(current_chunk)` - Sentences joined with single space |
| Return | List of chunk strings |

### Example

```
Input: 31KB text
MAX_CHUNK_SIZE: 12000 chars

Output:
  Chunk 1: 11,917 chars (ends at sentence boundary)
  Chunk 2: 11,979 chars (ends at sentence boundary)
  Chunk 3:  7,548 chars (remaining text)
```

---

## 3. Joining Chunks Together

### Function: `process_large_text()`

**Location:** `run.py:94-118`

### Code

```python
def process_large_text(providers, raw_text: str, config: dict) -> tuple[str, str]:
    # If small enough, process as single chunk
    if len(raw_text) <= MAX_CHUNK_SIZE:
        prompt_template = config['processing']['prompt']
        prompt = prompt_template.format(content=raw_text)
        return process_with_fallback(providers, prompt, config)
    
    # Split into chunks
    chunks = split_text_into_chunks(raw_text)
    print(f"    Split into {len(chunks)} chunks ({[len(c) for c in chunks]} chars each)")
    
    # Process each chunk
    prompt_template = config['processing']['prompt']
    results = []
    last_provider = None
    
    for i, chunk in enumerate(chunks):
        print(f"    Processing chunk {i+1}/{len(chunks)}...")
        prompt = prompt_template.format(content=chunk)
        result, provider = process_with_fallback(providers, prompt, config)
        results.append(result)
        last_provider = provider
        
        # Rate limiting between chunks
        if i < len(chunks) - 1:
            delay = 60.0 / config['rate_limit']['requests_per_minute']
            time.sleep(delay)
    
    # JOIN: Double newline between chunks
    combined = '\n\n'.join(results)
    return combined, last_provider
```

### Joining Method

```python
combined = '\n\n'.join(results)  # Double newline
```

This creates clear separation between processed chunks in the final output.

---

## Summary Table

| Step | Function/Code | Location |
|------|---------------|----------|
| Token estimation | `len(text)` (character count) | `run.py:95` |
| Chunk splitting | `split_text_into_chunks()` | `run.py:48-69` |
| Internal chunk join | `' '.join(current_chunk)` (space) | `run.py:60,67` |
| Final results join | `'\n\n'.join(results)` (double newline) | `run.py:117` |

---

## Visual: Chunk Processing Flow

```
31KB raw text
     │
     ▼
┌─────────────────────────────────────┐
│   split_text_into_chunks()          │
│   Sentence-aware splitting          │
└─────────────────────────────────────┘
     │
     ▼
┌─────────┐  ┌─────────┐  ┌─────────┐
│ Chunk 1 │  │ Chunk 2 │  │ Chunk 3 │
│ 12KB    │  │ 12KB    │  │  7KB    │
└────┬────┘  └────┬────┘  └────┬────┘
     │            │            │
     ▼            ▼            ▼
┌─────────┐  ┌─────────┐  ┌─────────┐
│ API #1  │  │ API #2  │  │ API #3  │
│ prompt  │  │ prompt  │  │ prompt  │
│   ↓     │  │   ↓     │  │   ↓     │
│ AI      │  │ AI      │  │ AI      │
│   ↓     │  │   ↓     │  │   ↓     │
│ Result1 │  │ Result2 │  │ Result3 │
└────┬────┘  └────┬────┘  └────┬────┘
     │            │            │
     └────────────┼────────────┘
                  ▼
        '\n\n'.join([R1, R2, R3])
                  │
                  ▼
         Combined output
```

---

## Key Takeaways

1. **No real tokenizer** - Uses character count as approximation (12000 chars ≈ safe limit)
2. **Sentence-boundary splitting** - Chunks don't break mid-sentence
3. **Space-joined internally** - Sentences within a chunk joined with `' '`
4. **Double-newline for results** - Final output uses `'\n\n'` between processed chunks
5. **Rate limiting between chunks** - Respects `requests_per_minute` config
