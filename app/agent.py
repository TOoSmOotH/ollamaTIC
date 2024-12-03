from typing import Dict, Any, AsyncGenerator, Optional
import json
from fastapi import Request
from pydantic import BaseModel
import logging
from datetime import datetime
from app.learning import LearningSystem
from app.prompt_template import PromptTemplate
import re

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
        self.prompt_templates: Dict[str, PromptTemplate] = {}

    async def process_request(
        self,
        request: Request,
        conversation_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process and potentially enhance the incoming request based on learned patterns.
        """
        logger.info("Processing request through agent")
        body = await self._get_request_body(request)
        model = body.get("model", "")
        
        # Extract prompt based on request format
        if "messages" in body:
            # OpenAI format - combine messages into a prompt
            messages = body.get("messages", [])
            prompt = "\n".join(f"{msg.get('role')}: {msg.get('content')}" for msg in messages)
        else:
            # Ollama format
            prompt = body.get("prompt", "")

        logger.debug(f"Request body - Model: {model}")
        logger.debug(f"Prompt (first 100 chars): {prompt[:100]}...")

        # Get relevant context from memory or use provided conversation context
        if conversation_context:
            context = conversation_context
            context_key = f"{model}:{prompt[:50]}"
            self.context_memory[context_key] = context
        else:
            context_key = f"{model}:{prompt[:50]}"
            context = self.context_memory.get(context_key, {})

        # Enhance the prompt using learned patterns
        enhanced_prompt = self.learning_system.enhance_prompt(prompt, model, context)
        if enhanced_prompt != prompt:
            logger.info("Prompt was enhanced with learned patterns")
            if "messages" in body:
                # For OpenAI format, append the enhancements to the last user message
                messages = body["messages"]
                if messages and messages[-1]["role"] == "user":
                    messages[-1]["content"] = enhanced_prompt
            else:
                # For Ollama format
                body["prompt"] = enhanced_prompt
        
        # Update context with request details
        context.update({
            "timestamp": datetime.utcnow(),
            "model": model,
            "original_prompt": prompt,
            "enhanced_prompt": enhanced_prompt,
        })
        
        logger.debug(f"Created context: {context}")
        return body, context

    async def process_response(self, response_stream, context: Dict[str, Any]) -> AsyncGenerator[bytes, None]:
        """Process a streaming response from the LLM."""
        logger.info("Processing streaming response")
        accumulated_response = []
        full_response = ""
        chunk_count = 0
        last_response = None
        total_text_length = 0
        
        async for chunk in response_stream:
            chunk_count += 1
            if isinstance(chunk, bytes):
                chunk_str = chunk.decode('utf-8')
            else:
                chunk_str = chunk
                
            try:
                # Parse the JSON to validate it
                json_obj = json.loads(chunk_str)
                logger.debug(f"Processing chunk {chunk_count}: {json_obj}")
                
                # Handle OpenAI format
                if 'choices' in json_obj and json_obj['choices']:
                    choice = json_obj['choices'][0]
                    if 'delta' in choice:
                        if 'content' in choice['delta']:
                            response_text = choice['delta']['content']
                            logger.debug(f"OpenAI delta content: {response_text}")
                        else:
                            logger.debug(f"OpenAI delta without content: {choice['delta']}")
                            response_text = ''
                    else:
                        response_text = choice.get('text', '')
                        logger.debug(f"OpenAI text content: {response_text}")
                # Handle Ollama format
                elif 'message' in json_obj:
                    response_text = json_obj['message'].get('content', '')
                    logger.debug(f"Ollama message content: {response_text}")
                else:
                    # Legacy Ollama format
                    response_text = json_obj.get('response', '')
                    logger.debug(f"Ollama legacy response: {response_text}")
                
                # Store last non-empty response for final message handling
                if response_text:
                    last_response = response_text
                    total_text_length += len(response_text)
                    logger.debug(f"Updated total text length: {total_text_length}")
                    # Only accumulate non-empty responses
                    accumulated_response.append(response_text)
                
                # Forward the validated JSON chunk
                yield chunk_str.encode('utf-8')
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in chunk: {chunk_str}")
            except Exception as e:
                logger.error(f"Error processing chunk: {str(e)}")
        
        # Combine all response chunks
        full_response = "".join(accumulated_response)
        logger.info(f"Raw accumulated response length: {len(full_response)}")
        logger.info(f"Total text length from chunks: {total_text_length}")
        
        if not full_response and last_response:
            logger.info("Using last non-empty response as full response")
            full_response = last_response
            
        logger.info(f"Final response length: {len(full_response)}")
        
        # Only log if we actually have content
        if full_response:
            logger.debug(f"Final response (first 200 chars): {full_response[:200]}...")
        else:
            logger.warning("No response content accumulated from stream")
            logger.debug(f"Last response was: {last_response}")
            logger.debug(f"Number of accumulated chunks: {len(accumulated_response)}")
            logger.debug(f"Non-empty chunks: {[c for c in accumulated_response if c][:5]}")  # First 5 non-empty chunks
        
        # Learn from the complete interaction after streaming is done
        logger.info("Stream completed, learning from interaction")
        if context.get("original_prompt") and full_response:
            await self._learn_from_interaction(
                prompt=context["original_prompt"],
                response=full_response,
                model=context.get("model", "unknown"),
                context=context
            )

    async def process_single_response(self, response: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single non-streaming response."""
        prompt = context.get("original_prompt") or context.get("prompt")
        response_text = response.get("response")
        
        if prompt and response_text:
            await self._learn_from_interaction(
                prompt=prompt,
                response=response_text,
                model=context.get("model", "unknown"),
                context=context
            )
            
        return response

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
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """
        Learn from the interaction to improve future responses.
        """
        logger.info(f"Learning from interaction - Model: {model}")
        
        # Validate inputs
        if not isinstance(prompt, str) or not isinstance(response, str):
            logger.warning("Invalid prompt or response type")
            return
            
        logger.debug(f"Prompt: {prompt[:100]}...")
        logger.debug(f"Response: {response[:100]}...")
        
        # Extract language from context if available
        language = context.get('language', '')
        if not language:
            # Try to detect language from prompt/response
            code_pattern = re.compile(r'```(\w+)')
            lang_match = code_pattern.search(prompt) or code_pattern.search(response)
            if lang_match:
                language = lang_match.group(1)
        
        # Create interaction dictionary with all expected fields
        interaction = {
            "model": model,
            "prompt": prompt,
            "response": response,
            "context": context or {},
            "success": success,
            "error": error_message,
            "language": language,
            "code": "",  # Will be extracted by analyze_interaction
            "query": context.get('query', '')  # Original query if available
        }
        
        # Analyze the interaction
        learning_results = self.learning_system.analyze_interaction(interaction)
        
        if "error" in learning_results:
            logger.warning(f"Error analyzing interaction: {learning_results['error']}")
            return
            
        logger.info(f"Learning results - Languages: {learning_results.get('languages', [])}")
        logger.info(f"Patterns found: {len(learning_results.get('patterns_found', []))}")
        
        # Create interaction record
        interaction_record = Interaction(
            timestamp=context.get("timestamp", datetime.now()),
            model=model,
            prompt=prompt,
            response=response,
            context=context or {},
            success_indicators={
                "completion": 1.0 if success else 0.0,
                "patterns_found": len(learning_results.get("patterns_found", [])),
            }
        )
        
        # Store the interaction
        self.interactions.append(interaction_record)
        
        # Update success metrics for any code blocks
        for language in learning_results.get("languages", []):
            logger.info(f"Updating metrics for language: {language}")
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
            "success_rate": interaction_record.success_indicators["completion"],
            "languages": learning_results.get("languages", []),
            "patterns": learning_results.get("patterns_found", [])
        }
