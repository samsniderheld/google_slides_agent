from typing import Dict, Type, Any
from .vector_store_providers import BaseVectorStoreProvider, OpenAIVectorStoreProvider, ChromaDBVectorStoreProvider


class VectorStoreProviderFactory:
    """
    Factory class for creating vector store providers.
    
    This class manages the registration and creation of different vector store providers.
    """
    
    _providers: Dict[str, Type[BaseVectorStoreProvider]] = {
        "openai": OpenAIVectorStoreProvider,
        "chromadb": ChromaDBVectorStoreProvider,
        "chroma": ChromaDBVectorStoreProvider,  # Alias
    }
    
    @classmethod
    def create_provider(cls, provider: str, **kwargs) -> BaseVectorStoreProvider:
        """
        Create a vector store provider instance.
        
        Args:
            provider (str): The provider type ("openai", "chromadb", "chroma")
            **kwargs: Additional arguments to pass to the provider constructor
            
        Returns:
            BaseVectorStoreProvider: The created provider instance
            
        Raises:
            ValueError: If the provider is not supported
        """
        provider = provider.lower()
        
        if provider not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise ValueError(f"Unsupported vector store provider: {provider}. Available: {available}")
        
        provider_class = cls._providers[provider]
        return provider_class(**kwargs)
    
    @classmethod
    def register_provider(cls, name: str, provider_class: Type[BaseVectorStoreProvider]) -> None:
        """
        Register a new vector store provider.
        
        Args:
            name (str): The name of the provider
            provider_class (Type[BaseVectorStoreProvider]): The provider class
        """
        cls._providers[name.lower()] = provider_class
    
    @classmethod
    def get_available_providers(cls) -> list:
        """
        Get a list of available vector store providers.
        
        Returns:
            list: List of provider names
        """
        return list(cls._providers.keys())
    
    @classmethod
    def is_provider_supported(cls, provider: str) -> bool:
        """
        Check if a provider is supported.
        
        Args:
            provider (str): The provider name
            
        Returns:
            bool: True if supported, False otherwise
        """
        return provider.lower() in cls._providers