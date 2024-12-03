from fastapi import Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from httpx import AsyncClient, HTTPError, ConnectError
import json
from typing import Dict, Any, Optional, AsyncGenerator
import time
from app.metrics import MetricsCollector
from app.config import get_settings
from app.agent import OllamaAgent
import logging

settings = get_settings()
logger = logging.getLogger(__name__)

class OllamaProxy:
    def __init__(self):
        self.base_url = settings.ollama_server
        self.client = AsyncClient(base_url=self.base_url, timeout=300.0)
        self.metrics = MetricsCollector()
        self.agent = OllamaAgent()

    async def forward_request(
        self,
        endpoint: str,
        request: Optional[Request],
        context: Optional[Dict[str, Any]] = None
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
            
            # Process request through agent with context
            body, agent_context = await self.agent.process_request(request, context)
            
            # Ensure model is set for POST requests
            if method == "post" and 'model' not in body:
                body['model'] = settings.default_model

            # Check if streaming is requested (only for POST requests)
            stream = body.get('stream', True) if method == "post" else False

            # Forward the request
            try:
                if method == "get":
                    response = await self.client.get(endpoint)
                else:
                    start_time = time.time()
                    response = await self.client.post(endpoint, json=body, timeout=300.0)
                    end_time = time.time()

                    # Update metrics
                    if response.status_code == 200:
                        self.metrics.record_request(
                            endpoint=endpoint,
                            model=body.get('model', 'unknown'),
                            duration=end_time - start_time
                        )

                response.raise_for_status()

                # Handle streaming response
                if stream and response.headers.get("transfer-encoding") == "chunked":
                    return StreamingResponse(
                        self.agent.process_response(
                            self._stream_response(response),
                            agent_context
                        ),
                        media_type="text/event-stream"
                    )
                else:
                    # For non-streaming responses, just return the JSON response
                    json_response = response.json()
                    # Process through agent if it's a completion response
                    if isinstance(json_response, dict) and "response" in json_response:
                        json_response = await self.agent.process_single_response(json_response, agent_context)
                    return JSONResponse(content=json_response)

            except HTTPError as e:
                raise HTTPException(
                    status_code=e.response.status_code if e.response else 500,
                    detail=str(e)
                )

        except ConnectError:
            raise HTTPException(
                status_code=503,
                detail=f"Could not connect to Ollama server at {self.base_url}"
            )

    async def _stream_response(self, response) -> AsyncGenerator[bytes, None]:
        """Stream the response from Ollama server"""
        try:
            buffer = ""
            async for chunk in response.aiter_bytes():
                chunk_str = chunk.decode('utf-8')
                buffer += chunk_str
                logger.debug(f"Received raw chunk: {chunk_str}")
                
                try:
                    # Try to parse complete JSON objects from the buffer
                    while True:
                        try:
                            # Find the end of the current JSON object
                            json_end = buffer.index("}\n") + 1
                            json_str = buffer[:json_end]
                            
                            # Parse and validate JSON
                            json_obj = json.loads(json_str)
                            logger.debug(f"Parsed JSON object: {json_obj}")
                            
                            # For final messages with empty content, preserve the metadata
                            if 'choices' in json_obj and json_obj['choices']:
                                choice = json_obj['choices'][0]
                                if choice.get('finish_reason') == 'stop' and 'delta' in choice:
                                    # Keep the metadata but ensure there's a content field
                                    if 'content' not in choice['delta']:
                                        logger.debug("Adding empty content to final delta")
                                        choice['delta']['content'] = ''
                                    
                            # Yield the valid JSON object
                            logger.debug(f"Yielding JSON: {json_str}")
                            yield json_str.encode('utf-8')
                            
                            # Remove processed JSON from buffer
                            buffer = buffer[json_end:]
                        except ValueError:
                            # No complete JSON object found
                            break
                except Exception as parse_error:
                    logger.error(f"Error parsing JSON: {parse_error}")
                    logger.debug(f"Buffer content: {buffer}")
                    
        except Exception as e:
            logger.error(f"Stream error: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
