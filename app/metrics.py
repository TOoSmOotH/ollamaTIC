from prometheus_client import Counter, Histogram, Gauge, REGISTRY
import time
from collections import deque
from typing import Dict, List
import threading
from app.storage import Storage

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
                cls._instance.request_history = deque(maxlen=100)  # Keep last 100 requests in memory
                cls._instance.storage = Storage()  # Initialize storage
            return cls._instance

    def record_request(self, endpoint: str, model: str, duration: float):
        """
        Record total request duration including network time
        """
        request_count.labels(endpoint=endpoint, model=model).inc()
        request_duration.labels(endpoint=endpoint, model=model).observe(duration)
        
        # Create request data
        request_data = {
            "request_id": int(time.time() * 1000),
            "model": model,
            "endpoint": endpoint,
            "total_duration": duration,
            "timestamp": int(time.time())
        }
        
        # Add to in-memory history
        self.request_history.appendleft(request_data)
        
        # Persist to database
        self.storage.save_request_metrics(request_data)

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
            last_request = self.request_history[0]
            last_request.update({
                "tokens_used": input_count + output_count,
                "context_size": input_count,
                "generation_duration": generation_duration
            })
            # Update the persisted metrics
            self.storage.save_request_metrics(last_request)

    def get_request_history(self, limit: int = 100) -> List[Dict]:
        """Get the request history from storage"""
        return self.storage.get_request_history(limit)

    def get_average_stats(self, window_hours: int = 24) -> Dict:
        """Get average statistics from storage"""
        return self.storage.get_average_stats(window_hours)

    def get_model_stats(self, window_hours: int = 24) -> Dict[str, Dict[str, float]]:
        """Get model-specific statistics from storage"""
        return self.storage.get_model_stats(window_hours)

    def get_cost_summary(self, window_hours: int = 24) -> Dict[str, float]:
        """Get cost summary and potential savings"""
        return self.storage.get_cost_summary(window_hours)

    def format_cost_summary(self, window_hours: int = 24) -> str:
        """Get a formatted string of the cost summary"""
        summary = self.get_cost_summary(window_hours)
        
        return f"""Cost Analysis (Last {summary['time_window_hours']} hours)
        
Total Usage:
- Input Tokens:  {summary['total_input_tokens']:,}
- Output Tokens: {summary['total_output_tokens']:,}

Estimated Costs:
- Claude Cost:   ${summary['claude_cost']:.2f}
- GPT-4 Cost:    ${summary['gpt4_cost']:.2f}
- Savings:       ${summary['potential_savings']:.2f} ({summary['savings_percentage']:.1f}%)
"""
