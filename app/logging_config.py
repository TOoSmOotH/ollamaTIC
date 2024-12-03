"""
Logging configuration for OllamaTIC.
"""

import logging
import sys
from pathlib import Path

def setup_logging(log_file: str = "ollamaTIC.log"):
    """Setup logging configuration."""
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),  # Log to console
            logging.FileHandler(log_dir / log_file)  # Log to file
        ]
    )
    
    # Set specific logger levels
    logging.getLogger("app.agent").setLevel(logging.DEBUG)
    logging.getLogger("app.learning").setLevel(logging.DEBUG)
    logging.getLogger("app.vector_store").setLevel(logging.INFO)
