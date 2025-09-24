from typing import Dict, Type
from .providers import BaseLLMProvider, OpenAIProvider, GeminiProvider


class LLMProviderFactory:
    """
    Factory class for creating LLM providers.
    """
    
    _providers = {
        "openai": OpenAIProvider,
        "gemini": GeminiProvider,
    }
    
    @classmethod
    def create_provider(cls, provider_name: str, **kwargs) -> BaseLLMProvider:
        """
        Create an LLM provider instance.
        
        Args:
            provider_name: Name of the provider ("openai" or "gemini")
            **kwargs: Additional arguments to pass to the provider constructor
            
        Returns:
            LLM provider instance
            
        Raises:
            ValueError: If provider_name is not supported
        """
        if provider_name.lower() not in cls._providers:
            raise ValueError(f"Unsupported provider: {provider_name}. Supported providers: {list(cls._providers.keys())}")
        
        provider_class = cls._providers[provider_name.lower()]
        return provider_class(**kwargs)
    
    @classmethod
    def register_provider(cls, name: str, provider_class: type):
        """
        Register a new LLM provider.
        
        Args:
            name: Name of the provider
            provider_class: Provider class that inherits from BaseLLMProvider
        """
        if not issubclass(provider_class, BaseLLMProvider):
            raise ValueError("Provider class must inherit from BaseLLMProvider")
        cls._providers[name.lower()] = provider_class