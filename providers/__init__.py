from .base import BaseProvider
from .siliconflow import SiliconFlowProvider
from .alibaba import AlibabaProvider

def create_provider(provider_config: dict) -> BaseProvider:
    name = provider_config['name']
    
    if name == 'siliconflow':
        return SiliconFlowProvider(provider_config)
    elif name == 'alibaba':
        return AlibabaProvider(provider_config)
    else:
        raise ValueError(f"Unknown provider: {name}")

def get_enabled_providers(config: dict) -> list:
    providers = []
    for p in config['providers']:
        if p.get('enabled', True):
            try:
                providers.append(create_provider(p))
            except ValueError as e:
                print(f"Warning: {e}")
    return providers
