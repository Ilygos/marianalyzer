"""ChromaDB storage implementation."""

from pathlib import Path
from typing import Any, Optional

import chromadb
from chromadb.config import Settings

from ..models import Chunk


class ChromaStore:
    """ChromaDB vector store."""

    def __init__(self, chroma_path: Path):
        """Initialize the ChromaDB store."""
        self.chroma_path = chroma_path
        self.chroma_path.mkdir(parents=True, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=str(chroma_path),
            settings=Settings(anonymized_telemetry=False),
        )

    def get_collection_name(self, company_id: str, collection_type: str = "chunks") -> str:
        """Get collection name for a company."""
        return f"{collection_type}_{company_id}"

    def get_or_create_collection(self, company_id: str, collection_type: str = "chunks"):
        """Get or create a collection for a company."""
        collection_name = self.get_collection_name(company_id, collection_type)
        return self.client.get_or_create_collection(
            name=collection_name,
            metadata={"company_id": company_id, "type": collection_type},
        )

    def add_chunks(
        self,
        company_id: str,
        chunks: list[Chunk],
        embeddings: list[list[float]],
    ) -> None:
        """Add chunks with embeddings to the vector store."""
        collection = self.get_or_create_collection(company_id, "chunks")
        
        ids = [chunk.chunk_id for chunk in chunks]
        documents = [chunk.text for chunk in chunks]
        metadatas = [
            {
                "doc_id": chunk.doc_id,
                "company_id": chunk.company_id,
                "chunk_type": chunk.chunk_type.value,
                "structure_path": ",".join(chunk.structure_path),
                "locator": str(chunk.locator.model_dump()),
            }
            for chunk in chunks
        ]
        
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def search_chunks(
        self,
        company_id: str,
        query_embedding: list[float],
        top_k: int = 5,
        where: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Search for similar chunks."""
        collection = self.get_or_create_collection(company_id, "chunks")
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
        )
        
        return results

    def delete_document_chunks(self, company_id: str, doc_id: str) -> None:
        """Delete all chunks for a document."""
        collection = self.get_or_create_collection(company_id, "chunks")
        
        # Query for all chunks with this doc_id
        results = collection.get(where={"doc_id": doc_id})
        
        if results["ids"]:
            collection.delete(ids=results["ids"])

    def delete_collection(self, company_id: str, collection_type: str = "chunks") -> None:
        """Delete a collection."""
        collection_name = self.get_collection_name(company_id, collection_type)
        try:
            self.client.delete_collection(name=collection_name)
        except Exception:
            pass  # Collection doesn't exist
