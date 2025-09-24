#!/usr/bin/env python3
"""
Example agent script demonstrating both standard and structured API calls.
Showcases the dynamic schema generation from YAML files.
"""

import os
import sys
import json
from typing import Optional

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.base_agent import BaseAgent


def print_welcome():
    """Print welcome message and instructions."""
    print("=" * 60)
    print("🤖 Example Agent Interactive Chat")
    print("=" * 60)
    print("This agent demonstrates both standard and structured API calls.")
    print("\nCommands:")
    print("  - Type your message to chat with the agent")
    print("  - Type 'structured <your prompt>' for structured response")
    print("  - Type 'schema' to see the structured response schema")
    print("  - Type 'quit', 'exit', or 'q' to exit")
    print("  - Type 'help' to see this message again")
    print("  - Type 'config' to see agent configuration")
    print("=" * 60)


def print_help():
    """Print help information."""
    print("\n📋 Available Commands:")
    print("  help              - Show this help message")
    print("  config            - Show agent configuration")
    print("  schema            - Show structured response schema")
    print("  structured <msg>  - Get structured response using YAML schema")
    print("  quit/exit/q       - Exit the chat")
    print("\n💡 Example structured command:")
    print("  structured Create concepts for a sustainable coffee shop")
    print()


def print_config(agent: BaseAgent):
    """Print agent configuration."""
    print(f"\n🔧 Agent Configuration:")
    print(f"  Name: {agent.name}")
    print(f"  LLM Provider: {agent.llm.provider_name}")
    print(f"  System Prompt: {agent.config['system_prompt'][:100]}...")
    print()


def print_schema():
    """Print the structured response schema."""
    schema_path = os.path.join("config_files", "creative_response_schema.yaml")
    if os.path.exists(schema_path):
        try:
            import yaml
            with open(schema_path, 'r') as f:
                schema = yaml.safe_load(f)
            
            print("\n📝 Structured Response Schema:")
            print(f"  Model: {schema.get('model_name', 'Unknown')}")
            print(f"  Description: {schema.get('description', 'No description')}")
            print("  Fields:")
            for field_name, field_def in schema.get('fields', {}).items():
                if isinstance(field_def, dict):
                    field_type = field_def.get('type', 'unknown')
                    field_desc = field_def.get('description', 'No description')
                    default_val = field_def.get('default', 'Required')
                    print(f"    - {field_name} ({field_type}): {field_desc}")
                    if default_val != 'Required':
                        print(f"      Default: {default_val}")
                else:
                    print(f"    - {field_name} ({field_def})")
            print()
        except Exception as e:
            print(f"\n❌ Error reading schema: {e}")
    else:
        print("\n⚠️ Schema file not found at config_files/creative_response_schema.yaml")


def create_agent(config_path: Optional[str] = None, llm_provider: str = "gemini") -> BaseAgent:
    """
    Create an agent from the configuration file with pre-loaded schema.
    
    Args:
        config_path: Path to the configuration file
        llm_provider: LLM provider to use ("openai" or "gemini")
        
    Returns:
        BaseAgent instance with pre-loaded schema for structured responses
    """
    if config_path is None:
        config_path = os.path.join("config_files", "example.yaml")
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    # Set up schema path for structured responses
    schema_path = os.path.join("config_files", "creative_response_schema.yaml")
    
    # Create agent with pre-loaded schema
    agent = BaseAgent(
        config_file=config_path, 
        llm=llm_provider, 
        schema_path=schema_path if os.path.exists(schema_path) else None
    )
    return agent


def main():
    """Main function to run the interactive chat loop."""
    try:
        # Create the agent
        print("Loading agent from config_files/example.yaml...")
        agent = create_agent()
        print(f"✅ Agent '{agent.name}' loaded successfully!")
        
        # Print welcome message
        print_welcome()
        
        # Start chat loop
        while True:
            try:
                # Get user input
                user_input = input("\n💬 You: ").strip()
                
                # Handle empty input
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Goodbye! Thanks for chatting!")
                    break
                
                elif user_input.lower() == 'help':
                    print_help()
                    continue
                
                elif user_input.lower() == 'config':
                    print_config(agent)
                    continue
                
                elif user_input.lower() == 'schema':
                    print_schema()
                    continue
                
                elif user_input.lower().startswith('structured '):
                    # Handle structured API call
                    prompt = user_input[11:].strip()  # Remove 'structured ' prefix
                    if not prompt:
                        print("\n⚠️ Please provide a prompt after 'structured'")
                        continue
                    
                    print(f"\n🤔 {agent.name} is generating structured response...")
                    
                    try:
                        # Schema is already loaded during agent initialization
                        structured_response = agent.basic_api_call_structured(prompt)
                        
                        if structured_response is None:
                            print("\n⚠️ No schema model available. Using standard response...")
                            response = agent.basic_api_call(prompt)
                            print(f"\n🤖 {agent.name}: {response}")
                        else:
                            print(f"\n🤖 {agent.name} (Structured):")
                            print(f"  📌 Title: {structured_response.title}")
                            print(f"  💡 Concept: {structured_response.concept}")
                            print(f"  🎯 Target Audience: {structured_response.target_audience}")
                            print(f"  📊 Feasibility Score: {structured_response.feasibility_score}/10")
                            
                            if hasattr(structured_response, 'key_features') and structured_response.key_features:
                                print(f"  ✨ Key Features:")
                                for i, feature in enumerate(structured_response.key_features, 1):
                                    print(f"     {i}. {feature}")
                            
                            print(f"\n📋 Raw JSON:")
                            if hasattr(structured_response, 'to_json'):
                                print(json.dumps(structured_response.to_json(), indent=2))
                            else:
                                print(json.dumps(structured_response.model_dump(), indent=2))
                        
                    except Exception as struct_error:
                        print(f"\n❌ Structured call failed: {struct_error}")
                        print("Falling back to standard response...")
                        try:
                            response = agent.basic_api_call(prompt)
                            print(f"\n🤖 {agent.name}: {response}")
                        except Exception as fallback_error:
                            print(f"\n❌ Standard call also failed: {fallback_error}")
                    
                    continue
                
                # Make standard API call to agent
                print(f"\n🤔 {agent.name} is thinking...")
                
                try:
                    response = agent.basic_api_call(user_input)
                    print(f"\n🤖 {agent.name}: {response}")
                    
                except Exception as api_error:
                    print(f"\n❌ Error calling LLM: {api_error}")
                    print("Please check your API keys are set correctly.")
                    print("Required environment variables:")
                    print("  - OPENAI_API_KEY (for OpenAI)")
                    print("  - GEMINI_API_KEY (for Gemini)")
                
            except KeyboardInterrupt:
                print("\n\n👋 Chat interrupted. Goodbye!")
                break
                
            except EOFError:
                print("\n\n👋 End of input. Goodbye!")
                break
    
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("Make sure the config_files/example.yaml file exists.")
        sys.exit(1)
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()