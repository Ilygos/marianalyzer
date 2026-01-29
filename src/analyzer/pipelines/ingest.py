"""Document ingestion pipeline."""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import track

from ..config import get_config
from ..models import Document
from ..parsers import DOCXParser, PDFParser, XLSXParser
from ..store import SQLiteStore

console = Console()


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def get_parser_for_file(file_path: Path):
    """Get appropriate parser for file type."""
    suffix = file_path.suffix.lower()
    
    if suffix == ".docx":
        return DOCXParser()
    elif suffix == ".xlsx":
        return XLSXParser()
    elif suffix == ".pdf":
        return PDFParser()
    else:
        return None


def ingest_documents(
    company_id: str,
    folder_path: Path,
    force: bool = False,
) -> None:
    """
    Ingest documents from a folder.
    
    Args:
        company_id: Company identifier
        folder_path: Path to folder containing documents
        force: Force re-ingestion even if files haven't changed
    """
    config = get_config()
    store = SQLiteStore(config.db_path)
    
    # Find all supported documents
    supported_extensions = {".pdf", ".docx", ".xlsx"}
    files = []
    for ext in supported_extensions:
        files.extend(folder_path.rglob(f"*{ext}"))
    
    console.print(f"Found {len(files)} documents to process")
    
    processed = 0
    skipped = 0
    errors = 0
    
    for file_path in track(files, description="Ingesting documents"):
        try:
            # Compute file hash
            file_hash = compute_file_hash(file_path)
            file_stat = file_path.stat()
            
            # Generate doc_id
            doc_id = hashlib.md5(
                f"{company_id}:{file_path.relative_to(folder_path)}".encode()
            ).hexdigest()[:16]
            
            # Check if document already exists and hasn't changed
            if not force:
                existing_doc = store.get_document(doc_id)
                if existing_doc and existing_doc.sha256 == file_hash:
                    skipped += 1
                    continue
            
            # If document exists with different hash, delete old data
            existing_doc = store.get_document(doc_id)
            if existing_doc:
                store.delete_document(doc_id)
            
            # Parse document
            parser = get_parser_for_file(file_path)
            if parser is None:
                console.print(f"[yellow]No parser for {file_path.suffix}[/yellow]")
                skipped += 1
                continue
            
            chunks, headings = parser.parse(file_path, doc_id, company_id)
            
            # Store document metadata
            document = Document(
                doc_id=doc_id,
                company_id=company_id,
                path=str(file_path.relative_to(folder_path)),
                type=file_path.suffix.lstrip("."),
                sha256=file_hash,
                mtime=file_stat.st_mtime,
                size=file_stat.st_size,
                created_at=datetime.utcnow(),
            )
            store.insert_document(document)
            
            # Store chunks
            for chunk in chunks:
                store.insert_chunk(chunk)
            
            # Store headings
            for heading in headings:
                store.insert_heading(heading)
            
            processed += 1
            
        except Exception as e:
            console.print(f"[red]Error processing {file_path}: {e}[/red]")
            errors += 1
    
    console.print(f"\n[green]Processed: {processed}[/green]")
    console.print(f"[yellow]Skipped: {skipped}[/yellow]")
    if errors > 0:
        console.print(f"[red]Errors: {errors}[/red]")
