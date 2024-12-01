"""
Compatibility layer for ensuring transparent operation with Cline and other Ollama clients.
This module handles the processing of requests and responses to maintain exact Ollama API format
while allowing optional agent enhancement.
"""

from fastapi import Request, Response
from typing import Optional, Dict, Any, Union
import json
from pydantic import BaseModel


class AgentHeaders:
    """Constants for agent-specific headers"""
    ENABLE = "X-Agent-Enable"
    MODE = "X-Agent-Mode"
    FEATURES = "X-Agent-Features"


class AgentMode:
    """Constants for agent operation modes"""
    PASSIVE = "passive"
    ACTIVE = "active"


class CompatibilityLayer:
    """
    Handles request and response processing to maintain compatibility with Ollama API
    while allowing optional agent enhancement.
    """

    @staticmethod
    async def should_activate_agent(request: Request) -> bool:
        """
        Determine if agent enhancement should be activated based on request headers.
        """
        agent_enabled = request.headers.get(AgentHeaders.ENABLE, "").lower() == "true"
        return agent_enabled

    @staticmethod
    async def get_agent_mode(request: Request) -> str:
        """
        Get the agent operation mode from request headers.
        Defaults to passive mode.
        """
        return request.headers.get(AgentHeaders.MODE, AgentMode.PASSIVE).lower()

    @staticmethod
    async def get_enabled_features(request: Request) -> list:
        """
        Get list of enabled agent features from request headers.
        """
        features_header = request.headers.get(AgentHeaders.FEATURES, "")
        if not features_header:
            return []
        return [f.strip() for f in features_header.split(",")]

    @staticmethod
    async def extract_body(request: Request) -> Dict[str, Any]:
        """
        Safely extract and parse request body.
        """
        body = await request.body()
        if not body:
            return {}
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {}

    async def process_request(self, request: Request) -> tuple[Request, Dict[str, Any]]:
        """
        Process incoming request, preserving original properties while extracting
        agent-specific information.
        
        Returns:
            Tuple of (original request, agent context dict)
        """
        agent_context = {
            "enabled": await self.should_activate_agent(request),
            "mode": await self.get_agent_mode(request),
            "features": await self.get_enabled_features(request),
            "original_body": await self.extract_body(request)
        }
        
        return request, agent_context

    async def process_streaming_response(
        self, 
        response_stream: Any,
        agent_context: Dict[str, Any]
    ) -> Any:
        """
        Process streaming response, ensuring compatibility with Ollama API format.
        Strips any agent-specific metadata from stream.
        """
        async for chunk in response_stream:
            # If agent is not enabled, yield original chunk unchanged
            if not agent_context["enabled"]:
                yield chunk
                continue

            # For enabled agent, process chunk while maintaining exact Ollama format
            try:
                if isinstance(chunk, bytes):
                    data = json.loads(chunk.decode())
                else:
                    data = chunk

                # Strip any agent-specific fields before yielding
                if isinstance(data, dict):
                    # Remove any agent-specific fields we might have added
                    data.pop("agent_metadata", None)
                    data.pop("agent_context", None)
                    
                    # Convert back to bytes if original was bytes
                    if isinstance(chunk, bytes):
                        yield json.dumps(data).encode()
                    else:
                        yield data
                else:
                    yield chunk
            except Exception:
                # On any error, yield original chunk unchanged
                yield chunk

    async def process_response(
        self, 
        response: Response,
        agent_context: Dict[str, Any]
    ) -> Response:
        """
        Process non-streaming response, ensuring compatibility with Ollama API format.
        Strips any agent-specific metadata from response.
        """
        if not agent_context["enabled"]:
            return response

        try:
            # For JSON responses, strip any agent-specific fields
            if response.headers.get("content-type") == "application/json":
                content = response.body
                if isinstance(content, bytes):
                    data = json.loads(content.decode())
                else:
                    data = content

                if isinstance(data, dict):
                    # Remove any agent-specific fields
                    data.pop("agent_metadata", None)
                    data.pop("agent_context", None)
                    
                    # Update response with cleaned data
                    response.body = json.dumps(data).encode()

        except Exception:
            # On any error, return original response unchanged
            pass

        return response
