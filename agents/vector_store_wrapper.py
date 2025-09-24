from typing import List, Dict, Any, Optional
from .vector_store_factory import VectorStoreProviderFactory
from .vector_store_providers import BaseVectorStoreProvider


class VectorStoreWrapper:
    """
    Wrapper class for different vector store providers.
    
    This class provides a unified interface using the provider pattern.
    """
    
    def __init__(self, provider: str = "openai", **provider_kwargs) -> None:
        """
        Initialize the VectorStoreWrapper with the specified provider.
        
        Args:
            provider (str): The provider to use ("openai", "chromadb", "chroma")
            **provider_kwargs: Additional arguments to pass to the provider
        """
        self.provider_name = provider
        self.provider = VectorStoreProviderFactory.create_provider(provider, **provider_kwargs)
    
    def create_vector_store(self, name: str, file_ids: Optional[List[str]] = None) -> str:
        """
        Create a new vector store.
        
        Args:
            name (str): Name for the vector store
            file_ids (Optional[List[str]]): List of file IDs to add to the vector store
            
        Returns:
            str: Vector store ID
        """
        return self.provider.create_vector_store(name, file_ids)
    
    def upload_file(self, file_path: str, purpose: str = "assistants") -> str:
        """
        Upload a file for use in vector stores.
        
        Args:
            file_path (str): Path to the file to upload
            purpose (str): Purpose of the file (default: "assistants")
            
        Returns:
            str: File ID
        """
        return self.provider.upload_file(file_path, purpose)
    
    def add_files_to_vector_store(self, vector_store_id: str, file_ids: List[str]) -> None:
        """
        Add files to an existing vector store.
        
        Args:
            vector_store_id (str): ID of the vector store
            file_ids (List[str]): List of file IDs to add
        """
        return self.provider.add_files_to_vector_store(vector_store_id, file_ids)
    
    def search_vector_store(
        self, 
        vector_store_id: str, 
        query: str, 
        limit: int = 20,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search a vector store for relevant content.
        
        Args:
            vector_store_id (str): ID of the vector store to search
            query (str): Search query
            limit (int): Maximum number of results to return (default: 20)
            filter_metadata (Optional[Dict[str, Any]]): Metadata filters to apply
            
        Returns:
            List[Dict[str, Any]]: List of search results with content and metadata
        """
        return self.provider.search_vector_store(vector_store_id, query, limit, filter_metadata)
    
    def list_vector_stores(self) -> List[Dict[str, Any]]:
        """
        List all vector stores.
        
        Returns:
            List[Dict[str, Any]]: List of vector stores with id, name, and metadata
        """
        return self.provider.list_vector_stores()
    
    def delete_vector_store(self, vector_store_id: str) -> bool:
        """
        Delete a vector store.
        
        Args:
            vector_store_id (str): ID of the vector store to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.provider.delete_vector_store(vector_store_id)
    
    def get_vector_store_status(self, vector_store_id: str) -> Dict[str, Any]:
        """
        Get the status and details of a vector store.
        
        Args:
            vector_store_id (str): ID of the vector store
            
        Returns:
            Dict[str, Any]: Vector store details including status and file counts
        """
        return self.provider.get_vector_store_status(vector_store_id)
    
    def get_store_id_by_name(self, name: str) -> Optional[str]:
        """
        Get vector store ID by name.
        
        Args:
            name (str): Name of the vector store to find
            
        Returns:
            Optional[str]: Vector store ID if found, None otherwise
        """
        if hasattr(self.provider, 'get_store_id_by_name'):
            return self.provider.get_store_id_by_name(name)
        
        # Fallback implementation for providers that don't have this method
        vector_stores = self.list_vector_stores()
        for vs in vector_stores:
            if vs["name"] == name:
                return vs["id"]
        return None
    
    def search_for_file(self, vector_store_id: str, query: str) -> Optional[str]:
        """
        Search vector store and return the filename that most closely matches the query.
        
        Args:
            vector_store_id (str): ID of the vector store to search
            query (str): Search query
            
        Returns:
            Optional[str]: Filename of the most relevant result, None if no results
        """
        return self.provider.search_for_file(vector_store_id, query)