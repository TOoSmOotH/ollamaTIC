"""
Vector database operations for storing and retrieving embeddings using ChromaDB.
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime
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
        where = {"language": language} if language else None
        
        results = self.code_snippets.query(
            query_embeddings=[self._encode_text(query)],
            n_results=limit,
            where=where
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
        where = {}
        if pattern_type:
            where["type"] = pattern_type
        if language:
            where["language"] = language
            
        where = where if where else None
        
        results = self.patterns.query(
            query_embeddings=[self._encode_text(query)],
            n_results=limit,
            where=where
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
