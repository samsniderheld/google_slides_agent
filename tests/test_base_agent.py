import unittest
from unittest.mock import Mock, patch, mock_open
import sys
import os
import yaml

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent


class TestBaseAgent(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.mock_llm_patcher = patch('agents.base_agent.LLMWrapper')
        self.mock_llm = self.mock_llm_patcher.start()
        self.mock_llm_instance = Mock()
        self.mock_llm.return_value = self.mock_llm_instance
        
        self.mock_vector_patcher = patch('agents.base_agent.VectorStoreWrapper')
        self.mock_vector = self.mock_vector_patcher.start()
        
    def tearDown(self):
        """Clean up after each test."""
        self.mock_llm_patcher.stop()
        self.mock_vector_patcher.stop()
    
    def test_initialization_with_defaults(self):
        """Test BaseAgent initialization with default parameters."""
        agent = BaseAgent()
        
        # Check default values
        self.assertEqual(agent.max_messages, 3)
        self.assertIsNotNone(agent.config)
        self.assertEqual(agent.name, "default_agent")
        self.assertIsNotNone(agent.messages)
        self.assertEqual(len(agent.messages), 1)  # System prompt
        self.assertEqual(agent.messages[0]["role"], "system")
        
        # Verify LLMWrapper was called with correct defaults
        self.mock_llm.assert_called_once_with("openai", schema_path=None, model=None)
    
    def test_initialization_with_custom_parameters(self):
        """Test BaseAgent initialization with custom parameters."""
        agent = BaseAgent(
            llm="gemini",
            model="gemini-2.0-flash",
            max_messages=5,
            enable_vector_store=False
        )
        
        self.assertEqual(agent.max_messages, 5)
        
        # Verify LLMWrapper was called with custom parameters
        self.mock_llm.assert_called_once_with("gemini", schema_path=None, model="gemini-2.0-flash")
    
    def test_initialization_with_vector_store(self):
        """Test BaseAgent initialization with vector store enabled."""
        agent = BaseAgent(enable_vector_store=True, vector_store_provider="openai")
        
        # Verify vector store was initialized
        self.mock_vector.assert_called_once_with("openai")
        self.assertIsNotNone(agent.vector_store)
    
    def test_initialization_without_vector_store(self):
        """Test BaseAgent initialization with vector store disabled."""
        agent = BaseAgent(enable_vector_store=False)
        
        # Verify vector store was not initialized
        self.mock_vector.assert_not_called()
        self.assertIsNone(agent.vector_store)
    
    def test_default_config(self):
        """Test default configuration structure."""
        agent = BaseAgent()
        config = agent.default_config()
        
        required_keys = ["name", "system_prompt", "llm"]
        for key in required_keys:
            self.assertIn(key, config)
        
        self.assertEqual(config["name"], "default_agent")
        self.assertEqual(config["llm"], "openAI")
        self.assertIsInstance(config["system_prompt"], str)
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    def test_load_config_file_success(self, mock_yaml_load, mock_file):
        """Test successful configuration file loading."""
        test_config = {
            "name": "test_agent",
            "system_prompt": "Test prompt",
            "llm": "gemini"
        }
        mock_yaml_load.return_value = test_config
        
        agent = BaseAgent(config_file="test_config.yaml")
        
        # Verify file was opened and YAML was parsed
        mock_file.assert_called_once_with("test_config.yaml", 'r')
        mock_yaml_load.assert_called_once()
        
        # Verify config was loaded correctly
        self.assertEqual(agent.config, test_config)
        self.assertEqual(agent.name, "test_agent")
    
    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_load_config_file_not_found(self, mock_file):
        """Test error handling when config file is not found."""
        with self.assertRaises(FileNotFoundError):
            BaseAgent(config_file="nonexistent.yaml")
    
    @patch('builtins.open', new_callable=mock_open, read_data="invalid: yaml: content:")
    @patch('yaml.safe_load', side_effect=yaml.YAMLError("Invalid YAML"))
    def test_load_config_file_invalid_yaml(self, mock_yaml_load, mock_file):
        """Test error handling when config file contains invalid YAML."""
        with self.assertRaises(yaml.YAMLError):
            BaseAgent(config_file="invalid.yaml")
    
    def test_llm_wrapper_initialization_parameters(self):
        """Test that LLMWrapper receives correct initialization parameters."""
        # Test with schema path
        agent = BaseAgent(
            llm="openai",
            model="gpt-4",
            schema_path="/path/to/schema.yaml"
        )
        
        self.mock_llm.assert_called_once_with(
            "openai", 
            schema_path="/path/to/schema.yaml", 
            model="gpt-4"
        )
    
    def test_llm_wrapper_model_parameter_none(self):
        """Test LLMWrapper initialization when model parameter is None."""
        agent = BaseAgent(llm="gemini", model=None)
        
        self.mock_llm.assert_called_once_with("gemini", schema_path=None, model=None)
    
    def test_system_prompt_initialization(self):
        """Test that system prompt is properly added to messages."""
        test_config = {
            "name": "test_agent",
            "system_prompt": "Custom system prompt",
            "llm": "openai"
        }
        
        with patch.object(BaseAgent, 'load_config_file', return_value=test_config):
            agent = BaseAgent(config_file="test.yaml")
        
        # Verify system prompt is in messages
        self.assertEqual(len(agent.messages), 1)
        self.assertEqual(agent.messages[0]["role"], "system")
        self.assertEqual(agent.messages[0]["content"], "Custom system prompt")
    
    @patch('agents.base_agent.LLMWrapper', side_effect=Exception("LLM initialization failed"))
    def test_llm_initialization_error(self, mock_llm):
        """Test error handling when LLM initialization fails."""
        with self.assertRaises(Exception) as context:
            BaseAgent(llm="invalid_provider")
        
        self.assertIn("LLM initialization failed", str(context.exception))
    
    def test_vector_store_kwargs_passing(self):
        """Test that vector store kwargs are passed correctly."""
        kwargs = {"embedding_model": "text-embedding-ada-002", "dimension": 1536}
        
        agent = BaseAgent(
            enable_vector_store=True,
            vector_store_provider="openai",
            **kwargs
        )
        
        # Verify vector store was called with the kwargs
        self.mock_vector.assert_called_once_with("openai", **kwargs)
    
    # Input Validation Tests
    def test_basic_api_call_empty_query(self):
        """Test that empty query raises ValueError."""
        agent = BaseAgent()
        
        with self.assertRaises(ValueError) as context:
            agent.basic_api_call("")
        
        self.assertIn("Query cannot be empty or None", str(context.exception))
    
    def test_basic_api_call_none_query(self):
        """Test that None query raises ValueError."""
        agent = BaseAgent()
        
        with self.assertRaises(ValueError) as context:
            agent.basic_api_call(None)
        
        self.assertIn("Query cannot be empty or None", str(context.exception))
    
    def test_basic_api_call_whitespace_query(self):
        """Test that whitespace-only query raises ValueError."""
        agent = BaseAgent()
        
        with self.assertRaises(ValueError) as context:
            agent.basic_api_call("   \n\t  ")
        
        self.assertIn("Query cannot be empty or None", str(context.exception))
    
    def test_basic_api_call_structured_empty_query(self):
        """Test that empty query raises ValueError for structured calls."""
        agent = BaseAgent()
        
        with self.assertRaises(ValueError) as context:
            agent.basic_api_call_structured("")
        
        self.assertIn("Query cannot be empty or None", str(context.exception))
    
    # API Error Handling Tests
    def test_basic_api_call_connection_error(self):
        """Test connection error handling."""
        agent = BaseAgent()
        self.mock_llm_instance.make_api_call.side_effect = Exception("Connection timeout")
        
        with self.assertRaises(ConnectionError) as context:
            agent.basic_api_call("Test query")
        
        self.assertIn("Network connection failed", str(context.exception))
    
    def test_basic_api_call_auth_error(self):
        """Test authentication error handling."""
        agent = BaseAgent()
        self.mock_llm_instance.make_api_call.side_effect = Exception("401 Unauthorized")
        
        with self.assertRaises(Exception) as context:
            agent.basic_api_call("Test query")
        
        self.assertIn("Authentication failed", str(context.exception))
        self.assertIn("API key", str(context.exception))
    
    def test_basic_api_call_rate_limit_error(self):
        """Test rate limit error handling."""
        agent = BaseAgent()
        self.mock_llm_instance.make_api_call.side_effect = Exception("429 Rate limit exceeded")
        
        with self.assertRaises(Exception) as context:
            agent.basic_api_call("Test query")
        
        self.assertIn("Rate limit exceeded", str(context.exception))
    
    def test_basic_api_call_quota_error(self):
        """Test quota error handling."""
        agent = BaseAgent()
        self.mock_llm_instance.make_api_call.side_effect = Exception("Quota exceeded")
        
        with self.assertRaises(Exception) as context:
            agent.basic_api_call("Test query")
        
        self.assertIn("quota exceeded", str(context.exception))
    
    def test_basic_api_call_structured_connection_error(self):
        """Test connection error handling for structured calls."""
        agent = BaseAgent()
        self.mock_llm_instance.make_api_call_structured.side_effect = Exception("Connection failed")
        
        with self.assertRaises(ConnectionError) as context:
            agent.basic_api_call_structured("Test query")
        
        self.assertIn("Network connection failed", str(context.exception))
    
    # Message Cleanup Tests
    def test_message_cleanup_on_api_failure(self):
        """Test that failed user message is removed from history."""
        agent = BaseAgent()
        initial_message_count = len(agent.messages)
        
        self.mock_llm_instance.make_api_call.side_effect = Exception("API Error")
        
        with self.assertRaises(Exception):
            agent.basic_api_call("Test query")
        
        # Message count should be back to initial (user message removed)
        self.assertEqual(len(agent.messages), initial_message_count)
    
    def test_message_cleanup_on_structured_api_failure(self):
        """Test that failed user message is removed from structured call history."""
        agent = BaseAgent()
        initial_message_count = len(agent.messages)
        
        self.mock_llm_instance.make_api_call_structured.side_effect = Exception("API Error")
        
        with self.assertRaises(Exception):
            agent.basic_api_call_structured("Test query")
        
        # Message count should be back to initial (user message removed)
        self.assertEqual(len(agent.messages), initial_message_count)
    
    def test_successful_api_call_keeps_messages(self):
        """Test that successful API call keeps both user and assistant messages."""
        agent = BaseAgent()
        initial_message_count = len(agent.messages)
        
        self.mock_llm_instance.make_api_call.return_value = "Test response"
        
        response = agent.basic_api_call("Test query")
        
        # Should have 2 more messages (user + assistant)
        self.assertEqual(len(agent.messages), initial_message_count + 2)
        self.assertEqual(response, "Test response")
    
    # Configuration Validation Tests
    @patch('builtins.open', side_effect=FileNotFoundError("File not found"))
    def test_config_file_not_found(self, mock_open):
        """Test FileNotFoundError when config file doesn't exist."""
        with self.assertRaises(FileNotFoundError) as context:
            BaseAgent(config_file="nonexistent.yaml")
        
        self.assertIn("Configuration file not found", str(context.exception))
    
    @patch('builtins.open', new_callable=mock_open, read_data="invalid: yaml: [")
    @patch('yaml.safe_load', side_effect=yaml.YAMLError("Invalid YAML syntax"))
    def test_config_file_invalid_yaml(self, mock_yaml, mock_file):
        """Test YAMLError when config file has invalid syntax."""
        with self.assertRaises(yaml.YAMLError) as context:
            BaseAgent(config_file="invalid.yaml")
        
        self.assertIn("Invalid YAML in configuration file", str(context.exception))
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    def test_config_missing_required_keys(self, mock_yaml, mock_file):
        """Test ValueError when config is missing required keys."""
        mock_yaml.return_value = {"name": "test"}  # Missing system_prompt
        
        with self.assertRaises(ValueError) as context:
            BaseAgent(config_file="incomplete.yaml")
        
        self.assertIn("missing required keys", str(context.exception))
        self.assertIn("system_prompt", str(context.exception))
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    def test_config_empty_name(self, mock_yaml, mock_file):
        """Test ValueError when config has empty name."""
        mock_yaml.return_value = {
            "name": "",
            "system_prompt": "Valid prompt"
        }
        
        with self.assertRaises(ValueError) as context:
            BaseAgent(config_file="empty_name.yaml")
        
        self.assertIn("'name' must be a non-empty string", str(context.exception))
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    def test_config_empty_system_prompt(self, mock_yaml, mock_file):
        """Test ValueError when config has empty system_prompt."""
        mock_yaml.return_value = {
            "name": "test_agent",
            "system_prompt": ""
        }
        
        with self.assertRaises(ValueError) as context:
            BaseAgent(config_file="empty_prompt.yaml")
        
        self.assertIn("'system_prompt' must be a non-empty string", str(context.exception))
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    def test_config_invalid_name_type(self, mock_yaml, mock_file):
        """Test ValueError when config name is not a string."""
        mock_yaml.return_value = {
            "name": 123,
            "system_prompt": "Valid prompt"
        }
        
        with self.assertRaises(ValueError) as context:
            BaseAgent(config_file="invalid_name_type.yaml")
        
        self.assertIn("'name' must be a non-empty string", str(context.exception))
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    def test_config_invalid_prompt_type(self, mock_yaml, mock_file):
        """Test ValueError when config system_prompt is not a string."""
        mock_yaml.return_value = {
            "name": "test_agent",
            "system_prompt": ["not", "a", "string"]
        }
        
        with self.assertRaises(ValueError) as context:
            BaseAgent(config_file="invalid_prompt_type.yaml")
        
        self.assertIn("'system_prompt' must be a non-empty string", str(context.exception))
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    def test_config_valid_file(self, mock_yaml, mock_file):
        """Test successful config loading with valid file."""
        valid_config = {
            "name": "test_agent",
            "system_prompt": "This is a valid system prompt."
        }
        mock_yaml.return_value = valid_config
        
        agent = BaseAgent(config_file="valid.yaml")
        
        self.assertEqual(agent.name, "test_agent")
        self.assertEqual(agent.config, valid_config)


if __name__ == '__main__':
    unittest.main()