import os
import yaml
from typing import Dict, Any, Optional, Type
from pydantic import BaseModel, Field, create_model


class SchemaGenerator:
    """
    Generates Pydantic models from YAML schema definitions.
    """
    
    @staticmethod
    def from_yaml_file(yaml_file: str) -> Type[BaseModel]:
        """
        Create a Pydantic model from a YAML schema file.
        
        Args:
            yaml_file: Path to the YAML schema file
            
        Returns:
            Pydantic model class
        """
        with open(yaml_file, 'r') as file:
            schema = yaml.safe_load(file)
        return SchemaGenerator.from_dict(schema)
    
    @staticmethod
    def from_dict(schema: Dict[str, Any]) -> Type[BaseModel]:
        """
        Create a Pydantic model from a schema dictionary.
        
        Args:
            schema: Schema dictionary with model name and fields
            
        Returns:
            Pydantic model class
        """
        model_name = schema.get('model_name', 'GeneratedModel')
        fields = schema.get('fields', {})
        
        # Convert YAML field definitions to Pydantic field definitions
        pydantic_fields = {}
        
        for field_name, field_def in fields.items():
            if isinstance(field_def, str):
                # Simple type definition
                field_type = SchemaGenerator._get_python_type(field_def)
                pydantic_fields[field_name] = (field_type, ...)
            elif isinstance(field_def, dict):
                # Complex field definition with type, description, default, etc.
                field_type = SchemaGenerator._get_python_type(field_def.get('type', 'str'), field_def.get('schema'))
                field_description = field_def.get('description', '')
                field_default = field_def.get('default', ...)
                
                if field_default == ...:
                    pydantic_fields[field_name] = (field_type, Field(description=field_description))
                else:
                    pydantic_fields[field_name] = (field_type, Field(default=field_default, description=field_description))
        
        # Create the model class
        model_class = create_model(model_name, **pydantic_fields)
        
        # Add custom methods if specified in schema
        if 'methods' in schema:
            SchemaGenerator._add_custom_methods(model_class, schema['methods'])
        
        return model_class
    
    @staticmethod
    def _get_python_type(type_str: str, nested_schema: Optional[Dict] = None) -> Type:
        """Convert YAML type string to Python type."""
        from typing import List, Dict, Any
        
        type_mapping = {
            'str': str,
            'string': str,
            'int': int,
            'integer': int,
            'float': float,
            'bool': bool,
            'boolean': bool,
            'list': list,
            'dict': dict,
            'any': Any,
        }
        
        # Handle list types like "list[dict]" with nested schema
        if type_str.startswith('list[') and type_str.endswith(']'):
            inner_type_str = type_str[5:-1]
            if inner_type_str == 'dict' and nested_schema:
                # Create nested model for the dict structure
                nested_model = SchemaGenerator._create_nested_model(nested_schema)
                return List[nested_model]
            else:
                inner_type = SchemaGenerator._get_python_type(inner_type_str)
                return List[inner_type]
        
        # Handle dict types with nested schema
        if type_str == 'dict' and nested_schema:
            return SchemaGenerator._create_nested_model(nested_schema)
        elif type_str.startswith('dict[') and type_str.endswith(']'):
            return Dict[str, Any]  # Simplified for now
        
        return type_mapping.get(type_str.lower(), str)
    
    @staticmethod
    def _create_nested_model(schema_dict: Dict[str, Any]) -> Type[BaseModel]:
        """Create a nested Pydantic model from a schema dictionary."""
        nested_fields = {}
        
        for field_name, field_def in schema_dict.items():
            if isinstance(field_def, str):
                field_type = SchemaGenerator._get_python_type(field_def)
                nested_fields[field_name] = (field_type, ...)
            elif isinstance(field_def, dict):
                field_type = SchemaGenerator._get_python_type(field_def.get('type', 'str'), field_def.get('schema'))
                field_description = field_def.get('description', '')
                field_default = field_def.get('default', ...)
                
                if field_default == ...:
                    nested_fields[field_name] = (field_type, Field(description=field_description))
                else:
                    nested_fields[field_name] = (field_type, Field(default=field_default, description=field_description))
        
        return create_model('NestedModel', **nested_fields)
    
    @staticmethod
    def _add_custom_methods(model_class: Type[BaseModel], methods: Dict[str, str]):
        """Add custom methods to the generated model class."""
        for method_name, method_body in methods.items():
            if method_name == 'to_json':
                def to_json(self):
                    return self.model_dump()
                setattr(model_class, 'to_json', to_json)
            elif method_name == 'to_str':
                def to_str(self):
                    return str(self.model_dump())
                setattr(model_class, 'to_str', to_str)