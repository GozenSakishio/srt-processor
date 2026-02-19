from abc import ABC, abstractmethod
from openai import OpenAI

class BaseProvider(ABC):
    def __init__(self, config: dict, api_key: str):
        self.config = config
        self.client = OpenAI(
            api_key=api_key,
            base_url=config['base_url']
        )
        self.name = config['name']
        self.model = config['model']
    
    @abstractmethod
    def process(self, prompt: str, temperature: float = 0.7, max_tokens: int = 4000) -> str:
        pass

class OpenAICompatibleProvider(BaseProvider):
    def process(self, prompt: str, temperature: float = 0.7, max_tokens: int = 4000) -> str:
        params = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        if self.config.get('extra_params'):
            params.update(self.config['extra_params'])
        response = self.client.chat.completions.create(**params)
        return response.choices[0].message.content
