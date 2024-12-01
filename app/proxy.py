from fastapi import Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from httpx import AsyncClient, HTTPError, ConnectError
import json
from typing import Dict, Any, Optional, AsyncGenerator
import time
from app.metrics import MetricsCollector
from app.config import get_settings

settings = get_settings()

class OllamaProxy:
    def __init__(self):
        self.base_url = settings.ollama_server
        self.client = AsyncClient(base_url=self.base_url, timeout=300.0)
        self.metrics = MetricsCollector()

    async def forward_request(
        self,
        endpoint: str,
        request: Optional[Request],
    ) -> Any:
        """
        Forward a request to the Ollama server and collect metrics.
        """
        try:
            # Handle GET requests or requests without body
            if request is None:
                response = await self.client.get(endpoint)
                response.raise_for_status()
                return JSONResponse(content=response.json())

            # Get the request method
            method = request.method.lower()
            
            # Get the request body for POST requests
            body = await request.body()
            json_body = json.loads(body) if body else {}
            
            # Ensure model is set for POST requests
            if method == "post" and 'model' not in json_body:
                json_body['model'] = settings.default_model

            # Check if streaming is requested (only for POST requests)
            stream = json_body.get('stream', True) if method == "post" else False

            # Forward the request
            try:
                if method == "get":
                    response = await self.client.get(
                        endpoint,
                        headers={k: v for k, v in request.headers.items() if k.lower() not in ['host', 'content-length']},
                    )
                else:
                    response = await self.client.post(
                        endpoint,
                        json=json_body,
                        headers={k: v for k, v in request.headers.items() if k.lower() not in ['host', 'content-length']},
                    )
                response.raise_for_status()
            except ConnectError as e:
                raise HTTPException(
                    status_code=503,
                    detail=f"Failed to connect to Ollama server at {self.base_url}. Is it running?"
                ) from e
            except HTTPError as e:
                if hasattr(e, 'response'):
                    raise HTTPException(
                        status_code=e.response.status_code,
                        detail=f"{e.response.status_code}: {e.response.text}"
                    ) from e
                else:
                    raise HTTPException(
                        status_code=500,
                        detail=str(e)
                    ) from e

            if stream:
                return StreamingResponse(
                    self._handle_streaming_response(response, json_body['model'], endpoint),
                    media_type="text/event-stream"
                )
            else:
                return await self._handle_single_response(response, json_body.get('model', 'unknown'), endpoint)

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def _handle_streaming_response(
        self, 
        response, 
        model: str, 
        endpoint: str
    ) -> AsyncGenerator[str, None]:
        """
        Handle streaming response from Ollama and collect metrics.
        """
        try:
            async for line in response.aiter_lines():
                if not line:
                    continue
                    
                try:
                    # Ensure line is a string
                    if isinstance(line, bytes):
                        line = line.decode()
                    
                    data = json.loads(line)
                    
                    # Collect metrics if the response is done
                    if data.get('done', False):
                        # Record total request duration
                        total_duration = data.get('total_duration', 0) / 1e9  # Convert nanoseconds to seconds
                        self.metrics.record_request(endpoint, model, total_duration)
                        
                        if 'eval_count' in data:
                            # Record token metrics with generation duration
                            self.metrics.record_tokens(
                                model=model,
                                input_count=data.get('prompt_eval_count', 0),
                                output_count=data.get('eval_count', 0),
                                generation_duration=data.get('eval_duration', 0) / 1e9  # Convert nanoseconds to seconds
                            )
                    
                    # For OpenAI compatibility endpoint, convert the response
                    if endpoint == "/v1/chat/completions":
                        response_id = f"chatcmpl-{int(time.time()*1000)}"
                        
                        if data.get('done', False):
                            # Final message
                            yield json.dumps({
                                "id": response_id,
                                "object": "chat.completion.chunk",
                                "created": int(time.time()),
                                "model": model,
                                "choices": [{
                                    "index": 0,
                                    "delta": {},
                                    "finish_reason": "stop"
                                }],
                                "type": "text"
                            }) + "\n"
                        else:
                            # Content message
                            if "message" in data and data["message"].get("content"):
                                yield json.dumps({
                                    "id": response_id,
                                    "object": "chat.completion.chunk",
                                    "created": int(time.time()),
                                    "model": model,
                                    "choices": [{
                                        "index": 0,
                                        "delta": {
                                            "content": data["message"]["content"]
                                        },
                                        "finish_reason": None
                                    }],
                                    "type": "text"
                                }) + "\n"
                    else:
                        # For non-OpenAI endpoints, return the original response
                        yield (line if line.endswith('\n') else line + '\n')
                
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON: {e}")
                    print(f"Line content: {line}")
                    continue
                except Exception as e:
                    print(f"Error processing line: {str(e)}")
                    print(f"Line type: {type(line)}")
                    print(f"Line content: {line}")
                    continue
                    
        except Exception as e:
            print(f"Error in streaming response: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def _handle_single_response(
        self, 
        response, 
        model: str, 
        endpoint: str
    ) -> JSONResponse:
        """
        Handle single response from Ollama and collect metrics.
        """
        data = response.json()
        
        # Record total request duration
        total_duration = data.get('total_duration', 0) / 1e9  # Convert nanoseconds to seconds
        self.metrics.record_request(endpoint, model, total_duration)
        
        if 'eval_count' in data:
            # Record token metrics with generation duration
            self.metrics.record_tokens(
                model=model,
                input_count=data.get('prompt_eval_count', 0),
                output_count=data.get('eval_count', 0),
                generation_duration=data.get('eval_duration', 0) / 1e9  # Convert nanoseconds to seconds
            )
        
        return JSONResponse(content=data)
