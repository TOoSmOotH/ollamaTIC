from pydantic_settings import BaseSettings
from typing import Dict, Any
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    
    # Ollama server settings
    ollama_server: str = "http://localhost:11434"
    default_model: str = "llama2"
    
    # Agent configuration per model
    # Example:
    # {
    #     "codellama": {
    #         "agent_enabled": true,
    #         "agent_mode": "active",
    #         "enabled_features": ["code_enhancement", "context_aware"]
    #     }
    # }
    model_configs: Dict[str, Dict[str, Any]] = {
        "codellama": {
            "agent_enabled": True,
            "agent_mode": "active",
            "enabled_features": ["code_enhancement", "context_aware"]
        }
    }

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
