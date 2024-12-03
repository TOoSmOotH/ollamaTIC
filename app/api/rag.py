from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.vector_store import VectorStore
from app.learning import LearningSystem
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
vector_store = VectorStore()
learning_system = LearningSystem(vector_store=vector_store)

class CollectionStats(BaseModel):
    name: str
    count: int
    embedding_dimension: int
    last_updated: datetime

class SearchResult(BaseModel):
    content: str
    metadata: Dict[str, Any]
    score: float

class RAGInsight(BaseModel):
    collection_name: str
    pattern_type: str
    frequency: int
    success_rate: float
    last_used: datetime
    examples: List[str]

@router.get("/collections")
async def get_collections() -> List[CollectionStats]:
    """Get statistics for all collections in the vector store"""
    collections = vector_store.list_collections()
    stats = []
    for collection in collections:
        count = vector_store.get_collection_count(collection)
        dim = vector_store.get_embedding_dimension(collection)
        last_updated = vector_store.get_last_update_time(collection)
        stats.append(CollectionStats(
            name=collection,
            count=count,
            embedding_dimension=dim,
            last_updated=last_updated
        ))
    return stats

@router.get("/search/{collection_name}")
async def search_collection(
    collection_name: str,
    query: str,
    limit: int = 5
) -> List[SearchResult]:
    """Search within a specific collection"""
    results = vector_store.search(
        collection_name=collection_name,
        query=query,
        limit=limit
    )
    return [
        SearchResult(
            content=result["content"],
            metadata=result["metadata"],
            score=result["score"]
        ) for result in results
    ]

@router.get("/insights")
async def get_insights():
    """Get learned insights from the system"""
    try:
        # Get all patterns and code snippets
        patterns = vector_store.search_patterns(
            query="",  # Empty query to get all patterns
            pattern_type="language_patterns",
            limit=20
        )
        
        code_snippets = vector_store.search_code_snippets(
            query="",  # Empty query to get all snippets
            limit=50
        )
        
        if not patterns and not code_snippets:
            return {"message": "No insights available yet", "insights": []}
            
        # Group insights by language
        insights_by_language = {}
        
        # Process patterns
        for pattern in patterns:
            pattern_data = pattern.get("pattern", {})
            if not pattern_data:
                continue
                
            language = pattern_data.get("language", "unknown")
            if language == "unknown":
                continue
                
            if language not in insights_by_language:
                insights_by_language[language] = {
                    "language": language,
                    "common_imports": {},
                    "function_patterns": {},
                    "error_patterns": {},
                    "best_practices": {},
                    "code_examples": []
                }
            
            # Merge pattern data
            current = insights_by_language[language]
            current["common_imports"].update(pattern_data.get("common_imports", {}))
            current["function_patterns"].update(pattern_data.get("function_patterns", {}))
            current["error_patterns"].update(pattern_data.get("error_patterns", {}))
            current["best_practices"].update(pattern_data.get("best_practices", {}))
        
        # Add code examples
        for snippet in code_snippets:
            language = snippet.get("metadata", {}).get("language", "unknown")
            if language == "unknown" or language not in insights_by_language:
                continue
                
            code = snippet.get("content", "").strip()
            if not code:
                continue
                
            success_rate = snippet.get("metadata", {}).get("success_rate", 0.0)
            usage_count = snippet.get("metadata", {}).get("usage_count", 0)
            
            # Only include successful examples
            if success_rate >= 0.7 and usage_count > 0:
                insights_by_language[language]["code_examples"].append({
                    "code": code,
                    "success_rate": success_rate,
                    "usage_count": usage_count,
                    "context": snippet.get("metadata", {}).get("context", "")
                })
        
        # Filter out languages with no meaningful insights
        insights = []
        for language, data in insights_by_language.items():
            if any([
                data["common_imports"],
                data["function_patterns"],
                data["error_patterns"],
                data["best_practices"],
                data["code_examples"]
            ]):
                # Sort code examples by success rate and usage count
                data["code_examples"].sort(
                    key=lambda x: (x["success_rate"], x["usage_count"]),
                    reverse=True
                )
                # Keep only top 5 examples
                data["code_examples"] = data["code_examples"][:5]
                insights.append(data)
        
        return {
            "message": "Successfully retrieved insights" if insights else "No meaningful insights available yet",
            "insights": insights
        }
        
    except Exception as e:
        logger.error(f"Error getting insights: {str(e)}")
        return {"message": f"Error retrieving insights: {str(e)}", "insights": []}

@router.post("/clean/{collection_name}")
async def clean_collection(
    collection_name: str,
    older_than_days: Optional[int] = None,
    min_score: Optional[float] = None
):
    """Clean up a collection based on age or quality criteria"""
    try:
        removed_count = vector_store.clean_collection(
            collection_name=collection_name,
            older_than_days=older_than_days,
            min_score=min_score
        )
        return {"message": f"Removed {removed_count} items from {collection_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/export/{collection_name}")
async def export_collection(collection_name: str):
    """Export a collection's data"""
    try:
        data = vector_store.export_collection(collection_name)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/import/{collection_name}")
async def import_collection(collection_name: str, data: Dict[str, Any]):
    """Import data into a collection"""
    try:
        vector_store.import_collection(collection_name, data)
        return {"message": f"Successfully imported data into {collection_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
