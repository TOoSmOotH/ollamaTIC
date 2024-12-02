"""
Storage system for persisting learned patterns and interactions.
"""

import json
from typing import Dict, Any, Optional, List
from pathlib import Path
import pickle
from datetime import datetime
import logging
from app.learning import LanguagePatterns, CodeBlock
import sqlite3
from contextlib import contextmanager
import threading
import time

logger = logging.getLogger(__name__)

class Storage:
    """
    Handles persistence of learned patterns and interactions.
    Uses SQLite for structured data and pickle files for complex objects.
    """
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "learning.db"
        self.patterns_path = self.data_dir / "patterns.pkl"
        self._lock = threading.Lock()
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database schema."""
        with self._get_db() as (conn, cursor):
            # Create interactions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME,
                    model TEXT,
                    prompt TEXT,
                    response TEXT,
                    context TEXT,
                    success_indicators TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    language TEXT,
                    metric_type TEXT,
                    metric_key TEXT,
                    value REAL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(language, metric_type, metric_key)
                )
            """)

            # Create request_history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS request_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id INTEGER,
                    model TEXT,
                    endpoint TEXT,
                    total_duration REAL,
                    generation_duration REAL,
                    tokens_used INTEGER,
                    context_size INTEGER,
                    timestamp INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()

    @contextmanager
    def _get_db(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            yield conn, cursor
        finally:
            conn.close()

    def save_language_patterns(self, patterns: Dict[str, LanguagePatterns]):
        """Save language patterns to disk."""
        with self._lock:
            with open(self.patterns_path, 'wb') as f:
                pickle.dump(patterns, f)

    def load_language_patterns(self) -> Dict[str, LanguagePatterns]:
        """Load language patterns from disk."""
        if not self.patterns_path.exists():
            return {}
        
        with self._lock:
            try:
                with open(self.patterns_path, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                logger.error(f"Error loading patterns: {e}")
                return {}

    def save_interaction(self, interaction: Dict[str, Any]):
        """Save an interaction to the database."""
        with self._get_db() as (conn, cursor):
            cursor.execute("""
                INSERT INTO interactions 
                (timestamp, model, prompt, response, context, success_indicators)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                interaction["timestamp"].isoformat(),
                interaction["model"],
                interaction["prompt"],
                interaction["response"],
                json.dumps(interaction["context"]),
                json.dumps(interaction["success_indicators"])
            ))
            conn.commit()

    def update_metrics(self, language: str, metric_type: str, metrics: Dict[str, float]):
        """Update metrics in the database."""
        with self._get_db() as (conn, cursor):
            for key, value in metrics.items():
                cursor.execute("""
                    INSERT OR REPLACE INTO metrics 
                    (language, metric_type, metric_key, value, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (language, metric_type, key, value))
            conn.commit()

    def get_language_metrics(self, language: str) -> Dict[str, Dict[str, float]]:
        """Get all metrics for a language."""
        with self._get_db() as (conn, cursor):
            cursor.execute("""
                SELECT metric_type, metric_key, value
                FROM metrics
                WHERE language = ?
            """, (language,))
            
            metrics = {}
            for row in cursor.fetchall():
                metric_type, key, value = row
                if metric_type not in metrics:
                    metrics[metric_type] = {}
                metrics[metric_type][key] = value
            
            return metrics

    def get_recent_interactions(self, limit: int = 100) -> list:
        """Get recent interactions from the database."""
        with self._get_db() as (conn, cursor):
            cursor.execute("""
                SELECT timestamp, model, prompt, response, context, success_indicators
                FROM interactions
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            interactions = []
            for row in cursor.fetchall():
                timestamp, model, prompt, response, context, indicators = row
                interactions.append({
                    "timestamp": datetime.fromisoformat(timestamp),
                    "model": model,
                    "prompt": prompt,
                    "response": response,
                    "context": json.loads(context),
                    "success_indicators": json.loads(indicators)
                })
            
            return interactions

    def get_language_success_rate(self, language: str) -> float:
        """Get the overall success rate for a language."""
        with self._get_db() as (conn, cursor):
            cursor.execute("""
                SELECT AVG(CAST(json_extract(success_indicators, '$.completion') AS FLOAT))
                FROM interactions
                WHERE json_extract(context, '$.languages') LIKE ?
            """, (f'%{language}%',))
            
            result = cursor.fetchone()[0]
            return float(result) if result is not None else 0.0

    def save_request_metrics(self, request_data: Dict[str, Any]):
        """Save request metrics to the database."""
        with self._get_db() as (conn, cursor):
            cursor.execute("""
                INSERT INTO request_history 
                (request_id, model, endpoint, total_duration, generation_duration, 
                tokens_used, context_size, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                request_data.get("request_id"),
                request_data.get("model"),
                request_data.get("endpoint"),
                request_data.get("total_duration"),
                request_data.get("generation_duration", 0),
                request_data.get("tokens_used", 0),
                request_data.get("context_size", 0),
                request_data.get("timestamp")
            ))
            conn.commit()

    def get_request_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get request history from the database."""
        with self._get_db() as (conn, cursor):
            cursor.execute("""
                SELECT request_id, model, endpoint, total_duration, generation_duration,
                       tokens_used, context_size, timestamp
                FROM request_history
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_average_stats(self, window_hours: int = 24) -> Dict[str, float]:
        """Get average statistics from request history within a time window."""
        with self._get_db() as (conn, cursor):
            window_start = int(time.time()) - (window_hours * 3600)
            cursor.execute("""
                SELECT 
                    AVG(tokens_used) as avg_tokens,
                    AVG(total_duration) as avg_duration,
                    AVG(generation_duration) as avg_generation,
                    COUNT(*) as total_requests,
                    SUM(tokens_used) as total_tokens
                FROM request_history
                WHERE timestamp >= ?
            """, (window_start,))
            
            row = cursor.fetchone()
            return {
                "average_tokens_used": row[0] or 0,
                "average_total_duration": row[1] or 0,
                "average_generation_duration": row[2] or 0,
                "total_requests": row[3] or 0,
                "total_tokens": row[4] or 0
            }

    def get_model_stats(self, window_hours: int = 24) -> Dict[str, Dict[str, float]]:
        """Get statistics grouped by model."""
        with self._get_db() as (conn, cursor):
            window_start = int(time.time()) - (window_hours * 3600)
            cursor.execute("""
                SELECT 
                    model,
                    COUNT(*) as request_count,
                    AVG(tokens_used) as avg_tokens,
                    AVG(total_duration) as avg_duration,
                    SUM(tokens_used) as total_tokens,
                    SUM(context_size) as total_input_tokens,
                    SUM(tokens_used - context_size) as total_output_tokens
                FROM request_history
                WHERE timestamp >= ?
                GROUP BY model
            """, (window_start,))
            
            stats = {}
            for row in cursor.fetchall():
                model = row[0]
                stats[model] = {
                    "request_count": row[1],
                    "average_tokens": row[2] or 0,
                    "average_duration": row[3] or 0,
                    "total_tokens": row[4] or 0,
                    "total_input_tokens": row[5] or 0,
                    "total_output_tokens": row[6] or 0
                }
                
                # Calculate costs for different models
                input_tokens = stats[model]["total_input_tokens"]
                output_tokens = stats[model]["total_output_tokens"]
                
                # Calculate Claude costs ($3/M input, $15/M output)
                claude_input_cost = (input_tokens / 1_000_000) * 3
                claude_output_cost = (output_tokens / 1_000_000) * 15
                stats[model]["claude_cost"] = claude_input_cost + claude_output_cost
                
                # Calculate GPT-4 costs ($2.50/M input, $10/M output)
                gpt4_input_cost = (input_tokens / 1_000_000) * 2.50
                gpt4_output_cost = (output_tokens / 1_000_000) * 10
                stats[model]["gpt4_cost"] = gpt4_input_cost + gpt4_output_cost
                
                # Calculate savings
                stats[model]["cost_savings"] = stats[model]["claude_cost"] - stats[model]["gpt4_cost"]
                
            return stats

    def get_cost_summary(self, window_hours: int = 24) -> Dict[str, float]:
        """Get a summary of costs and potential savings across all models."""
        model_stats = self.get_model_stats(window_hours)
        
        total_claude_cost = sum(stats["claude_cost"] for stats in model_stats.values())
        total_gpt4_cost = sum(stats["gpt4_cost"] for stats in model_stats.values())
        total_savings = sum(stats["cost_savings"] for stats in model_stats.values())
        
        total_input_tokens = sum(stats["total_input_tokens"] for stats in model_stats.values())
        total_output_tokens = sum(stats["total_output_tokens"] for stats in model_stats.values())
        
        return {
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "claude_cost": total_claude_cost,
            "gpt4_cost": total_gpt4_cost,
            "potential_savings": total_savings,
            "time_window_hours": window_hours,
            "savings_percentage": ((total_claude_cost - total_gpt4_cost) / total_claude_cost * 100) if total_claude_cost > 0 else 0
        }
