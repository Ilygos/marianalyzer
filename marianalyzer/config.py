"""Configuration management using Pydantic settings."""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Ollama Configuration
    ollama_host: str = Field(
        default="http://localhost:11434",
        description="Ollama API host URL",
    )
    llm_model: str = Field(
        default="qwen2.5:7b-instruct",
        description="LLM model for generation",
    )
    embed_model: str = Field(
        default="nomic-embed-text",
        description="Embedding model",
    )

    # Data Directories
    data_dir: Path = Field(
        default=Path(".rfp_rag"),
        description="Root data directory",
    )
    db_path: Optional[Path] = Field(
        default=None,
        description="SQLite database path",
    )
    chroma_path: Optional[Path] = Field(
        default=None,
        description="ChromaDB storage path",
    )
    bm25_path: Optional[Path] = Field(
        default=None,
        description="BM25 index pickle path",
    )

    # Chunking Parameters
    chunk_size: int = Field(
        default=400,
        description="Target chunk size in tokens",
    )
    chunk_overlap: int = Field(
        default=100,
        description="Overlap between chunks in tokens",
    )

    # Retrieval Parameters
    bm25_top_k: int = Field(
        default=50,
        description="Number of BM25 results to retrieve",
    )
    vector_top_k: int = Field(
        default=50,
        description="Number of vector results to retrieve",
    )
    hybrid_top_k: int = Field(
        default=20,
        description="Number of final hybrid results",
    )

    # Extraction Parameters
    requirement_confidence_threshold: float = Field(
        default=0.7,
        description="Minimum confidence for requirement extraction",
    )

    # Aggregation Parameters
    clustering_threshold: float = Field(
        default=0.85,
        description="Similarity threshold for clustering",
    )
    min_cluster_size: int = Field(
        default=2,
        description="Minimum cluster size",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )
    log_file: Optional[Path] = Field(
        default=None,
        description="Log file path",
    )

    def __init__(self, **kwargs):
        """Initialize config and set dependent paths."""
        super().__init__(**kwargs)

        # Set dependent paths if not explicitly provided
        if self.db_path is None:
            self.db_path = self.data_dir / "rfp_rag.db"
        if self.chroma_path is None:
            self.chroma_path = self.data_dir / "chroma"
        if self.bm25_path is None:
            self.bm25_path = self.data_dir / "bm25_index.pkl"
        if self.log_file is None:
            self.log_file = self.data_dir / "rfp_rag.log"

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if self.chroma_path:
            self.chroma_path.parent.mkdir(parents=True, exist_ok=True)


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create global config instance."""
    global _config
    if _config is None:
        _config = Config()
        _config.ensure_directories()
    return _config


def reset_config() -> None:
    """Reset global config (mainly for testing)."""
    global _config
    _config = None
