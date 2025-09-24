# Agent Boilerplate

A flexible boilerplate for creating and managing AI agents with multiple LLM providers and vector store capabilities. Features an abstract provider system with dynamic schema generation from YAML files for structured responses. Supports OpenAI, Google Gemini, and custom LLM providers, with vector store functionality available for OpenAI.

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/samsniderheld/agent_boiler_plate.git
    cd agent_boiler_plate
    ```

2. Create a virtual environment and activate it:
    ```sh
    python3 -m venv venv
    source venv/bin/activate
    ```

3. Install the required dependencies:
    ```sh
    pip install -r requirements.txt
    ```

4. Install extra dependencies:

    ```sh
    pip install torchao --extra-index-url https://download.pytorch.org/whl/cu121 # full options are cpu/cu118/cu121/cu124
    pip install git+https://github.com/xhinker/sd_embed.git@main
    ```

## API Configurations

The system supports multiple LLM providers. Configure the APIs you want to use:

### OpenAI
1. Obtain your OpenAI API key from the [OpenAI website](https://platform.openai.com/api-keys)
2. Set your API key as an environment variable:
    ```sh
    export OPENAI_API_KEY='your_openai_api_key'
    ```

### Google Gemini
1. Get your Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Set your API key as an environment variable:
    ```sh
    export GEMINI_API_KEY='your_gemini_api_key'
    ```

## Agent Configuration

Agents are configured using YAML files in the `config_files/` directory.

Example `example.yaml`:

```yaml
name: example
system_prompt: |
  You are a creative agent. Your job is to take an input prompt and come up with some creative concepts for it.
```

## Architecture

### LLM Provider System
The system uses an abstract provider pattern for maximum flexibility:

- **`BaseLLMProvider`**: Abstract base class defining the interface
- **`OpenAIProvider`**: OpenAI GPT models implementation
- **`GeminiProvider`**: Google Gemini models implementation  
- **`LLMProviderFactory`**: Factory for creating and registering providers
- **`LLMWrapper`**: Unified interface with schema pre-loading
- **`SchemaGenerator`**: Dynamic Pydantic model generation from YAML

### BaseAgent
The `BaseAgent` class loads configuration files and provides both standard and structured API interfaces, with optional vector store capabilities:

```python
# Create agent with specific LLM provider and schema
agent = BaseAgent(
    config_file="config_files/example.yaml", 
    llm="openai",
    schema_path="config_files/creative_response_schema.yaml"
)

# Standard API calls
response = agent.basic_api_call("Your prompt here")

# Structured API calls (uses pre-loaded schema)
structured = agent.basic_api_call_structured("Create creative concepts")
print(structured.title, structured.concept)

# Enable vector store functionality (OpenAI only)
agent_with_vector = BaseAgent(
    config_file="config_files/example.yaml",
    llm="openai",
    enable_vector_store=True
)
```

## Quick Start

### Interactive Example
Run the interactive example agent with both standard and structured response capabilities:

```sh
python3 example_agent.py
```

This creates an agent from `config_files/example.yaml` with pre-loaded schema and starts an interactive chat loop.

**Available commands:**
- Regular chat: `Create concepts for a coffee shop`
- Structured responses: `structured Create concepts for a sustainable coffee shop`
- View schema: `schema`
- Help: `help`

### Programmatic Usage

```python
from agents.base_agent import BaseAgent

# Create agent with Gemini and pre-loaded schema
agent = BaseAgent(
    config_file="config_files/example.yaml",
    llm="gemini",
    schema_path="config_files/creative_response_schema.yaml"
)

# Standard chat
response = agent.basic_api_call("Come up with creative concepts for a coffee shop")
print(response)

# Structured response (uses pre-loaded schema)
structured = agent.basic_api_call_structured("Create sustainable coffee shop concepts")
print(f"Title: {structured.title}")
print(f"Concept: {structured.concept}")
print(f"Target Audience: {structured.target_audience}")
print(f"Feasibility: {structured.feasibility_score}/10")
```

## Vector Store Integration (OpenAI Only)

The system includes comprehensive vector store functionality for knowledge retrieval and context-enhanced responses. This feature is currently available only with OpenAI.

### Setup Vector Store

```python
from agents.base_agent import BaseAgent

# Create agent with vector store enabled
agent = BaseAgent(
    config_file="config_files/example.yaml",
    llm="openai",  # Vector stores require OpenAI
    enable_vector_store=True
)

# Create a new vector store with documents
vector_store_id = agent.create_vector_store(
    name="My Knowledge Base",
    file_paths=["document1.pdf", "document2.txt", "document3.md"]
)

# Or use an existing vector store
agent.set_vector_store("vs_existing_id")
# Or set by name
agent.set_vector_store_by_name("My Knowledge Base")
```

### Vector Store Operations

```python
# Search for relevant content
results = agent.search_vector_store(
    query="What are the benefits of renewable energy?",
    limit=5
)

