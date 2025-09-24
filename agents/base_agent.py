import yaml
from typing import Dict, Any, Optional, Union, List
from .llm_wrapper import LLMWrapper
from .vector_store_wrapper import VectorStoreWrapper

class BaseAgent:
    """
    Base class for all agents.

    Attributes:
        config (Dict[str, Any]): Configuration loaded from the config file.
        llm (LLMWrapper): Wrapper for the language model.
        context (str): Context for the agent.
    """

    def __init__(self, config_file: str = None, llm: str = "openai", schema_path: Optional[str] = None, enable_vector_store: bool = False, vector_store_provider: str = "openai", max_messages: int = 3, **vector_store_kwargs) -> None:
        """
        Initializes the BaseAgent with a configuration file.

        Args:
            config_file (str): Path to the configuration file. Defaults to None.
            llm (str): LLM provider to use. Defaults to "openai".
            schema_path (Optional[str]): Path to YAML schema file for structured responses.
            enable_vector_store (bool): Whether to enable vector store functionality. Defaults to False.
            vector_store_provider (str): Vector store provider to use. Defaults to "openai".
            max_messages (int): Maximum number of messages to keep (excluding system prompt). Defaults to 3.
            **vector_store_kwargs: Additional arguments to pass to the vector store provider.
        """
        if config_file:
            self.config = self.load_config_file(config_file)
        else:
            self.config = self.default_config()
            
        self.llm = LLMWrapper(llm, schema_path=schema_path)
        self.name = self.config["name"]
        self.max_messages = max_messages
        self.messages = []
        self.messages.append({
                "role": "system",
                "content": self.config['system_prompt']
            })
        
        # Initialize vector store if enabled
        self.vector_store = VectorStoreWrapper(vector_store_provider, **vector_store_kwargs) if enable_vector_store else None
        self.vector_store_id = None
        

    def load_config_file(self, config_file: str) -> Dict[str, Any]:
        """
        Loads the configuration file.

        Args:
            config_file (str): Path to the configuration file.

        Returns:
            Dict[str, Any]: Configuration dictionary.
        """
        with open(config_file, 'r') as file:
            config = yaml.safe_load(file)
        return config

    def default_config(self) -> Dict[str, Any]:
        """
        Provides a default configuration.

        Returns:
            Dict[str, Any]: Default configuration dictionary.
        """
        return {
            "name": "default_agent",
            "system_prompt": "Default system prompt.",
            "llm": "openAI"
        }

    def _trim_messages(self) -> None:
        """
        Trim messages to keep only the system prompt + max_messages.
        Always keeps the system prompt (first message) and the most recent max_messages.
        """
        if len(self.messages) > self.max_messages + 1:  # +1 for system prompt
            # Keep system prompt + most recent max_messages
            system_prompt = self.messages[0]
            recent_messages = self.messages[-(self.max_messages):]
            self.messages = [system_prompt] + recent_messages

    def basic_api_call(self, query: str) -> str:
        """
        Makes a basic API call to the language model with the provided query.

        Args:
            query (str): The query to send to the language model.

        Returns:
            str: The response from the language model.
        """
        # messages = [
        #     {
        #         "role": "system",
        #         "content": self.config['system_prompt']
        #     },
        #     {"role": "user", "content": query}
        # ]

        self.messages.append({"role": "user", "content": query})
        self._trim_messages()
        response = self.llm.make_api_call(self.messages)
        self.messages.append({"role": "assistant", "content": response})
        self._trim_messages()
        return response

    def basic_api_call_structured(self, query: str) -> Any:
        """
        Makes a basic API call to the language model with the provided query and expects a structured response.
        Uses the schema model set during agent initialization.

        Args:
            query (str): The query to send to the language model.

        Returns:
            Any: The structured response from the language model.
        """
        # messages = [
        #     {
        #         "role": "system",
        #         "content": self.config['system_prompt']
        #     },
        #     {"role": "user", "content": query}
        # ]
        # response = self.llm.make_api_call_structured(messages)
        self.messages.append({"role": "user", "content": query})
        self._trim_messages()
        response = self.llm.make_api_call_structured(self.messages)
        # For structured responses, convert to string for message history
        response_str = str(response) if hasattr(response, '__str__') else str(response)
        self.messages.append({"role": "assistant", "content": response_str})
        self._trim_messages()
        return response

    def create_vector_store(self, name: str, file_paths: Optional[List[str]] = None) -> str:
        """
        Create a vector store and optionally add files to it.
        
        Args:
            name (str): Name for the vector store
            file_paths (Optional[List[str]]): List of file paths to upload and add to the vector store
            
        Returns:
            str: Vector store ID
        """
        if not self.vector_store:
            raise ValueError("Vector store not enabled. Initialize agent with enable_vector_store=True")
        
        file_ids = []
        if file_paths:
            for file_path in file_paths:
                file_id = self.vector_store.upload_file(file_path)
                file_ids.append(file_id)
        
        self.vector_store_id = self.vector_store.create_vector_store(name, file_ids)
        return self.vector_store_id

    def add_files_to_vector_store(self, file_paths: List[str], vector_store_id: Optional[str] = None) -> List[str]:
        """
        Upload files and add them to the vector store.
        
        Args:
            file_paths (List[str]): List of file paths to upload
            vector_store_id (Optional[str]): Vector store ID. Uses agent's default if not provided.
            
        Returns:
            List[str]: List of uploaded file IDs
        """
        if not self.vector_store:
            raise ValueError("Vector store not enabled. Initialize agent with enable_vector_store=True")
        
        store_id = vector_store_id or self.vector_store_id
        if not store_id:
            raise ValueError("No vector store ID available. Create a vector store first.")
        
        file_ids = []
        for file_path in file_paths:
            file_id = self.vector_store.upload_file(file_path)
            file_ids.append(file_id)
        
        self.vector_store.add_files_to_vector_store(store_id, file_ids)
        return file_ids

    def search_vector_store(self, query: str, limit: int = 20, vector_store_id: Optional[str] = None, filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search the vector store for relevant content.
        
        Args:
            query (str): Search query
            limit (int): Maximum number of results to return
            vector_store_id (Optional[str]): Vector store ID. Uses agent's default if not provided.
            filter_metadata (Optional[Dict[str, Any]]): Metadata filters to apply
            
        Returns:
            List[Dict[str, Any]]: List of search results
        """
        if not self.vector_store:
            raise ValueError("Vector store not enabled. Initialize agent with enable_vector_store=True")
        
        store_id = vector_store_id or self.vector_store_id
        if not store_id:
            raise ValueError("No vector store ID available. Create a vector store first.")
        
        return self.vector_store.search_vector_store(store_id, query, limit, filter_metadata)

    def query_with_context(self, query: str, context_query: Optional[str] = None, max_context_results: int = 5) -> str:
        """
        Query the LLM with additional context from the vector store.
        
        Args:
            query (str): The main query to send to the LLM
            context_query (Optional[str]): Query to search vector store for context. Uses main query if not provided.
            max_context_results (int): Maximum number of context results to include
            
        Returns:
            str: The response from the language model with vector store context
        """
        if not self.vector_store or not self.vector_store_id:
            return self.basic_api_call(query)
        
        search_query = context_query or query
        context_results = self.search_vector_store(search_query, limit=max_context_results)
        
        if context_results:
            context_text = "\n\n".join([result["content"] for result in context_results])
            enhanced_query = f"Context from knowledge base:\n{context_text}\n\nUser query: {query}"
        else:
            enhanced_query = query
        
        return self.basic_api_call(enhanced_query)

    def list_vector_stores(self) -> List[Dict[str, Any]]:
        """
        List all available vector stores.
        
        Returns:
            List[Dict[str, Any]]: List of vector stores
        """
        if not self.vector_store:
            raise ValueError("Vector store not enabled. Initialize agent with enable_vector_store=True")
        
        return self.vector_store.list_vector_stores()

    def set_vector_store(self, vector_store_id: str) -> None:
        """
        Set the active vector store for this agent.
        
        Args:
            vector_store_id (str): ID of the vector store to use
        """
        self.vector_store_id = vector_store_id

    def get_vector_store_status(self, vector_store_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get status and details of the vector store.
        
        Args:
            vector_store_id (Optional[str]): Vector store ID. Uses agent's default if not provided.
            
        Returns:
            Dict[str, Any]: Vector store status and details
        """
        if not self.vector_store:
            raise ValueError("Vector store not enabled. Initialize agent with enable_vector_store=True")
        
        store_id = vector_store_id or self.vector_store_id
        if not store_id:
            raise ValueError("No vector store ID available.")
        
        return self.vector_store.get_vector_store_status(store_id)

    def get_store_id_by_name(self, name: str) -> Optional[str]:
        """
        Get vector store ID by name.
        
        Args:
            name (str): Name of the vector store to find
            
        Returns:
            Optional[str]: Vector store ID if found, None otherwise
        """
        if not self.vector_store:
            raise ValueError("Vector store not enabled. Initialize agent with enable_vector_store=True")
        
        return self.vector_store.get_store_id_by_name(name)

    def set_vector_store_by_name(self, name: str) -> bool:
        """
        Set the active vector store by name.
        
        Args:
            name (str): Name of the vector store to use
            
        Returns:
            bool: True if found and set, False if not found
        """
        store_id = self.get_store_id_by_name(name)
        if store_id:
            self.vector_store_id = store_id
            return True
        return False

    def search_for_file(self, query: str, vector_store_id: Optional[str] = None) -> Optional[str]:
        """
        Search vector store and return the filename that most closely matches the query.
        
        Args:
            query (str): Search query
            vector_store_id (Optional[str]): Vector store ID. Uses agent's default if not provided.
            
        Returns:
            Optional[str]: Filename of the most relevant result, None if no results
        """
        if not self.vector_store:
            raise ValueError("Vector store not enabled. Initialize agent with enable_vector_store=True")
        
        store_id = vector_store_id or self.vector_store_id
        if not store_id:
            raise ValueError("No vector store ID available. Create a vector store first.")
        
        return self.vector_store.search_for_file(store_id, query)