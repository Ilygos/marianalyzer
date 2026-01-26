"""Vector indexing using ChromaDB."""

from typing import List, Tuple

import chromadb
from chromadb.config import Settings

from marianalyzer.config import Config
from marianalyzer.database import Database
from marianalyzer.llm.embedder import embed_batch
from marianalyzer.models import Chunk
from marianalyzer.utils.logging_config import get_logger

logger = get_logger()


class VectorIndex:
    """Vector index using ChromaDB."""

    def __init__(self, persist_directory: str):
        """Initialize vector index.

        Args:
            persist_directory: Directory to persist ChromaDB data
        """
        self.persist_directory = persist_directory

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
            ),
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="chunks",
            metadata={"hnsw:space": "cosine"},
        )

        logger.info(f"Vector index initialized at {persist_directory}")

    def build(
        self,
        chunks: List[Chunk],
        embed_model: str,
        ollama_host: str,
        batch_size: int = 10,
    ) -> None:
        """Build vector index from chunks.

        Args:
            chunks: List of chunks to index
            embed_model: Embedding model name
            ollama_host: Ollama API host
            batch_size: Batch size for embedding generation
        """
        logger.info(f"Building vector index with {len(chunks)} chunks")

        # Clear existing collection
        try:
            # Deleting and re-creating avoids Chroma validation errors on empty filters
            self.client.delete_collection("chunks")
        except Exception as exc:  # Chroma raises if the collection does not exist
            logger.debug(f"Collection delete skipped: {exc}")

        self.collection = self.client.get_or_create_collection(
            name="chunks",
            metadata={"hnsw:space": "cosine"},
        )

        # Extract texts and IDs
        texts = [chunk.chunk_text for chunk in chunks]
        ids = [str(chunk.id) for chunk in chunks]

        # Generate embeddings in batches
        logger.info("Generating embeddings...")
        embeddings = embed_batch(
            texts=texts,
            model=embed_model,
            ollama_host=ollama_host,
            batch_size=batch_size,
        )

        # Prepare metadata
        metadatas = [
            {
                "doc_id": str(chunk.doc_id),
                "chunk_type": chunk.chunk_type,
                "citation": chunk.citation,
            }
            for chunk in chunks
        ]

        # Add to collection in batches
        logger.info("Adding to ChromaDB...")
        for i in range(0, len(chunks), batch_size):
            end_idx = min(i + batch_size, len(chunks))

            self.collection.add(
                ids=ids[i:end_idx],
                embeddings=embeddings[i:end_idx],
                documents=texts[i:end_idx],
                metadatas=metadatas[i:end_idx],
            )

        logger.info(f"Vector index built successfully ({len(chunks)} chunks)")

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 50,
    ) -> List[Tuple[str, float, dict]]:
        """Search index with query embedding.

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return

        Returns:
            List of (chunk_id, score, metadata) tuples
        """
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )

        # Flatten results
        output = []
        if results["ids"] and results["distances"]:
            for chunk_id, distance, metadata in zip(
                results["ids"][0],
                results["distances"][0],
                results["metadatas"][0],
            ):
                # Convert distance to similarity score (1 - distance for cosine)
                score = 1.0 - distance
                output.append((chunk_id, score, metadata))

        return output

    def search_by_text(
        self,
        query: str,
        embed_model: str,
        ollama_host: str,
        top_k: int = 50,
    ) -> List[Tuple[str, float, dict]]:
        """Search index with text query.

        Args:
            query: Search query text
            embed_model: Embedding model name
            ollama_host: Ollama API host
            top_k: Number of results to return

        Returns:
            List of (chunk_id, score, metadata) tuples
        """
        from marianalyzer.llm.embedder import embed_single

        # Generate query embedding
        query_embedding = embed_single(query, embed_model, ollama_host)

        # Search
        return self.search(query_embedding, top_k)

    def get_count(self) -> int:
        """Get number of indexed chunks.

        Returns:
            Number of chunks in index
        """
        return self.collection.count()


def build_vector_index(db: Database, config: Config) -> None:
    """Build and save vector index from database.

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
    index = VectorIndex(str(config.chroma_path))
    index.build(
        chunks=chunks,
        embed_model=config.embed_model,
        ollama_host=config.ollama_host,
        batch_size=10,
    )


def load_vector_index(config: Config) -> VectorIndex:
    """Load vector index from disk.

    Args:
        config: Configuration

    Returns:
        Loaded VectorIndex
    """
    if not config.chroma_path.exists():
        raise FileNotFoundError(f"Vector index not found: {config.chroma_path}")

    return VectorIndex(str(config.chroma_path))
