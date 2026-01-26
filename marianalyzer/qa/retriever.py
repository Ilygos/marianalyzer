"""Hybrid retrieval combining BM25 and vector search."""

from typing import List, Tuple

from marianalyzer.config import Config
from marianalyzer.indexing.bm25_index import load_bm25_index
from marianalyzer.indexing.vector_index import load_vector_index
from marianalyzer.models import Chunk
from marianalyzer.utils.logging_config import get_logger

logger = get_logger()


class HybridRetriever:
    """Hybrid retriever combining BM25 and vector search."""

    def __init__(self, config: Config):
        """Initialize hybrid retriever.

        Args:
            config: Configuration
        """
        self.config = config

        # Load indexes
        logger.info("Loading BM25 index...")
        self.bm25_index = load_bm25_index(config)

        logger.info("Loading vector index...")
        self.vector_index = load_vector_index(config)

    def retrieve(
        self,
        query: str,
        top_k: int = 20,
    ) -> List[Tuple[Chunk, float]]:
        """Retrieve relevant chunks using hybrid search.

        Combines BM25 and vector search results with score normalization.

        Args:
            query: Search query
            top_k: Number of results to return

        Returns:
            List of (chunk, score) tuples sorted by relevance
        """
        logger.info(f"Retrieving top {top_k} chunks for query: {query[:80]}...")

        # BM25 retrieval
        bm25_results = self.bm25_index.search(
            query,
            top_k=self.config.bm25_top_k,
        )

        # Vector retrieval
        vector_results = self.vector_index.search_by_text(
            query,
            embed_model=self.config.embed_model,
            ollama_host=self.config.ollama_host,
            top_k=self.config.vector_top_k,
        )

        # Merge results
        merged = self._merge_results(
            bm25_results=bm25_results,
            vector_results=vector_results,
            top_k=top_k,
        )

        logger.info(f"Retrieved {len(merged)} chunks")

        return merged

    def _merge_results(
        self,
        bm25_results: List[Tuple[Chunk, float]],
        vector_results: List[Tuple[str, float, dict]],
        top_k: int,
    ) -> List[Tuple[Chunk, float]]:
        """Merge and rerank BM25 and vector search results.

        Uses reciprocal rank fusion (RRF) for combining scores.

        Args:
            bm25_results: BM25 results (chunk, score)
            vector_results: Vector results (chunk_id, score, metadata)
            top_k: Number of results to return

        Returns:
            Merged and reranked results
        """
        # Create chunk lookup from BM25 results
        chunk_lookup = {str(chunk.id): chunk for chunk, _ in bm25_results}

        # Reciprocal Rank Fusion constant
        k = 60

        # Score each chunk using RRF
        chunk_scores = {}

        # Add BM25 scores
        for rank, (chunk, score) in enumerate(bm25_results, start=1):
            chunk_id = str(chunk.id)
            chunk_scores[chunk_id] = chunk_scores.get(chunk_id, 0) + 1.0 / (k + rank)

        # Add vector scores
        for rank, (chunk_id, score, metadata) in enumerate(vector_results, start=1):
            chunk_scores[chunk_id] = chunk_scores.get(chunk_id, 0) + 1.0 / (k + rank)

            # Add to lookup if not already there
            if chunk_id not in chunk_lookup:
                # Recreate chunk from metadata
                from marianalyzer.models import Chunk as ChunkModel
                chunk = ChunkModel(
                    id=int(chunk_id),
                    doc_id=int(metadata.get("doc_id", 0)),
                    chunk_index=0,
                    chunk_text="",  # Will be filled from DB if needed
                    chunk_type=metadata.get("chunk_type", "unknown"),
                    citation=metadata.get("citation", ""),
                )
                chunk_lookup[chunk_id] = chunk

        # Sort by combined score
        sorted_chunks = sorted(
            chunk_scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:top_k]

        # Return as (chunk, score) tuples
        results = [
            (chunk_lookup[chunk_id], score)
            for chunk_id, score in sorted_chunks
            if chunk_id in chunk_lookup
        ]

        return results


def retrieve_chunks(
    query: str,
    config: Config,
    top_k: int = 20,
) -> List[Chunk]:
    """Retrieve relevant chunks for a query.

    Args:
        query: Search query
        config: Configuration
        top_k: Number of results to return

    Returns:
        List of chunks
    """
    retriever = HybridRetriever(config)
    results = retriever.retrieve(query, top_k=top_k)
    return [chunk for chunk, _ in results]
