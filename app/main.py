from fastapi import FastAPI, HTTPException, Request, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse
from pydantic import ValidationError
import httpx
import json
import os
from dotenv import load_dotenv
from app.proxy import OllamaProxy
from app.openai_compat import (
    OpenAIChatRequest,
    OpenAIChatResponse,
    OpenAIChatStreamResponse,
    convert_to_ollama_request,
    convert_from_ollama_response,
    convert_from_ollama_stream
)
from prometheus_client import make_asgi_app
import time
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.metrics import MetricsCollector

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Ollama Proxy",
    description="Proxy server for monitoring Ollama model usage",
    version="0.1.0"
)

# Create API router
api_router = APIRouter(prefix="/api")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize proxy and metrics collector
proxy = OllamaProxy()
metrics_collector = MetricsCollector()

# Health check endpoint
@app.get("/health")
async def health_check():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{proxy.base_url}/api/tags")
            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "ollama_server": proxy.base_url,
                    "ollama_status": "connected"
                }
    except Exception as e:
        return {
            "status": "degraded",
            "ollama_server": proxy.base_url,
            "ollama_status": "disconnected",
            "error": str(e)
        }

# Ollama API endpoints
@api_router.get("/tags")
async def list_models():
    """List all available models"""
    return await proxy.forward_request("/api/tags", None)

@api_router.post("/generate")
async def generate(request: Request):
    """Forward generate requests to Ollama server"""
    return await proxy.forward_request("/api/generate", request)

@api_router.post("/chat")
async def chat(request: Request):
    """Forward chat requests to Ollama server"""
    return await proxy.forward_request("/api/chat", request)

