"""CLI interface for the analyzer."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from .config import get_config
from .mcp import serve_mcp
from .pipelines import build_index, build_playbook, extract_requirements, ingest_documents

app = typer.Typer(
    name="analyzer",
    help="Company-specific document analyzer with MCP integration",
)

console = Console()


@app.command()
def ingest(
    company_id: str = typer.Argument(..., help="Company identifier"),
    folder: Path = typer.Argument(..., help="Folder containing documents"),
    force: bool = typer.Option(False, "--force", "-f", help="Force re-ingestion"),
) -> None:
    """Ingest documents from a folder."""
    if not folder.exists():
        console.print(f"[red]Folder not found: {folder}[/red]")
        raise typer.Exit(1)
    
    if not folder.is_dir():
        console.print(f"[red]Not a directory: {folder}[/red]")
        raise typer.Exit(1)
    
    console.print(f"[bold]Ingesting documents for {company_id}[/bold]")
    ingest_documents(company_id, folder, force=force)


@app.command()
def build_index_cmd(
    company_id: str = typer.Argument(..., help="Company identifier"),
    batch_size: int = typer.Option(50, help="Batch size for embedding"),
) -> None:
    """Build vector index for a company."""
    console.print(f"[bold]Building index for {company_id}[/bold]")
    build_index(company_id, batch_size=batch_size)


@app.command()
def extract(
    company_id: str = typer.Argument(..., help="Company identifier"),
) -> None:
    """Extract requirements from documents."""
    console.print(f"[bold]Extracting requirements for {company_id}[/bold]")
    extract_requirements(company_id)


@app.command()
def build_playbook_cmd(
    company_id: str = typer.Argument(..., help="Company identifier"),
    doc_type: str = typer.Option("general", help="Document type"),
) -> None:
    """Build company playbook."""
    console.print(f"[bold]Building playbook for {company_id}[/bold]")
    build_playbook(company_id, doc_type=doc_type)


@app.command()
def serve_mcp_cmd() -> None:
    """Start the MCP server."""
    console.print("[bold]Starting MCP server...[/bold]")
    serve_mcp()


@app.command()
def process_all(
    company_id: str = typer.Argument(..., help="Company identifier"),
    folder: Path = typer.Argument(..., help="Folder containing documents"),
    doc_type: str = typer.Option("general", help="Document type"),
    force: bool = typer.Option(False, "--force", "-f", help="Force re-ingestion"),
) -> None:
    """Run the complete pipeline: ingest, index, extract, and build playbook."""
    if not folder.exists():
        console.print(f"[red]Folder not found: {folder}[/red]")
        raise typer.Exit(1)
    
    console.print(f"[bold cyan]Running complete pipeline for {company_id}[/bold cyan]\n")
    
    # Step 1: Ingest
    console.print("[bold]Step 1/4: Ingesting documents[/bold]")
    ingest_documents(company_id, folder, force=force)
    
    # Step 2: Build index
    console.print("\n[bold]Step 2/4: Building vector index[/bold]")
    build_index(company_id)
    
    # Step 3: Extract requirements
    console.print("\n[bold]Step 3/4: Extracting requirements[/bold]")
    extract_requirements(company_id)
    
    # Step 4: Build playbook
    console.print("\n[bold]Step 4/4: Building playbook[/bold]")
    build_playbook(company_id, doc_type=doc_type)
    
    console.print("\n[bold green]Pipeline complete![/bold green]")


@app.command()
def config() -> None:
    """Show configuration."""
    cfg = get_config()
    console.print("[bold]Configuration:[/bold]")
    console.print(f"Data directory: {cfg.data_dir}")
    console.print(f"Database: {cfg.db_path}")
    console.print(f"ChromaDB: {cfg.chroma_path}")
    console.print(f"Ollama host: {cfg.ollama_host}")
    console.print(f"LLM model: {cfg.ollama_llm_model}")
    console.print(f"Embedding model: {cfg.ollama_embedding_model}")


if __name__ == "__main__":
    app()
