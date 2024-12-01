"""
Tests for the compatibility layer to ensure transparent operation with Cline and other Ollama clients.
"""

import pytest
from fastapi import Request, Response
from fastapi.testclient import TestClient
import json
from app.compatibility import CompatibilityLayer, AgentHeaders, AgentMode


@pytest.fixture
def compatibility_layer():
    return CompatibilityLayer()


@pytest.fixture
def mock_request_with_agent():
    """Create a mock request with agent headers enabled"""
    headers = {
        AgentHeaders.ENABLE: "true",
        AgentHeaders.MODE: AgentMode.ACTIVE,
        AgentHeaders.FEATURES: "feature1,feature2"
    }
    return Request({"type": "http", "headers": headers, "method": "POST"})


@pytest.fixture
def mock_request_without_agent():
    """Create a mock request without agent headers"""
    return Request({"type": "http", "headers": {}, "method": "POST"})


async def test_should_activate_agent(compatibility_layer, mock_request_with_agent, mock_request_without_agent):
    """Test agent activation detection"""
    assert await compatibility_layer.should_activate_agent(mock_request_with_agent) == True
    assert await compatibility_layer.should_activate_agent(mock_request_without_agent) == False


async def test_get_agent_mode(compatibility_layer, mock_request_with_agent, mock_request_without_agent):
    """Test agent mode detection"""
    assert await compatibility_layer.get_agent_mode(mock_request_with_agent) == AgentMode.ACTIVE
    assert await compatibility_layer.get_agent_mode(mock_request_without_agent) == AgentMode.PASSIVE


async def test_get_enabled_features(compatibility_layer, mock_request_with_agent, mock_request_without_agent):
    """Test feature list extraction"""
    features = await compatibility_layer.get_enabled_features(mock_request_with_agent)
    assert features == ["feature1", "feature2"]
    
    features = await compatibility_layer.get_enabled_features(mock_request_without_agent)
    assert features == []


async def test_process_request(compatibility_layer, mock_request_with_agent):
    """Test request processing"""
    request, agent_context = await compatibility_layer.process_request(mock_request_with_agent)
    
    assert agent_context["enabled"] == True
    assert agent_context["mode"] == AgentMode.ACTIVE
    assert agent_context["features"] == ["feature1", "feature2"]


async def test_process_streaming_response(compatibility_layer):
    """Test streaming response processing"""
    # Mock streaming response with agent metadata
    async def mock_stream():
        yield json.dumps({"response": "test", "agent_metadata": "should_be_removed"}).encode()
        yield json.dumps({"response": "test2"}).encode()

    agent_context = {"enabled": True}
    processed_stream = compatibility_layer.process_streaming_response(mock_stream(), agent_context)
    
    chunks = []
    async for chunk in processed_stream:
        chunks.append(json.loads(chunk.decode()))

    assert len(chunks) == 2
    assert "agent_metadata" not in chunks[0]
    assert chunks[0]["response"] == "test"
    assert chunks[1]["response"] == "test2"


async def test_process_response(compatibility_layer):
    """Test non-streaming response processing"""
    # Create a response with agent metadata
    response_data = {
        "response": "test",
        "agent_metadata": "should_be_removed",
        "agent_context": "should_be_removed"
    }
    response = Response(
        content=json.dumps(response_data).encode(),
        media_type="application/json"
    )

    agent_context = {"enabled": True}
    processed_response = await compatibility_layer.process_response(response, agent_context)
    
    processed_data = json.loads(processed_response.body.decode())
    assert "agent_metadata" not in processed_data
    assert "agent_context" not in processed_data
    assert processed_data["response"] == "test"
