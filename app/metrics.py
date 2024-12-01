from prometheus_client import Counter, Histogram, Gauge, REGISTRY
import time
from collections import deque
from typing import Dict, List
import threading

# Request metrics
request_count = Counter(
    'ollama_requests_total',
    'Total number of requests processed',
    ['endpoint', 'model']
)

request_duration = Histogram(
    'ollama_request_duration_seconds',
    'Total request duration in seconds (includes network time)',
    ['endpoint', 'model']
)

token_generation_duration = Histogram(
    'ollama_token_generation_seconds',
    'Token generation duration in seconds (actual model inference time)',
    ['model']
)

# Token metrics
input_tokens = Counter(
    'ollama_input_tokens_total',
    'Total number of input tokens processed',
    ['model']
)

output_tokens = Counter(
    'ollama_output_tokens_total',
    'Total number of output tokens generated',
    ['model']
)

tokens_per_second = Gauge(
    'ollama_tokens_per_second',
    'Tokens generated per second',
    ['model']
)

class MetricsCollector:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(MetricsCollector, cls).__new__(cls)
                cls._instance.request_history = deque(maxlen=100)  # Keep last 100 requests
            return cls._instance

    def record_request(self, endpoint: str, model: str, duration: float):
        """
        Record total request duration including network time
        """
        request_count.labels(endpoint=endpoint, model=model).inc()
        request_duration.labels(endpoint=endpoint, model=model).observe(duration)
        
        # Add to request history
        self.request_history.appendleft({
            "request_id": int(time.time() * 1000),
            "model": model,
            "endpoint": endpoint,
            "total_duration": duration,
            "timestamp": int(time.time())
        })

    def record_tokens(self, model: str, input_count: int, output_count: int, generation_duration: float):
        """
        Record token metrics and token generation duration (model inference time)
        """
        input_tokens.labels(model=model).inc(input_count)
        output_tokens.labels(model=model).inc(output_count)
        token_generation_duration.labels(model=model).observe(generation_duration)
        
        if generation_duration > 0:
            tokens_per_second.labels(model=model).set(output_count / generation_duration)
            
        # Update the last request with token information
        if self.request_history:
            self.request_history[0].update({
                "tokens_used": input_count + output_count,
                "context_size": input_count,
                "generation_duration": generation_duration
            })

    def get_request_history(self) -> List[Dict]:
        """Get the request history"""
        return list(self.request_history)

    def get_average_stats(self) -> Dict:
        """Get average statistics from request history"""
        stats = {
            "average_tokens_used": 0,
            "average_total_duration": 0,
            "average_generation_duration": 0
        }
        
        if not self.request_history:
            return stats
            
        history_list = list(self.request_history)
        total_requests = len(history_list)
        
        if total_requests == 0:
            return stats
            
        # Calculate averages from request history
        total_tokens = sum(req.get('tokens_used', 0) for req in history_list)
        total_duration = sum(req.get('total_duration', 0) for req in history_list)
        total_generation = sum(req.get('generation_duration', 0) for req in history_list)
        
        stats["average_tokens_used"] = total_tokens / total_requests
        stats["average_total_duration"] = total_duration / total_requests
        stats["average_generation_duration"] = total_generation / total_requests
            
        return stats
