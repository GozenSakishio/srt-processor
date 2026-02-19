#!/usr/bin/env python3
import os
import re
import time
from pathlib import Path
from datetime import datetime

import yaml
from dotenv import load_dotenv

from providers import get_enabled_providers

load_dotenv()

INPUT_DIR = Path("input")
OUTPUT_DIR = Path("output")
CONFIG_FILE = Path("config.yaml")


def load_config():
    with open(CONFIG_FILE, encoding='utf-8') as f:
        return yaml.safe_load(f)


def read_srt(file_path: Path) -> str:
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def extract_text_from_srt(srt_content: str) -> str:
    lines = srt_content.strip().split('\n')
    text_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.isdigit():
            continue
        if re.match(r'\d{2}:\d{2}:\d{2}', line):
            continue
        text_lines.append(line)
    
    return '\n'.join(text_lines)


def process_with_fallback(providers, prompt: str, config: dict) -> tuple[str, str]:
    rate_config = config['rate_limit']
    max_retries = rate_config.get('max_retries', 3)
    
    for provider in providers:
        for attempt in range(max_retries):
            try:
                print(f"    Trying {provider.name} ({provider.model}) attempt {attempt + 1}/{max_retries}")
                result = provider.process(prompt)
                return result, provider.name
            except Exception as e:
                print(f"    Error with {provider.name}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
    
    raise RuntimeError("All providers failed")


def main():
    config = load_config()
    providers = get_enabled_providers(config)
    
    if not providers:
        print("Error: No available providers. Check your API keys.")
        return
    
    print(f"Available providers: {[p.name for p in providers]}")
    
    srt_files = list(INPUT_DIR.glob("*.srt"))
    
    if not srt_files:
        print("No .srt files found in input/")
        return
    
    print(f"\nProcessing {len(srt_files)} SRT file(s)...\n")
    
    rate_config = config['rate_limit']
    delay = 60.0 / rate_config['requests_per_minute']
    prompt_template = config['processing']['prompt']
    include_title = config['processing'].get('include_filename_as_title', True)
    
    for i, srt_file in enumerate(srt_files, 1):
        print(f"[{i}/{len(srt_files)}] {srt_file.name}")
        
        try:
            srt_content = read_srt(srt_file)
            raw_text = extract_text_from_srt(srt_content)
            
            if not raw_text.strip():
                print(f"    Skipping: No text content found")
                continue
            
            prompt = prompt_template.format(content=raw_text)
            
            cleaned_text, used_provider = process_with_fallback(providers, prompt, config)
            
            output_lines = []
            if include_title:
                title = srt_file.stem
                output_lines.append(f"# {title}\n")
            output_lines.append(cleaned_text)
            
            output_file = OUTPUT_DIR / f"{srt_file.stem}.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(output_lines))
            
            print(f"    Done via {used_provider} -> {output_file.name}")
            
        except Exception as e:
            print(f"    Failed: {e}")
        
        if i < len(srt_files):
            time.sleep(delay)
    
    print("\nAll done!")


if __name__ == "__main__":
    main()
