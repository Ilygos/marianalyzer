"""BM25 full-text indexing using rank-bm25."""

import pickle
from pathlib import Path
from typing import List, Tuple

from rank_bm25 import BM25Okapi

from marianalyzer.config import Config
from marianalyzer.database import Database
from marianalyzer.models import Chunk
from marianalyzer.utils.logging_config import get_logger

logger = get_logger()


class BM25Index:
    """BM25 index for full-text search."""

    def __init__(self):
        """Initialize BM25 index."""
        self.index: BM25Okapi = None
        self.chunks: List[Chunk] = []

    def build(self, chunks: List[Chunk]) -> None:
        """Build BM25 index from chunks.

        Args:
            chunks: List of chunks to index
        """
        logger.info(f"Building BM25 index with {len(chunks)} chunks")

        self.chunks = chunks

        # Tokenize chunk texts
        tokenized_texts = [
            chunk.chunk_text.lower().split()
            for chunk in chunks
        ]

        # Build index
        self.index = BM25Okapi(tokenized_texts)

        logger.info("BM25 index built successfully")

    def search(self, query: str, top_k: int = 50) -> List[Tuple[Chunk, float]]:
        """Search index with query.

        Args:
            query: Search query
            top_k: Number of results to return

        Returns:
            List of (chunk, score) tuples sorted by relevance
        """
        if self.index is None:
            raise RuntimeError("Index not built yet")

        # Tokenize query
        tokenized_query = query.lower().split()

        # Get scores
        scores = self.index.get_scores(tokenized_query)

        # Get top-k indices
        top_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True,
        )[:top_k]

        # Return chunks with scores
        results = [
            (self.chunks[i], scores[i])
            for i in top_indices
        ]

        return results

    def save(self, path: Path) -> None:
        """Save index to disk.

        Args:
            path: Path to save index file
        """
        logger.info(f"Saving BM25 index to {path}")

        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "wb") as f:
            pickle.dump({
                "index": self.index,
                "chunks": self.chunks,
            }, f)

        logger.info(f"BM25 index saved ({path.stat().st_size} bytes)")

    @classmethod
    def load(cls, path: Path) -> "BM25Index":
        """Load index from disk.

        Args:
            path: Path to index file

        Returns:
            Loaded BM25Index
        """
        logger.info(f"Loading BM25 index from {path}")

        with open(path, "rb") as f:
            data = pickle.load(f)

        index = cls()
        index.index = data["index"]
        index.chunks = data["chunks"]

        logger.info(f"BM25 index loaded ({len(index.chunks)} chunks)")

        return index


def build_bm25_index(db: Database, config: Config) -> None:
    """Build and save BM25 index from database.

    Args:
        db: Database instance
        config: Configuration
    """
    # Load all chunks
    chunks = db.get_all_chunks()

    if not chunks:
        logger.warning("No chunks found in database")
        return

    # Build index
    index = BM25Index()
    index.build(chunks)

    # Save to disk
    index.save(config.bm25_path)


def load_bm25_index(config: Config) -> BM25Index:
    """Load BM25 index from disk.

    Args:
        config: Configuration

    Returns:
        Loaded BM25Index
    """
    if not config.bm25_path.exists():
        raise FileNotFoundError(f"BM25 index not found: {config.bm25_path}")

    return BM25Index.load(config.bm25_path)
