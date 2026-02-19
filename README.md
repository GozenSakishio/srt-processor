# SRT Processor

Clean SRT subtitle files for RAG knowledge base using AI (SiliconFlow & Alibaba Cloud).

## Features

- Dual provider support with automatic fallback
- Extracts and cleans subtitle text
- Outputs formatted TXT for RAG systems
- Filename used as section title

## Quick Start

```bash
# 1. Clone
git clone https://github.com/GozenSakishio/srt-processor
cd srt-processor

# 2. Setup
cp .env.example .env
# Edit .env with your API keys

pip install -r requirements.txt

# 3. Process
cp your/files/*.srt input/
python run.py
```

## Configuration

Edit `config.yaml`:

```yaml
providers:
  - name: alibaba
    base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
    model: qwen3-8b
    enabled: true
    extra_params:
      enable_thinking: false
      
  - name: siliconflow
    base_url: https://api.siliconflow.cn/v1
    model: Qwen/Qwen3-8B
    enabled: true
```

Providers are tried in order. Use `extra_params` for provider-specific options (e.g., Alibaba requires `enable_thinking: false` for non-streaming calls).

## API Keys

| Provider | Key Name | Get Key |
|----------|----------|---------|
| SiliconFlow | `SILICONFLOW_API_KEY` | https://cloud.siliconflow.cn |
| Alibaba Cloud | `ALIBABA_API_KEY` | https://dashscope.console.aliyun.com |

## Output

- Input: `input/video.srt`
- Output: `output/video.txt`

Output format:
```
# video

[Cleaned subtitle text without timestamps...]
```
