import os
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from openai import OpenAI


class BaseVectorStoreProvider(ABC):
    """
    Abstract base class for vector store providers.
    
    This class defines the interface that all vector store providers must implement.
    """
    
    @abstractmethod
    def create_vector_store(self, name: str, file_ids: Optional[List[str]] = None) -> str:
        """
        Create a new vector store.
        
        Args:
            name (str): Name for the vector store
            file_ids (Optional[List[str]]): List of file IDs to add to the vector store
            
        Returns:
            str: Vector store ID
        """
        pass
    
    @abstractmethod
    def upload_file(self, file_path: str, purpose: str = "assistants") -> str:
        """
        Upload a file for use in vector stores.
        
        Args:
            file_path (str): Path to the file to upload
            purpose (str): Purpose of the file
            
        Returns:
            str: File ID
        """
        pass
    
    @abstractmethod
    def add_files_to_vector_store(self, vector_store_id: str, file_ids: List[str]) -> None:
        """
        Add files to an existing vector store.
        
        Args:
            vector_store_id (str): ID of the vector store
            file_ids (List[str]): List of file IDs to add
        """
        pass
    
    @abstractmethod
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
            limit (int): Maximum number of results to return
            filter_metadata (Optional[Dict[str, Any]]): Metadata filters to apply
            
        Returns:
            List[Dict[str, Any]]: List of search results with content and metadata
        """
        pass
    
    @abstractmethod
    def list_vector_stores(self) -> List[Dict[str, Any]]:
        """
        List all vector stores.
        
        Returns:
            List[Dict[str, Any]]: List of vector stores with id, name, and metadata
        """
        pass
    
    @abstractmethod
    def delete_vector_store(self, vector_store_id: str) -> bool:
        """
        Delete a vector store.
        
        Args:
            vector_store_id (str): ID of the vector store to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_vector_store_status(self, vector_store_id: str) -> Dict[str, Any]:
        """
        Get the status and details of a vector store.
        
        Args:
            vector_store_id (str): ID of the vector store
            
        Returns:
            Dict[str, Any]: Vector store details including status and file counts
        """
        pass
    
    @abstractmethod
    def search_for_file(self, vector_store_id: str, query: str) -> Optional[str]:
        """
        Search vector store and return the filename that most closely matches the query.
        
        Args:
            vector_store_id (str): ID of the vector store to search
            query (str): Search query
            
        Returns:
            Optional[str]: Filename of the most relevant result, None if no results
        """
        pass


