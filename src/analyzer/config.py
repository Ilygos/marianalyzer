"""Configuration for the analyzer."""

import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Application configuration."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Paths
    data_dir: Path = Path.home() / ".analyzer" / "data"
    db_path: Optional[Path] = None
    chroma_path: Optional[Path] = None

    # Ollama settings
    ollama_host: str = "http://localhost:11434"
    ollama_llm_model: str = "qwen2.5:7b-instruct"
    ollama_embedding_model: str = "nomic-embed-text"

    # LLM settings
    llm_temperature: float = 0.1
    llm_max_tokens: int = 4096

    # Extraction settings
    requirement_keywords: list[str] = [
        "must",
        "shall",
        "should",
        "required",
        "mandatory",
        "obligatory",
    ]

    # Chunk settings
    max_chunk_size: int = 2000
    chunk_overlap: int = 200

    # Retrieval settings
    default_top_k: int = 5
    similarity_threshold: float = 0.7

    # Playbook settings
    min_section_frequency: float = 0.3  # Section must appear in 30% of docs to be "typical"
    required_section_threshold: float = 0.8  # 80% frequency = required

    def __init__(self, **kwargs):
        """Initialize config and set up paths."""
        super().__init__(**kwargs)
        
        # Set default paths if not provided
        if self.db_path is None:
            self.db_path = self.data_dir / "analyzer.db"
        if self.chroma_path is None:
            self.chroma_path = self.data_dir / "chroma"
        
        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global config instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def set_config(config: Config) -> None:
    """Set the global config instance."""
    global _config
    _config = config
