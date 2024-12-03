import chromadb
from chromadb.api.types import QueryResult, EmbeddingFunction, Documents, Embeddings
from typing import List, Dict, Optional, Any
import json
from datetime import datetime
import logging
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleEmbeddingFunction(EmbeddingFunction):
    """Simple embedding function that uses character-level hashing."""
    
    def __call__(self, texts: Documents) -> Embeddings:
        # Convert texts to character-level embeddings (simplified for testing)
        embeddings = []
        for text in texts:
            # Create a simple embedding based on character hashing
            chars = np.array([hash(c) % 1024 for c in text])
            # Normalize and pad/truncate to fixed size
            embedding = np.zeros(1024)
            embedding[:len(chars)] = chars
            embedding = embedding / np.linalg.norm(embedding)
            embeddings.append(embedding.tolist())
        return embeddings

class ExperienceCollector:
    """
    Collects and manages learning experiences using ChromaDB as a vector store.
    Handles code snippets, conversations, and performance metrics.
    """
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        """
        Initialize the ExperienceCollector with ChromaDB collections.
        
        Args:
            persist_directory: Directory where ChromaDB will persist its data
        """
        self.persist_directory = persist_directory
        self.chroma_client = None
        self.collections = {}
        self.embedding_function = SimpleEmbeddingFunction()
    
    async def initialize(self):
        """Initialize ChromaDB client and collections."""
        if self.persist_directory:
            self.chroma_client = chromadb.PersistentClient(
                path=self.persist_directory
            )
        else:
            self.chroma_client = chromadb.Client()
        
        # Initialize collections
        self.collections = {
            "code_snippets": self.chroma_client.get_or_create_collection(
                name="code_snippets",
                metadata={"description": "Storage for code examples and patterns"},
                embedding_function=self.embedding_function
            ),
            "conversations": self.chroma_client.get_or_create_collection(
                name="conversations",
                metadata={"description": "Storage for conversation histories"},
                embedding_function=self.embedding_function
            ),
            "metrics": self.chroma_client.get_or_create_collection(
                name="metrics",
                metadata={"description": "Storage for performance metrics"},
                embedding_function=self.embedding_function
            )
        }
        
        logger.info("ExperienceCollector initialized with collections: %s", 
                   list(self.collections.keys()))

    async def store_experience(
        self,
        collection_name: str,
        content: str,
        metadata: Dict[str, Any],
        id: Optional[str] = None
    ) -> str:
        """
        Store a new experience in the specified collection.
        
        Args:
            collection_name: Name of the collection to store in
            content: The main content to embed
            metadata: Additional metadata about the experience
            id: Optional unique identifier
            
        Returns:
            str: ID of the stored experience
        """
        if not self.chroma_client:
            raise RuntimeError("ExperienceCollector not initialized. Call initialize() first.")
            
        if collection_name not in self.collections:
            raise ValueError(f"Invalid collection name: {collection_name}")
            
        # Add timestamp to metadata
        metadata["timestamp"] = datetime.utcnow().isoformat()
        
        # Convert any lists in metadata to strings
        for key, value in metadata.items():
            if isinstance(value, (list, tuple)):
                metadata[key] = ",".join(str(x) for x in value)
        
        # Generate ID if not provided
        if id is None:
            id = f"{collection_name}_{datetime.utcnow().timestamp()}"
            
        try:
            self.collections[collection_name].add(
                documents=[content],
                metadatas=[metadata],
                ids=[id]
            )
            logger.info(f"Stored new experience in {collection_name} with ID: {id}")
            return id
            
        except Exception as e:
            logger.error(f"Error storing experience: {str(e)}")
            raise

    async def query_similar_experiences(
        self,
        collection_name: str,
        query: str,
        n_results: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Query for similar experiences in the specified collection.
        
        Args:
            collection_name: Name of the collection to query
            query: The query string to find similar experiences
            n_results: Maximum number of results to return
            metadata_filter: Optional filter for metadata fields
            
        Returns:
            List of similar experiences with their metadata
        """
        if not self.chroma_client:
            raise RuntimeError("ExperienceCollector not initialized. Call initialize() first.")
            
        if collection_name not in self.collections:
            raise ValueError(f"Invalid collection name: {collection_name}")
            
        try:
            results = self.collections[collection_name].query(
                query_texts=[query],
                n_results=n_results,
                where=metadata_filter
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results["ids"][0])):
                formatted_results.append({
                    "id": results["ids"][0][i],
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if "distances" in results else None
                })
            
            logger.info(f"Found {len(formatted_results)} similar experiences in {collection_name}")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error querying experiences: {str(e)}")
            raise

    async def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """
        Get statistics about a specific collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Dictionary containing collection statistics
        """
        if not self.chroma_client:
            raise RuntimeError("ExperienceCollector not initialized. Call initialize() first.")
            
        if collection_name not in self.collections:
            raise ValueError(f"Invalid collection name: {collection_name}")
            
        collection = self.collections[collection_name]
        
        try:
            # Get count of items
            count = collection.count()
            
            # Get peek of items
            peek = collection.peek()
            
            return {
                "name": collection_name,
                "count": count,
                "sample": peek
            }
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {str(e)}")
            raise

    async def delete_experience(self, collection_name: str, id: str):
        """
        Delete a specific experience from a collection.
        
        Args:
            collection_name: Name of the collection
            id: ID of the experience to delete
        """
        if not self.chroma_client:
            raise RuntimeError("ExperienceCollector not initialized. Call initialize() first.")
            
        if collection_name not in self.collections:
            raise ValueError(f"Invalid collection name: {collection_name}")
            
        try:
            self.collections[collection_name].delete(
                ids=[id]
            )
            logger.info(f"Deleted experience {id} from {collection_name}")
            
        except Exception as e:
            logger.error(f"Error deleting experience: {str(e)}")
            raise