# OpenAI-compatible endpoints
@app.post("/v1/chat/completions")
async def openai_chat_completions(request: Request):
    """OpenAI-compatible chat completions endpoint"""
    try:
        # Get raw JSON data from request
        raw_data = await request.json()
        
        # Parse into OpenAIChatRequest model
        chat_request = OpenAIChatRequest(**raw_data)
        
        # Log incoming request
        print(f"OpenAI request: {chat_request.model_dump_json()}")
        
        # Convert request to Ollama format
        ollama_request = convert_to_ollama_request(chat_request)
        print(f"Ollama request: {json.dumps(ollama_request)}")
        
        # Create a mock Request object for the proxy
        class MockRequest:
            def __init__(self, json_data):
                self._json = json_data
                self.method = "POST"
                self.headers = {}

            async def body(self):
                return json.dumps(self._json).encode()

            async def json(self):
                return self._json

        mock_request = MockRequest(ollama_request)
        
        # Forward the request to Ollama
        response = await proxy.forward_request("/api/chat", mock_request)
        
        if chat_request.stream:
            async def stream_response():
                try:
                    # Send initial role message
                    ts = int(time.time() * 1000)
                    message_id = f'chatcmpl-{ts}'

                    # Send api_req_started message with token counts
                    api_req_msg = {
                        'id': message_id,
                        'object': 'chat.completion.chunk',
                        'created': int(time.time()),
                        'model': chat_request.model,
                        'choices': [{
                            'index': 0,
                            'delta': {
                                'role': 'assistant'
                            }
                        }]
                    }
                    yield f"data: {json.dumps(api_req_msg)}\n\n"
                                        
                    # Process response stream
                    total_completion_tokens = 0
                    async for chunk in response.body_iterator:
                        if chunk:
                            try:
                                # Check if chunk is already a string
                                if isinstance(chunk, str):
                                    chunk_str = chunk
                                else:
                                    chunk_str = chunk.decode()
                                
                                data = json.loads(chunk_str)
                                print(f"DEBUG - Received chunk data: {data}")  # Debug print
                                
                                # For OpenAI compatibility endpoint, convert the response
                                if data.get('done', False):
                                    # Get token counts
                                    prompt_tokens = data.get('prompt_eval_count', 0)
                                    completion_tokens = data.get('eval_count', 0)
                                    print(f"DEBUG - Token counts - Prompt: {prompt_tokens}, Completion: {completion_tokens}")  # Debug print

                                    # Record total request duration
                                    total_duration = data.get('total_duration', 0) / 1e9  # Convert nanoseconds to seconds
                                    metrics_collector.record_request("/v1/chat/completions", chat_request.model, total_duration)
                                    
                                    # Record token metrics with generation duration
                                    metrics_collector.record_tokens(
                                        model=chat_request.model,
                                        input_count=prompt_tokens,
                                        output_count=completion_tokens,
                                        generation_duration=data.get('eval_duration', 0) / 1e9  # Convert nanoseconds to seconds
                                    )

                                    # Send final completion message
                                    final_msg = {
                                        'id': message_id,
                                        'object': 'chat.completion.chunk',
                                        'created': int(time.time()),
                                        'model': chat_request.model,
                                        'choices': [{
                                            'index': 0,
                                            'delta': {},
                                            'finish_reason': 'stop'
                                        }],
                                        'usage': {
                                            'prompt_tokens': int(prompt_tokens),
                                            'completion_tokens': int(completion_tokens),
                                            'total_tokens': int(prompt_tokens) + int(completion_tokens)
                                        }
                                    }
                                    print(f"DEBUG - Sending final_msg: {final_msg}")  # Debug print
                                    yield f"data: {json.dumps(final_msg)}\n\n"
                                    yield "data: [DONE]\n\n"
                                else:
                                    # Content message
                                    if "message" in data and data["message"].get("content"):
                                        content = data["message"]["content"]
                                        if content:
                                            content_msg = {
                                                'id': message_id,
                                                'object': 'chat.completion.chunk',
                                                'created': int(time.time()),
                                                'model': chat_request.model,
                                                'choices': [{
                                                    'index': 0,
                                                    'delta': {
                                                        'content': content
                                                    }
                                                }]
                                            }
                                            print(f"DEBUG - Sending content_msg: {content_msg}")  # Debug print
                                            yield f"data: {json.dumps(content_msg)}\n\n"
                            except json.JSONDecodeError as e:
                                print(f"Failed to decode JSON: {chunk}, Error: {e}")
                            except Exception as e:
                                print(f"Error processing chunk: {chunk}, Error: {e}")
                except Exception as e:
                    print(f"Error in stream_response: {str(e)}")
                    raise HTTPException(status_code=500, detail=str(e))
            
            return StreamingResponse(
                stream_response(),
                media_type="text/event-stream"
            )
        else:
            # For non-streaming responses, we need to get the full response
            ollama_response = await response.json()
            print(f"Ollama response: {json.dumps(ollama_response)}")

            # Record total request duration
            total_duration = ollama_response.get('total_duration', 0) / 1e9  # Convert nanoseconds to seconds
            metrics_collector.record_request("/v1/chat/completions", chat_request.model, total_duration)
            
            # Record token metrics with generation duration
            metrics_collector.record_tokens(
                model=chat_request.model,
                input_count=ollama_response.get('prompt_eval_count', 0),
                output_count=ollama_response.get('eval_count', 0),
                generation_duration=ollama_response.get('eval_duration', 0) / 1e9  # Convert nanoseconds to seconds
            )

            openai_response = convert_from_ollama_response(ollama_response, chat_request)
            return JSONResponse(content=openai_response.model_dump())
            
    except ValidationError as e:
        print(f"Validation error: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        print(f"Error in chat completions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Monitoring endpoints
@api_router.get("/request_history")
async def request_history():
    """Get request history"""
    return metrics_collector.get_request_history()

@api_router.get("/average_stats")
async def average_stats():
    """Get average tokens used and average time requests took"""
    return metrics_collector.get_average_stats()

# Include API router
app.include_router(api_router)

# Mount static files for the frontend AFTER all API routes
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
