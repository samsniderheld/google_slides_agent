import os
from typing import List, Dict, Any, Optional

from .schema_generator import SchemaGenerator
from .factory import LLMProviderFactory


class LLMWrapper:
    """
    Wrapper class for different language models.
    
    This class provides a unified interface using the provider pattern.
    """
    
    def __init__(self, provider: str = "gemini", schema_path: Optional[str] = None, **provider_kwargs) -> None:
        """
        Initializes the LLMWrapper with the specified provider.
        
        Args:
            provider (str): The provider to use ("openai" or "gemini")
            schema_path (Optional[str]): Path to YAML schema file for structured responses
            **provider_kwargs: Additional arguments to pass to the provider
        """
        self.provider_name = provider
        self.provider = LLMProviderFactory.create_provider(provider, **provider_kwargs)
        
        # Pre-generate schema model if provided
        self.default_schema_model = None
        if schema_path and os.path.exists(schema_path):
            try:
                self.default_schema_model = SchemaGenerator.from_yaml_file(schema_path)
            except Exception as e:
                print(f"Warning: Could not load schema from {schema_path}: {e}")

    def make_api_call(self, messages: List[Dict[str, Any]]) -> str:
        """
        Makes an API call to the language model with the provided messages.
        
        Args:
            messages: The messages to send to the language model.
            
        Returns:
            The response from the language model.
        """
        return self.provider.make_api_call(messages)
    
    def make_api_call_structured(self, messages: List[Dict[str, Any]]) -> Any:
        """
        Makes a structured API call to the language model with the provided messages.
        Uses the default schema model set during initialization.
        
        Args:
            messages: The messages to send to the language model.
            
        Returns:
            The structured response from the language model.
        """
        return self.provider.make_api_call_structured(messages, self.default_schema_model)