# Add more files to existing vector store
agent.add_files_to_vector_store(["new_document.pdf"])

# Query LLM with vector store context
response = agent.query_with_context(
    query="Explain renewable energy benefits",
    context_query="renewable energy advantages",  # Optional: different search query
    max_context_results=3
)

# List all available vector stores
stores = agent.list_vector_stores()
for store in stores:
    print(f"Name: {store['name']}, ID: {store['id']}, Files: {store['file_counts']}")

# Get vector store status
status = agent.get_vector_store_status()
print(f"Status: {status['status']}, Files: {status['file_counts']}")

# Find vector store ID by name
store_id = agent.get_store_id_by_name("My Knowledge Base")
```

### Vector Store Features

- **Document Upload**: Support for PDF, TXT, MD, and other text formats
- **Intelligent Search**: Vector-based similarity search for relevant content retrieval
- **Context Integration**: Automatically enhance LLM queries with relevant knowledge base content
- **Store Management**: Create, list, and manage multiple vector stores
- **Name-based Access**: Find and set vector stores by human-readable names
- **File Management**: Add files to existing vector stores incrementally

## Dynamic Schema Generation

Define response structures using YAML schemas that are automatically converted to Pydantic models:

### Schema Definition

`config_files/creative_response_schema.yaml`:
```yaml
model_name: CreativeResponse
description: Schema for creative concept responses
fields:
  title:
    type: str
    description: The title of the creative concept
  concept:
    type: str
    description: Detailed description of the creative concept
  key_features:
    type: list[str]
    description: List of key features or highlights
  target_audience:
    type: str
    description: Who this concept would appeal to
  feasibility_score:
    type: int
    description: Feasibility score from 1-10
    default: 5
methods:
  to_json: true
  to_str: true
```

### Supported Field Types
- `str`, `int`, `float`, `bool`
- `list[str]`, `list[int]`, etc.
- `dict[str, any]`
- Complex nested structures

### Schema Features
- **Field descriptions**: Help LLMs understand expected content
- **Default values**: Optional fields with fallback values
- **Custom methods**: Add `to_json()` and `to_str()` methods
- **Type validation**: Automatic Pydantic validation

## Extending with Custom Providers

Add support for new LLM providers:

```python
from agents.llm_wrapper import BaseLLMProvider, LLMProviderFactory

class AnthropicProvider(BaseLLMProvider):
    def __init__(self, api_key: str = None, model: str = "claude-3-sonnet"):
        # Initialize Anthropic client
        pass
    
    def make_api_call(self, messages):
        # Implement API call logic
        pass
    
    def make_api_call_structured(self, messages, response_model):
        # Implement structured response logic  
        pass

# Register the new provider
LLMProviderFactory.register_provider("anthropic", AnthropicProvider)

# Use it with schema
agent = BaseAgent(
    config_file="config.yaml", 
    llm="anthropic",
    schema_path="config_files/my_schema.yaml"
)
```

## Project Structure

```
├── agents/
│   ├── __init__.py
│   ├── base_agent.py              # Base agent class with vector store support
│   ├── llm_wrapper.py             # LLM provider system & schema generator
│   ├── vector_store_wrapper.py    # OpenAI vector store integration
│   ├── providers.py               # LLM provider implementations
│   ├── factory.py                 # LLM provider factory
│   └── schema_generator.py        # Dynamic schema generation
├── config_files/
│   ├── example.yaml               # Example agent configuration
│   └── creative_response_schema.yaml # Example YAML schema
├── example_agent.py               # Interactive example script
├── requirements.txt               # Python dependencies
├── .gitignore                     # Git ignore file
└── README.md
```

## Features

- **Multi-Provider Support**: Easy switching between OpenAI, Gemini, and custom providers
- **Vector Store Integration**: Knowledge retrieval and context-enhanced responses (OpenAI only)
- **Dynamic Schema Generation**: Create Pydantic models from YAML schema definitions
- **Structured Responses**: Get consistent, typed responses from LLMs
- **Schema Pre-loading**: Efficient architecture that loads schemas once during initialization
- **Abstract Provider System**: Clean architecture for adding new LLM providers
- **YAML Configuration**: Simple agent and schema configuration using YAML files
- **Interactive Interface**: Ready-to-use chat interface with structured response demo
- **Type Safety**: Full type hints for better development experience
- **Error Handling**: Comprehensive error handling with graceful fallbacks
- **Extensible**: Factory pattern allows easy registration of custom providers
- **Document Search**: Upload documents and search for relevant content using vector similarity
- **Context-Aware Queries**: Automatically enhance LLM responses with relevant knowledge base content

## Performance Benefits

- **Efficient Schema Loading**: YAML schemas are parsed and converted to Pydantic models once during agent initialization, not on every API call
- **Memory Optimization**: Pre-loaded schema models eliminate repetitive parsing overhead
- **Fast Structured Responses**: Direct use of compiled Pydantic models for validation and serialization

## License

MIT License - see LICENSE file for details.
