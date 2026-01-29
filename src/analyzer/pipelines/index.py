"""Index building pipeline."""

from rich.console import Console
from rich.progress import track

from ..config import get_config
from ..store import ChromaStore, SQLiteStore
from ..utils import generate_embedding

console = Console()


def build_index(company_id: str, batch_size: int = 50) -> None:
    """
    Build vector index for a company's documents.
    
    Args:
        company_id: Company identifier
        batch_size: Number of chunks to process at once
    """
    config = get_config()
    sqlite_store = SQLiteStore(config.db_path)
    chroma_store = ChromaStore(config.chroma_path)
    
    # Get all chunks for the company
    chunks = sqlite_store.get_chunks_by_company(company_id)
    
    console.print(f"Building index for {len(chunks)} chunks")
    
    # Process in batches
    for i in track(range(0, len(chunks), batch_size), description="Embedding chunks"):
        batch = chunks[i:i + batch_size]
        
        # Generate embeddings
        embeddings = []
        for chunk in batch:
            embedding = generate_embedding(chunk.text)
            embeddings.append(embedding)
        
        # Add to ChromaDB
        chroma_store.add_chunks(company_id, batch, embeddings)
    
    console.print("[green]Index building complete[/green]")