class OpenAIVectorStoreProvider(BaseVectorStoreProvider):
    """
    OpenAI Vector Store provider implementation.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the OpenAI Vector Store provider.
        
        Args:
            api_key (Optional[str]): OpenAI API key. If not provided, will use OPENAI_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set.")
        self.client = OpenAI(api_key=self.api_key)
    
    def create_vector_store(self, name: str, file_ids: Optional[List[str]] = None) -> str:
        vector_store_data = {"name": name}
        if file_ids:
            vector_store_data["file_ids"] = file_ids
            
        vector_store = self.client.vector_stores.create(**vector_store_data)
        return vector_store.id
    
    def upload_file(self, file_path: str, purpose: str = "assistants") -> str:
        with open(file_path, "rb") as file:
            uploaded_file = self.client.files.create(file=file, purpose=purpose)
        return uploaded_file.id
    
    def add_files_to_vector_store(self, vector_store_id: str, file_ids: List[str]) -> None:
        for file_id in file_ids:
            self.client.vector_stores.files.create(
                vector_store_id=vector_store_id,
                file_id=file_id
            )
    
    def search_vector_store(
        self, 
        vector_store_id: str, 
        query: str, 
        limit: int = 20,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        search_params = {
            "query": query,
            "max_num_results": limit
        }
        
        results = self.client.vector_stores.search(
            vector_store_id=vector_store_id,
            **search_params
        )
        
        return [{"content": result.content, "metadata": getattr(result, 'metadata', {})} for result in results.data]
    
    def list_vector_stores(self) -> List[Dict[str, Any]]:
        vector_stores = self.client.vector_stores.list()
        return [
            {
                "id": vs.id, 
                "name": vs.name, 
                "created_at": vs.created_at,
                "file_counts": vs.file_counts
            } 
            for vs in vector_stores.data
        ]
    
    def delete_vector_store(self, vector_store_id: str) -> bool:
        try:
            self.client.vector_stores.delete(vector_store_id)
            return True
        except Exception:
            return False
    
    def get_vector_store_status(self, vector_store_id: str) -> Dict[str, Any]:
        vector_store = self.client.vector_stores.retrieve(vector_store_id)
        return {
            "id": vector_store.id,
            "name": vector_store.name,
            "status": vector_store.status,
            "file_counts": vector_store.file_counts,
            "created_at": vector_store.created_at,
            "last_active_at": vector_store.last_active_at
        }
    
    def search_for_file(self, vector_store_id: str, query: str) -> Optional[str]:
        results = self.client.responses.create(
            model="gpt-4o",
            input=query,
            tools=[{
                "type": "file_search",
                "vector_store_ids": [vector_store_id]
            }]
        )
        
        try:
            return results.output[1].content[0].annotations[0].filename
        except (IndexError, AttributeError):
            return None


class ChromaDBVectorStoreProvider(BaseVectorStoreProvider):
    """
    ChromaDB Vector Store provider implementation.
    """
    
    def __init__(self, persist_directory: str = "./chroma_db", collection_name: str = "default"):
        """
        Initialize the ChromaDB Vector Store provider.
        
        Args:
            persist_directory (str): Directory to persist ChromaDB data
            collection_name (str): Default collection name
        """
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError:
            raise ImportError("ChromaDB not installed. Install with: pip install chromadb")
        
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        self.default_collection_name = collection_name
        self.collections = {}
    
    def create_vector_store(self, name: str, file_ids: Optional[List[str]] = None) -> str:
        collection = self.client.create_collection(
            name=name,
            metadata={"created_by": "agent_boilerplate"}
        )
        self.collections[name] = collection
        
        if file_ids:
            self.add_files_to_vector_store(name, file_ids)
        
        return name
    
    def upload_file(self, file_path: str, purpose: str = "assistants") -> str:
        """
        For ChromaDB, we return the file path as the 'file_id' since we'll process it directly.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        return file_path
    
    def add_files_to_vector_store(self, vector_store_id: str, file_ids: List[str]) -> None:
        if vector_store_id not in self.collections:
            try:
                self.collections[vector_store_id] = self.client.get_collection(vector_store_id)
            except Exception:
                raise ValueError(f"Vector store '{vector_store_id}' not found")
        
        collection = self.collections[vector_store_id]
        documents = []
        metadatas = []
        ids = []
        
        for i, file_path in enumerate(file_ids):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    documents.append(content)
                    metadatas.append({
                        "filename": os.path.basename(file_path),
                        "file_path": file_path,
                        "source": file_path
                    })
                    ids.append(f"{vector_store_id}_{i}_{os.path.basename(file_path)}")
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
                continue
        
        if documents:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
    
    def search_vector_store(
        self, 
        vector_store_id: str, 
        query: str, 
        limit: int = 20,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        if vector_store_id not in self.collections:
            try:
                self.collections[vector_store_id] = self.client.get_collection(vector_store_id)
            except Exception:
                raise ValueError(f"Vector store '{vector_store_id}' not found")
        
        collection = self.collections[vector_store_id]
        
        search_kwargs = {
            "query_texts": [query],
            "n_results": limit
        }
        
        if filter_metadata:
            search_kwargs["where"] = filter_metadata
        
        results = collection.query(**search_kwargs)
        
        formatted_results = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                result = {
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] and results["metadatas"][0] else {}
                }
                formatted_results.append(result)
        
        return formatted_results
    
    def list_vector_stores(self) -> List[Dict[str, Any]]:
        collections = self.client.list_collections()
        return [
            {
                "id": collection.name,
                "name": collection.name,
                "created_at": collection.metadata.get("created_at", "unknown"),
                "file_counts": {"total": collection.count()}
            }
            for collection in collections
        ]
    
    def delete_vector_store(self, vector_store_id: str) -> bool:
        try:
            self.client.delete_collection(vector_store_id)
            if vector_store_id in self.collections:
                del self.collections[vector_store_id]
            return True
        except Exception:
            return False
    
    def get_vector_store_status(self, vector_store_id: str) -> Dict[str, Any]:
        if vector_store_id not in self.collections:
            try:
                self.collections[vector_store_id] = self.client.get_collection(vector_store_id)
            except Exception:
                raise ValueError(f"Vector store '{vector_store_id}' not found")
        
        collection = self.collections[vector_store_id]
        return {
            "id": collection.name,
            "name": collection.name,
            "status": "active",
            "file_counts": {"total": collection.count()},
            "created_at": collection.metadata.get("created_at", "unknown"),
            "last_active_at": "unknown"
        }
    
    def search_for_file(self, vector_store_id: str, query: str) -> Optional[str]:
        results = self.search_vector_store(vector_store_id, query, limit=1)
        
        if results and len(results) > 0:
            metadata = results[0].get("metadata", {})
            filename = metadata.get("filename") or metadata.get("file_name") or metadata.get("source")
            return filename
        
        return None
    
    def get_store_id_by_name(self, name: str) -> Optional[str]:
        """
        Get vector store ID by name. For ChromaDB, the name IS the ID.
        
        Args:
            name (str): Name of the vector store to find
            
        Returns:
            Optional[str]: Vector store ID if found, None otherwise
        """
        try:
            self.client.get_collection(name)
            return name
        except Exception:
            return None