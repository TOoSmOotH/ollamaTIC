from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union

class ModelOptions(BaseModel):
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    repeat_penalty: Optional[float] = None
    seed: Optional[int] = None
    stop: Optional[Union[str, List[str]]] = None
    num_predict: Optional[int] = None
    system: Optional[str] = None

class GenerateRequest(BaseModel):
    model: str
    prompt: str
    system: Optional[str] = None
    template: Optional[str] = None
    context: Optional[List[int]] = None
    stream: bool = True
    raw: bool = False
    format: Optional[str] = None
    options: Optional[ModelOptions] = None
    keep_alive: Optional[str] = "5m"

class ChatMessage(BaseModel):
    role: str
    content: str
    images: Optional[List[str]] = None

class ChatRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: bool = True
    options: Optional[ModelOptions] = None
    keep_alive: Optional[str] = "5m"

class GenerateResponse(BaseModel):
    model: str
    created_at: str
    response: str
    done: bool
    context: Optional[List[int]] = None
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    prompt_eval_duration: Optional[int] = None
    eval_count: Optional[int] = None
    eval_duration: Optional[int] = None
    done_reason: Optional[str] = None

class TokenMetrics(BaseModel):
    input_tokens: int = Field(..., description="Number of tokens in the input prompt")
    output_tokens: int = Field(..., description="Number of tokens generated in the response")
    tokens_per_second: float = Field(..., description="Generation speed in tokens per second")
    total_duration: float = Field(..., description="Total request duration in seconds")
    prompt_eval_duration: Optional[float] = Field(None, description="Time spent evaluating the prompt in seconds")
    eval_duration: Optional[float] = Field(None, description="Time spent generating the response in seconds")
