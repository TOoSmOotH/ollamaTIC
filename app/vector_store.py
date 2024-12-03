"""
Vector database operations for storing and retrieving embeddings using ChromaDB.
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import numpy as np
import chromadb
from chromadb.config import Settings
from chromadb.errors import InvalidCollectionException
import sentence_transformers
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class VectorStore:
    """Manages vector storage and retrieval operations."""
    
    COLLECTIONS = {
        "code_snippets": "Code snippets with language metadata",
        "conversation_history": "Conversation histories",
        "learned_patterns": "Learned code patterns"
    }
    
    def __init__(self, persist_dir: str = "data/vectordb"):
        """
        Initialize the vector store with automatic collection creation.
        
        Args:
            persist_dir: Directory to store the vector database
        """
        # Ensure persist directory exists
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.Client(Settings(
            persist_directory=persist_dir,
            is_persistent=True
        ))
        
        self.encoder = sentence_transformers.SentenceTransformer('all-MiniLM-L6-v2')
        
        # Initialize collections
        logger.info("Initializing vector store collections")
        self._init_collections()
    
    def _init_collections(self):
        """Initialize collections if they don't exist."""
        for name, description in self.COLLECTIONS.items():
            try:
                collection = self.client.get_collection(name)
                logger.debug(f"Collection '{name}' already exists")
            except InvalidCollectionException:
                collection = self.client.create_collection(
                    name=name,
                    metadata={"description": description}
                )
                logger.info(f"Created collection '{name}'")
            
            # Store collection reference
            setattr(self, f"_{name}", collection)
    
    @property
    def code_snippets(self):
        """Get the code snippets collection."""
        return self._code_snippets
    
    @property
    def conversations(self):
        """Get the conversation history collection."""
        return self._conversation_history
    
    @property
    def patterns(self):
        """Get the learned patterns collection."""
        return self._learned_patterns
    
    def _encode_text(self, text: str) -> List[float]:
        """Encode text into vector embedding."""
        return self.encoder.encode(text).tolist()
    
    def store_code_snippet(self, 
                          code: str, 
                          language: str, 
                          metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store a code snippet with its metadata."""
        logger.info(f"Storing code snippet for language: {language}")
        logger.debug(f"Code snippet (first 100 chars): {code[:100]}...")
        
        if metadata is None:
            metadata = {}
            
        # Generate unique ID
        snippet_id = f"snippet_{hash(f"{code}{datetime.now().isoformat()}")}"
        
        self.code_snippets.add(
            ids=[snippet_id],
            embeddings=[self._encode_text(code)],
            metadatas=[{
                "language": language,
                "timestamp": datetime.now().isoformat(),
                **{k: str(v) if isinstance(v, (list, dict)) else v for k, v in metadata.items()}
            }],
            documents=[code]
        )
        
        return snippet_id
    
    def store_conversation(self, 
                          messages: List[Dict[str, str]], 
                          metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store a conversation history."""
        logger.info("Storing conversation history")
        logger.debug(f"Number of messages: {len(messages)}")
        
        if metadata is None:
            metadata = {}
            
        # Concatenate messages for embedding and storage
        conversation_text = " ".join([
            f"{msg.get('role', 'unknown')}: {msg.get('content', '')}"
            for msg in messages
        ])
        
        # Generate unique ID
        conv_id = f"conv_{hash(f"{conversation_text}{datetime.now().isoformat()}")}"
        
        self.conversations.add(
            ids=[conv_id],
            embeddings=[self._encode_text(conversation_text)],
            metadatas=[{
                "messages": json.dumps(messages),
                "timestamp": datetime.now().isoformat(),
                **{k: str(v) if isinstance(v, (list, dict)) else v for k, v in metadata.items()}
            }],
            documents=[conversation_text]
        )
        
        return conv_id
    
    def store_pattern(self,
                     pattern: Dict[str, Any],
                     pattern_type: str,
                     language: str) -> str:
        """Store a learned pattern."""
        logger.info(f"Storing {pattern_type} pattern for language: {language}")
        logger.debug(f"Pattern: {pattern}")
        
        # Convert pattern to string for embedding
        pattern_text = json.dumps(pattern)
        
        # Generate unique ID
        pattern_id = f"pattern_{hash(f"{pattern_text}{datetime.now().isoformat()}")}"
        
        self.patterns.add(
            ids=[pattern_id],
            embeddings=[self._encode_text(pattern_text)],
            metadatas=[{
                "type": pattern_type,
                "language": language,
                "timestamp": datetime.now().isoformat()
            }],
            documents=[pattern_text]
        )
        
        return pattern_id
    
    def search_code_snippets(self,
                           query: str,
                           language: Optional[str] = None,
                           limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar code snippets."""
        logger.info(f"Searching code snippets for query: {query}")
        logger.debug(f"Language filter: {language}")
        
        where_conditions = {"language": {"$eq": language}} if language else None
        
        results = self.code_snippets.query(
            query_embeddings=[self._encode_text(query)],
            n_results=limit,
            where=where_conditions
        )
        
        return [
            {
                "id": id,
                "code": document,
                "score": float(distance),
                **metadata
            }
            for id, document, metadata, distance in zip(
                results["ids"][0],
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0]
            )
        ]
    
    def search_conversations(self,
                           query: str,
                           limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar conversations."""
        logger.info(f"Searching conversations for query: {query}")
        
        results = self.conversations.query(
            query_embeddings=[self._encode_text(query)],
            n_results=limit
        )
        
        return [
            {
                "id": id,
                "text": document,
                "score": float(distance),
                "messages": json.loads(metadata["messages"]),
                "timestamp": metadata["timestamp"]
            }
            for id, document, metadata, distance in zip(
                results["ids"][0],
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0]
            )
        ]
    
    def search_patterns(self,
                       query: str,
                       pattern_type: Optional[str] = None,
                       language: Optional[str] = None,
                       limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar patterns."""
        logger.info(f"Searching patterns for query: {query}")
        logger.debug(f"Pattern type filter: {pattern_type}, Language filter: {language}")
        
        # Build where clause conditions
        where_conditions = {}
        if pattern_type and language:
            where_conditions = {
                "$and": [
                    {"type": {"$eq": pattern_type}},
                    {"language": {"$eq": language}}
                ]
            }
        elif pattern_type:
            where_conditions = {"type": {"$eq": pattern_type}}
        elif language:
            where_conditions = {"language": {"$eq": language}}
        
        results = self.patterns.query(
            query_embeddings=[self._encode_text(query)],
            n_results=limit,
            where=where_conditions if where_conditions else None
        )
        
        return [
            {
                "id": id,
                "pattern": json.loads(document),
                "score": float(distance),
                **metadata
            }
            for id, document, metadata, distance in zip(
                results["ids"][0],
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0]
            )
        ]
    
    def get_collection_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics about the collections."""
        logger.info("Retrieving collection statistics")
        
        return {
            "code_snippets": {
                "count": self.code_snippets.count(),
                "name": self.code_snippets.name,
                "metadata": self.code_snippets.metadata
            },
            "conversations": {
                "count": self.conversations.count(),
                "name": self.conversations.name,
                "metadata": self.conversations.metadata
            },
            "patterns": {
                "count": self.patterns.count(),
                "name": self.patterns.name,
                "metadata": self.patterns.metadata
            }
        }
    
    def list_collections(self) -> List[str]:
        """List all available collections."""
        logger.info("Listing available collections")
        
        return list(self.COLLECTIONS.keys())
    
    def get_collection_count(self, collection_name: str) -> int:
        """Get the number of items in a collection."""
        logger.info(f"Retrieving count for collection: {collection_name}")
        
        collection = getattr(self, f"_{collection_name}")
        return collection.count()
    
    def get_embedding_dimension(self, collection_name: str) -> int:
        """Get the embedding dimension of a collection."""
        logger.info(f"Retrieving embedding dimension for collection: {collection_name}")
        
        # MiniLM-L6-v2 has 384 dimensions
        return 384
    
    def get_last_update_time(self, collection_name: str) -> datetime:
        """Get the last update time of a collection."""
        logger.info(f"Retrieving last update time for collection: {collection_name}")
        
        collection = getattr(self, f"_{collection_name}")
        # Get all items
        result = collection.get()
        
        if result and result['metadatas']:
            # Find the most recent timestamp
            timestamps = [
                datetime.fromisoformat(meta['timestamp'])
                for meta in result['metadatas']
                if 'timestamp' in meta
            ]
            if timestamps:
                return max(timestamps)
        
        return datetime.now()
    
    def search(self, collection_name: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search within a specific collection."""
        logger.info(f"Searching collection: {collection_name} for query: {query}")
        
        collection = getattr(self, f"_{collection_name}")
        query_embedding = self._encode_text(query)
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=limit
        )
        
        output = []
        if results['ids']:
            for i in range(len(results['ids'][0])):
                output.append({
                    "content": results['documents'][0][i] if 'documents' in results else "No content available",
                    "metadata": results['metadatas'][0][i],
                    "score": float(results['distances'][0][i]) if 'distances' in results else 0.0
                })
        return output
    
    def clean_collection(self, collection_name: str, older_than_days: Optional[int] = None, 
                        min_score: Optional[float] = None) -> int:
        """Clean up a collection based on age or quality criteria."""
        logger.info(f"Cleaning collection: {collection_name}")
        
        collection = getattr(self, f"_{collection_name}")
        where_clause = {}
        
        if older_than_days:
            cutoff_date = (datetime.now() - timedelta(days=older_than_days)).isoformat()
            where_clause["timestamp"] = {"$lt": cutoff_date}
            
        # Get IDs to remove
        results = collection.get(where=where_clause)
        if not results['ids']:
            return 0
            
        # Apply score filter if specified
        ids_to_remove = []
        if min_score is not None:
            for i, metadata in enumerate(results['metadatas']):
                if metadata.get('success_rate', 0) < min_score:
                    ids_to_remove.append(results['ids'][i])
        else:
            ids_to_remove = results['ids']
        
        if ids_to_remove:
            collection.delete(ids=ids_to_remove)
        
        return len(ids_to_remove)
    
    def export_collection(self, collection_name: str) -> Dict[str, Any]:
        """Export a collection's data."""
        logger.info(f"Exporting collection: {collection_name}")
        
        collection = getattr(self, f"_{collection_name}")
        results = collection.get()
        
        return {
            "name": collection_name,
            "description": self.COLLECTIONS[collection_name],
            "timestamp": datetime.now().isoformat(),
            "data": {
                "ids": results['ids'],
                "embeddings": results['embeddings'],
                "metadatas": results['metadatas'],
                "documents": results.get('documents', [])
            }
        }
    
    def import_collection(self, collection_name: str, data: Dict[str, Any]) -> None:
        """Import data into a collection."""
        logger.info(f"Importing data into collection: {collection_name}")
        
        collection = getattr(self, f"_{collection_name}")
        
        # Validate the data structure
        required_keys = ["ids", "embeddings", "metadatas"]
        if not all(key in data["data"] for key in required_keys):
            raise ValueError("Invalid data format")
        
        # Add the data to the collection
        collection.add(
            ids=data["data"]["ids"],
            embeddings=data["data"]["embeddings"],
            metadatas=data["data"]["metadatas"],
            documents=data["data"].get("documents", [])
        )
