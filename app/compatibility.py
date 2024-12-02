from fastapi import Request, Response
from typing import Optional, Dict, Any, Union
import json
from pydantic import BaseModel
from app.config import get_settings
from app.prompt_template import PromptTemplate

settings = get_settings()

class AgentMode:
    """Constants for agent operation modes"""
    PASSIVE = "passive"
    ACTIVE = "active"

class CompatibilityLayer:
    """
    Handles request and response processing to maintain compatibility with Ollama API
    while allowing optional agent enhancement through different paths.
    """

    def __init__(self):
        self.settings = get_settings()
        # Load model-specific configurations
        self.model_configs = self.settings.model_configs or {}
        self.prompt_templates = {}

    @staticmethod
    def is_agent_path(path: str) -> bool:
        """
        Determine if the request path is an agent-enabled path.
        Agent paths start with /agent/
        """
        return path.startswith("/agent/")

    def get_base_path(self, path: str) -> str:
        """
        Get the base API path from either standard or agent path.
        /agent/chat -> /api/chat
        /api/chat -> /api/chat
        """
        if self.is_agent_path(path):
            return path.replace("/agent/", "/api/", 1)
        return path

    async def should_activate_agent(self, request: Request, body: Dict[str, Any]) -> bool:
        """
        Determine if agent enhancement should be activated based on:
        1. Path (/agent/ prefix)
        2. Model-specific configuration
        3. Client identifier (if available)
        """
        # Check path-based activation
        if self.is_agent_path(request.url.path):
            return True

        # Check model-specific configuration
        model_name = body.get("model", "")
        if model_name in self.model_configs:
            return self.model_configs[model_name].get("agent_enabled", False)

        return False

    async def get_agent_mode(self, request: Request, body: Dict[str, Any]) -> str:
        """
        Get the agent operation mode based on configuration.
        Defaults to passive mode.
        """
        model_name = body.get("model", "")
        if model_name in self.model_configs:
            return self.model_configs[model_name].get("agent_mode", AgentMode.PASSIVE)
        return AgentMode.PASSIVE

    async def get_enabled_features(self, request: Request, body: Dict[str, Any]) -> list:
        """
        Get list of enabled agent features from configuration.
        """
        model_name = body.get("model", "")
        if model_name in self.model_configs:
            return self.model_configs[model_name].get("enabled_features", [])
        return []

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
        body = await self.extract_body(request)
        
        agent_context = {
            "enabled": await self.should_activate_agent(request, body),
            "mode": await self.get_agent_mode(request, body),
            "features": await self.get_enabled_features(request, body),
            "original_body": body,
            "base_path": self.get_base_path(request.url.path)
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

    async def create_prompt_template(self, template: str, variables: List[str], model_id: str, language: Optional[str] = None, task_type: Optional[str] = None, priority: int = 1) -> PromptTemplate:
        """
        Create a new prompt template.
        """
        prompt_template = PromptTemplate(template=template, variables=variables, model_id=model_id, language=language, task_type=task_type, priority=priority)
        self.prompt_templates[prompt_template.template] = prompt_template
        return prompt_template

    async def get_prompt_template(self, template: str) -> Optional[PromptTemplate]:
        """
        Retrieve a prompt template by its template string.
        """
        return self.prompt_templates.get(template)

    async def list_prompt_templates(self) -> List[PromptTemplate]:
        """
        List all registered prompt templates.
        """
        return list(self.prompt_templates.values())
