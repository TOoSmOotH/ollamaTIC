"""
Storage system for persisting learned patterns and interactions.
"""

import json
from typing import Dict, Any, Optional
from pathlib import Path
import pickle
from datetime import datetime
import logging
from app.learning import LanguagePatterns, CodeBlock
import sqlite3
from contextlib import contextmanager
import threading

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
