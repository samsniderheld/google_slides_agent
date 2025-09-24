import os
import json
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Type, Union

from google import genai
from google.genai import types
from openai import OpenAI
from pydantic import BaseModel, Field, create_model

from .schema_generator import SchemaGenerator


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    This class defines the interface that all LLM providers must implement.
    """
    
    @abstractmethod
    def make_api_call(self, messages: List[Dict[str, Any]]) -> str:
        """
        Make a standard API call to the LLM.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Response text from the LLM
        """
        pass
    
    @abstractmethod
    def make_api_call_structured(
        self, 
        messages: List[Dict[str, Any]], 
        response_model: Optional[Union[Type[BaseModel], str]] = None
    ) -> Any:
        """
        Make a structured API call to the LLM.
        
        Args:
            messages: List of message dictionaries
            response_model: Pydantic model class or path to YAML schema file
            
        Returns:
            Parsed response object
        """
        pass


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI LLM provider implementation.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set.")
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
    
    def make_api_call(self, messages: List[Dict[str, Any]]) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )
        return response.choices[0].message.content
    
    def make_api_call_structured(
        self, 
        messages: List[Dict[str, Any]], 
        response_model: Optional[Union[Type[BaseModel], str]] = None
    ) -> Any:
        # Handle YAML schema file
        if isinstance(response_model, str):
            response_model = SchemaGenerator.from_yaml_file(response_model)
        
        if response_model is None:
            # Default fallback model
            response_model = create_model('DefaultResponse', content=(str, Field(description="Response content")))
        
        response = self.client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=messages,
            response_format=response_model
        )
        return response.choices[0].message.parsed


class GeminiProvider(BaseLLMProvider):
    """
    Google Gemini LLM provider implementation.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set.")
        self.client = genai.Client(api_key=self.api_key)
        self.model = model
    
    def make_api_call(self, messages: List[Dict[str, Any]]) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=messages[1]["content"],
            config=types.GenerateContentConfig(
                system_instruction=messages[0]["content"]
            )
        )
        return response.text
    
    def make_api_call_structured(
        self, 
        messages: List[Dict[str, Any]], 
        response_model: Optional[Union[Type[BaseModel], str]] = None
    ) -> Any:
        # Handle YAML schema file
        if isinstance(response_model, str):
            response_model = SchemaGenerator.from_yaml_file(response_model)
        
        if response_model is None:
            # Default fallback model
            response_model = create_model('DefaultResponse', content=(str, Field(description="Response content")))
        
        response = self.client.models.generate_content(
            model=self.model,
            contents=messages[1]["content"],
            config=types.GenerateContentConfig(
                system_instruction=messages[0]["content"],
                response_mime_type='application/json',
                response_schema=response_model
            )
        )
        
        # Parse JSON response into the model
        try:
            response_data = json.loads(response.text)
            return response_model(**response_data)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            # Fallback: try to create model with the raw text
            try:
                return response_model(content=response.text)
            except:
                raise ValueError(f"Could not parse structured response: {e}")