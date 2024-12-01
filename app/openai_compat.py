from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
import time
import json

class OpenAIMessage(BaseModel):
    role: str
    content: Union[str, List[Dict[str, Any]]]
    name: Optional[str] = None

class OpenAIChatRequest(BaseModel):
    model: str
    messages: List[OpenAIMessage]
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    stream: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = 0
    frequency_penalty: Optional[float] = 0
    user: Optional[str] = None
    response_format: Optional[Dict[str, str]] = None
    seed: Optional[int] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None

class OpenAIUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

class OpenAIChoice(BaseModel):
    index: int
    message: OpenAIMessage
    finish_reason: Optional[str] = None

class OpenAIChatResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{int(time.time()*1000)}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[OpenAIChoice]
    usage: OpenAIUsage

class OpenAIStreamChoice(BaseModel):
    index: int
    delta: Dict[str, Any]
    finish_reason: Optional[str] = None

class OpenAIChatStreamResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{int(time.time()*1000)}")
    object: str = "chat.completion.chunk"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    system_fingerprint: str = "fp_44709d6fcb"  # Example fingerprint
    choices: List[OpenAIStreamChoice]

def convert_to_ollama_request(openai_request: OpenAIChatRequest) -> Dict[str, Any]:
    """Convert OpenAI chat request to Ollama format"""
    messages = []
    for msg in openai_request.messages:
        content = msg.content
        if isinstance(content, list):
            # Convert content array to string if it's a list
            content = " ".join(item.get("text", "") for item in content if item.get("type") == "text")
        messages.append({
            "role": msg.role,
            "content": content
        })

    return {
        "model": openai_request.model,
        "messages": messages,
        "stream": openai_request.stream,
        "options": {
            "temperature": openai_request.temperature,
            "top_p": openai_request.top_p,
            "stop": openai_request.stop if isinstance(openai_request.stop, list) else [openai_request.stop] if openai_request.stop else None,
            "num_predict": openai_request.max_tokens
        }
    }

def convert_from_ollama_response(
    ollama_response: Dict[str, Any],
    request: OpenAIChatRequest
) -> OpenAIChatResponse:
    """Convert Ollama response to OpenAI format"""
    return OpenAIChatResponse(
        model=request.model,
        choices=[
            OpenAIChoice(
                index=0,
                message=OpenAIMessage(
                    role="assistant",
                    content=ollama_response.get("response", "")
                ),
                finish_reason=ollama_response.get("done_reason", "stop")
            )
        ],
        usage=OpenAIUsage(
            prompt_tokens=ollama_response.get("prompt_eval_count", 0),
            completion_tokens=ollama_response.get("eval_count", 0),
            total_tokens=ollama_response.get("prompt_eval_count", 0) + 
                        ollama_response.get("eval_count", 0)
        )
    )

async def convert_from_ollama_stream(response_stream, request: OpenAIChatRequest):
    """This function is no longer used - streaming is handled directly in main.py"""
    pass
