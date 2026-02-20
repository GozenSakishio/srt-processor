# Prompt Language and Provider Selection

This note covers two improvements: using appropriate prompt language and adding CLI for provider selection.

---

## Part 1: Prompt Language Matters

### The Problem

Using Chinese prompt for English content:

```yaml
processing:
  prompt: |
    你是一个专业的文本清洗助手。请清洗以下字幕文本，要求：
    1. 移除所有时间戳和序号
    2. 合并断句不完整的句子
    ...
```

**Input:** English subtitles (Blender/Eevee tutorials)

**Output Issues:**
- Meta-commentary in mixed language: "Here is the cleaned and formatted version..."
- Inconsistent style
- Model has to "translate internally" to understand instructions

### Comparison Table

| Aspect | Chinese Prompt | English Prompt |
|--------|---------------|----------------|
| Input language | English | English |
| Model reasoning | Translates internally | Direct understanding |
| Output style | Sometimes adds Chinese-style meta text | Cleaner, direct output |
| Instruction following | Good | Better for English content |

### Recommended English Prompt

```yaml
processing:
  prompt: |
    You are a professional text cleaning assistant. Clean the following subtitle text with these requirements:
    
    1. Remove all timestamps and sequence numbers
    2. Merge incomplete sentences into complete ones
    3. Fix obvious punctuation errors
    4. Keep the original meaning unchanged
    5. Output coherent paragraph text
    6. Output ALL content completely - do not omit or truncate any part
    
    Subtitle content:
    {content}
```

### Why This Helps

1. **No meta-commentary** - English prompt → direct English output without "以下是清洗后的文本..." intros
2. **Better instruction following** - Qwen models process English instructions more naturally for English content
3. **Consistent style** - Output matches input language without mixed language artifacts

---

## Part 2: Provider Selection Via CLI

### The Problem

Testing individual providers required editing `config.yaml`:

```yaml
providers:
  - name: alibaba
    enabled: true      # ← Have to toggle this manually
  - name: siliconflow  
    enabled: true      # ← And this
  - name: openrouter
    enabled: true      # ← And this
```

This becomes tedious when testing/debugging.

### Solution: Add CLI Argument

```python
#!/usr/bin/env python3
import argparse

def main():
    parser = argparse.ArgumentParser(description='Process SRT files with AI')
    parser.add_argument('--provider', '-p', 
                        help='Use only this provider (e.g., alibaba, openrouter, siliconflow)')
    parser.add_argument('--list-providers', '-l', 
                        action='store_true',
                        help='List available providers and exit')
    args = parser.parse_args()
    
    config = load_config()
    
    # List providers option
    if args.list_providers:
        print("Available providers in config:")
        for p in config['providers']:
            status = "enabled" if p.get('enabled', True) else "disabled"
            print(f"  - {p['name']} ({p['model']}) [{status}]")
        return
    
    providers = get_enabled_providers(config)
    
    # Filter to single provider if specified
    if args.provider:
        providers = [p for p in providers if p.name == args.provider]
        if not providers:
            print(f"Error: Provider '{args.provider}' not found or not enabled")
            print(f"Available: {[p.name for p in get_enabled_providers(config)]}")
            return
        print(f"Using only: {args.provider}")
    
    # ... rest of main() ...
```

### Usage Examples

```bash
# Use all enabled providers (fallback order)
python run.py

# Test only alibaba
python run.py --provider alibaba
python run.py -p alibaba

# Test only openrouter  
python run.py -p openrouter

# List available providers
python run.py --list-providers
python run.py -l
```

### Alternative: Environment Variable

Simpler approach using environment variable:

```python
# In run.py main()
import os

provider_filter = os.getenv('PROVIDER')
if provider_filter:
    providers = [p for p in providers if p.name == provider_filter]
```

```bash
PROVIDER=openrouter python run.py
```

---

## How Provider Fallback Works

The provider order in `config.yaml` determines fallback priority:

```yaml
providers:
  - name: alibaba      # 1st - tried first
    enabled: true
  - name: siliconflow  # 2nd - fallback if alibaba fails
    enabled: true
  - name: openrouter   # 3rd - fallback if both above fail
    enabled: true
```

Processing flow:
```
Request → alibaba
            ↓ (fail)
         siliconflow
            ↓ (fail)
         openrouter
            ↓ (fail)
         Error: All providers failed
```

---

## Key Takeaways

1. **Match prompt language to content** - English content → English prompt for cleaner output
2. **CLI arguments for testing** - No need to edit config for quick provider tests
3. **Provider order matters** - First provider in list is primary, rest are fallbacks
4. **Environment variables are simpler** - `PROVIDER=x python run.py` for quick tests
