import pytest
import os
import shutil
from learning.collector import ExperienceCollector
from pytest_asyncio import fixture as async_fixture

class TestExperienceCollector:
    @async_fixture(scope="function")
    async def collector(self, request):
        """Create and initialize a test ExperienceCollector instance."""
        collector = ExperienceCollector(persist_directory=None)  # Use in-memory client
        await collector.initialize()
        return collector

    @pytest.mark.asyncio
    async def test_store_and_query_code_snippet(self, collector):
        # Test data
        code_content = """
        def hello_world():
            print("Hello, World!")
        """
        metadata = {
            "language": "python",
            "type": "function",
            "tags": ["greeting", "basic"]
        }
        
        # Store the experience
        id = await collector.store_experience(
            collection_name="code_snippets",
            content=code_content,
            metadata=metadata
        )
        
        assert id is not None
        
        # Query for similar experiences
        results = await collector.query_similar_experiences(
            collection_name="code_snippets",
            query="print hello world function"
        )
        
        assert len(results) > 0
        assert results[0]["content"] == code_content
        assert results[0]["metadata"]["language"] == "python"

    @pytest.mark.asyncio
    async def test_collection_stats(self, collector):
        # Store some test data
        await collector.store_experience(
            collection_name="metrics",
            content="Test metric",
            metadata={"type": "performance"}
        )
        
        # Get collection stats
        stats = await collector.get_collection_stats("metrics")
        
        assert stats["name"] == "metrics"
        assert stats["count"] > 0
        assert len(stats["sample"]) > 0

    @pytest.mark.asyncio
    async def test_delete_experience(self, collector):
        # Store and then delete an experience
        id = await collector.store_experience(
            collection_name="conversations",
            content="Test conversation",
            metadata={"type": "chat"}
        )
        
        # Delete the experience
        await collector.delete_experience("conversations", id)
        
        # Verify deletion
        stats = await collector.get_collection_stats("conversations")
        assert stats["count"] == 0
