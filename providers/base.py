from abc import ABC, abstractmethod
import httpx
from openai import OpenAI

class BaseProvider(ABC):
    def __init__(self, config: dict, api_key: str, timeout: float = 60.0):
        self.config = config
        http_client = httpx.Client(
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            timeout=httpx.Timeout(timeout, connect=30.0)
        )
        self.client = OpenAI(
            api_key=api_key,
            base_url=config['base_url'],
            timeout=timeout,
            http_client=http_client
        )
        self.name = config['name']
        self.model = config['model']
    
    @abstractmethod
    def process(self, prompt: str, temperature: float = 0.7, max_tokens: int = 4000) -> str:
        pass

class OpenAICompatibleProvider(BaseProvider):
    def process(self, prompt: str, temperature: float = 0.7, max_tokens: int = 4000) -> str:
        extra_body = self.config.get('extra_params')
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            extra_body=extra_body
        )
        return response.choices[0].message.content
