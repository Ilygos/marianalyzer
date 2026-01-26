"""Batch embedding generation utilities."""

from typing import List

from tqdm import tqdm

from marianalyzer.llm.ollama_client import OllamaClient
from marianalyzer.utils.logging_config import get_logger

logger = get_logger()


def embed_batch(
    texts: List[str],
    model: str,
    ollama_host: str = "http://localhost:11434",
    batch_size: int = 10,
    show_progress: bool = True,
) -> List[List[float]]:
    """Generate embeddings for texts in batches.

    Args:
        texts: List of texts to embed
        model: Embedding model name
        ollama_host: Ollama API host
        batch_size: Number of texts per batch
        show_progress: Whether to show progress bar

    Returns:
        List of embedding vectors
    """
    if not texts:
        return []

    client = OllamaClient(ollama_host)

    # Check if Ollama is running
    if not client.check_health():
        raise RuntimeError("Ollama is not running or not accessible")

    logger.info(f"Generating embeddings for {len(texts)} texts in batches of {batch_size}")

    embeddings = []

    # Process in batches
    iterator = range(0, len(texts), batch_size)
    if show_progress:
        iterator = tqdm(iterator, desc="Embedding", unit="batch")

    for i in iterator:
        batch = texts[i:i+batch_size]

        try:
            batch_embeddings = client.embed(batch, model)
            embeddings.extend(batch_embeddings)

        except Exception as e:
            logger.error(f"Failed to embed batch {i//batch_size + 1}: {e}")
            # Add zero vectors as fallback
            fallback_dim = 768  # Default dimension
            if embeddings:
                fallback_dim = len(embeddings[0])
            embeddings.extend([[0.0] * fallback_dim] * len(batch))

    logger.info(f"Generated {len(embeddings)} embeddings")

    return embeddings


def embed_single(
    text: str,
    model: str,
    ollama_host: str = "http://localhost:11434",
) -> List[float]:
    """Generate embedding for a single text.

    Args:
        text: Text to embed
        model: Embedding model name
        ollama_host: Ollama API host

    Returns:
        Embedding vector
    """
    client = OllamaClient(ollama_host)
    embeddings = client.embed([text], model)
    return embeddings[0] if embeddings else []
