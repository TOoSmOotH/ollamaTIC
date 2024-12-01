from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    ollama_server: str = "http://localhost:11434"
    default_model: str = "llama2"
    metrics_enabled: bool = True

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
