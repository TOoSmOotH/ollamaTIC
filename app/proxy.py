from fastapi import Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from httpx import AsyncClient, HTTPError, ConnectError
import json
from typing import Dict, Any, Optional, AsyncGenerator
import time
from app.metrics import MetricsCollector
from app.config import get_settings
from app.agent import OllamaAgent

settings = get_settings()

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
            
            # Process request through agent
            body, context = await self.agent.process_request(request)
            
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
                            context
                        ),
                        media_type="text/event-stream"
                    )
                else:
                    # For non-streaming responses, just return the JSON response
                    json_response = response.json()
                    # Process through agent if it's a completion response
                    if isinstance(json_response, dict) and "response" in json_response:
                        json_response = await self.agent.process_single_response(json_response, context)
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
            async for chunk in response.aiter_bytes():
                yield chunk
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
