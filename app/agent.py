"""
OllamaTIC Agent - Enhances Ollama responses with continuous learning capabilities.
The agent processes all requests, learning from interactions and improving responses over time.
"""

from typing import Dict, Any, AsyncGenerator, Optional
import json
from fastapi import Request
from pydantic import BaseModel
import logging
from datetime import datetime
from app.learning import LearningSystem

logger = logging.getLogger(__name__)

class Interaction(BaseModel):
    """Record of an interaction with the model"""
    timestamp: datetime
    model: str
    prompt: str
    response: str
    context: Dict[str, Any]
    success_indicators: Dict[str, float]

class OllamaAgent:
    """
    Agent that processes all Ollama interactions, learning and improving over time.
    """
    def __init__(self):
        self.interactions: list[Interaction] = []
        self.learning_system = LearningSystem()
        self.context_memory: Dict[str, Any] = {}

    async def process_request(self, request: Request) -> Dict[str, Any]:
        """
        Process and potentially enhance the incoming request based on learned patterns.
        """
        body = await self._get_request_body(request)
        model = body.get("model", "")
        prompt = body.get("prompt", "")

        # Get relevant context from memory
        context_key = f"{model}:{prompt[:50]}"
        context = self.context_memory.get(context_key, {})

        # Enhance the prompt using learned patterns
        enhanced_prompt = self.learning_system.enhance_prompt(prompt, model, context)
        if enhanced_prompt != prompt:
            body["prompt"] = enhanced_prompt
        
        # Store context for this interaction
        context = {
            "timestamp": datetime.utcnow(),
            "model": model,
            "original_prompt": prompt,
            "enhanced_prompt": enhanced_prompt,
        }

        return body, context

    async def process_response(
        self,
        response: AsyncGenerator[bytes, None],
        context: Dict[str, Any]
    ) -> AsyncGenerator[bytes, None]:
        """
        Process the response stream, learning from the interaction.
        """
        full_response = ""
        error_detected = False
        error_message = None
        
        async for chunk in response:
            try:
                if isinstance(chunk, bytes):
                    data = json.loads(chunk.decode())
                    if "response" in data:
                        full_response += data["response"]
                    # Check for error indicators
                    if "error" in data:
                        error_detected = True
                        error_message = data["error"]
                yield chunk
            except Exception as e:
                logger.error(f"Error processing response chunk: {e}")
                error_detected = True
                error_message = str(e)
                yield chunk

        # Learn from this interaction
        await self._learn_from_interaction(
            context["model"],
            context["original_prompt"],
            full_response,
            context,
            not error_detected,
            error_message
        )

    async def _get_request_body(self, request: Request) -> Dict[str, Any]:
        """Extract and parse request body."""
        body = await request.body()
        if not body:
            return {}
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {}

    async def _learn_from_interaction(
        self,
        model: str,
        prompt: str,
        response: str,
        context: Dict[str, Any],
        success: bool,
        error_message: Optional[str] = None
    ):
        """
        Learn from the interaction to improve future responses.
        """
        # Analyze the interaction
        learning_results = self.learning_system.analyze_interaction(
            prompt=prompt,
            response=response,
            model=model,
            context=context
        )
        
        # Create interaction record
        interaction = Interaction(
            timestamp=context["timestamp"],
            model=model,
            prompt=prompt,
            response=response,
            context=context,
            success_indicators={
                "completion": 1.0 if success else 0.0,
                "patterns_found": len(learning_results["patterns_found"]),
            }
        )
        
        # Store the interaction
        self.interactions.append(interaction)
        
        # Update success metrics for any code blocks
        for language in learning_results["languages"]:
            self.learning_system.update_success_metrics(
                language=language,
                code_block=response,
                success=success,
                error_message=error_message
            )
        
        # Update context memory
        context_key = f"{model}:{prompt[:50]}"
        self.context_memory[context_key] = {
            "last_used": datetime.utcnow(),
            "success_rate": interaction.success_indicators["completion"],
            "languages": learning_results["languages"],
            "patterns": learning_results["patterns_found"]
        }
