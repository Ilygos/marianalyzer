"""CLI application using Typer."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from marianalyzer.config import get_config
from marianalyzer.database import Database
from marianalyzer.utils.logging_config import setup_logging

app = typer.Typer(
    name="rfp-rag",
    help="Local RAG system for analyzing RFP and call-for-offer documents",
    no_args_is_help=True,
)
console = Console()


def get_db() -> Database:
    """Get database instance."""
    config = get_config()
    db = Database(config.db_path)
    db.connect()
    db.create_schema()
    return db


@app.command()
def ingest(
    folder: Path = typer.Argument(
        ...,
        help="Folder containing documents to ingest",
        exists=True,
        dir_okay=True,
        file_okay=False,
    ),
    recursive: bool = typer.Option(
        True,
        "--recursive/--no-recursive",
        help="Recursively scan subfolders",
    ),
):
    """Ingest documents from a folder."""
    from marianalyzer.ingest.document_processor import ingest_folder

    config = get_config()
    setup_logging(config.log_file, config.log_level)

    console.print(f"[bold blue]Ingesting documents from:[/bold blue] {folder}")

    db = get_db()
    try:
        stats = ingest_folder(folder, db, recursive=recursive)

        console.print(f"\n[bold green]Ingestion Complete![/bold green]")
        console.print(f"Total files: {stats['total_files']}")
        console.print(f"[green]Successful: {stats['successful']}[/green]")
        if stats['failed'] > 0:
            console.print(f"[red]Failed: {stats['failed']}[/red]")

    finally:
        db.close()


@app.command(name="build-index")
def build_index():
    """Build BM25 and vector indexes for retrieval."""
    from marianalyzer.indexing.bm25_index import build_bm25_index
    from marianalyzer.indexing.vector_index import build_vector_index

    config = get_config()
    setup_logging(config.log_file, config.log_level)

    console.print("[bold blue]Building indexes...[/bold blue]")

    db = get_db()
    try:
        # Build BM25 index
        console.print("\n[cyan]Building BM25 index...[/cyan]")
        build_bm25_index(db, config)
        console.print("[green]BM25 index complete![/green]")

        # Build vector index
        console.print("\n[cyan]Building vector index...[/cyan]")
        build_vector_index(db, config)
        console.print("[green]Vector index complete![/green]")

        console.print("\n[bold green]All indexes built successfully![/bold green]")

    finally:
        db.close()


@app.command()
def extract(
    pattern: str = typer.Argument(
        "requirements",
        help="Pattern to extract (requirements, risks, etc.)",
    ),
):
    """Extract patterns (requirements, etc.) from documents."""
    from marianalyzer.extraction.requirement_extractor import extract_requirements

    config = get_config()
    setup_logging(config.log_file, config.log_level)

    if pattern != "requirements":
        console.print(f"[red]Unknown pattern: {pattern}[/red]")
        console.print("Currently only 'requirements' is supported")
        raise typer.Exit(1)

    console.print("[bold blue]Extracting requirements...[/bold blue]")

    db = get_db()
    try:
        stats = extract_requirements(db, config)

        console.print(f"\n[bold green]Extraction Complete![/bold green]")
        console.print(f"Requirements extracted: {stats['extracted']}")
        console.print(f"Chunks processed: {stats['chunks_processed']}")

    finally:
        db.close()


@app.command()
def aggregate():
    """Aggregate and cluster extracted patterns."""
    from marianalyzer.aggregation.family_builder import build_families

    config = get_config()
    setup_logging(config.log_file, config.log_level)

    console.print("[bold blue]Aggregating requirements...[/bold blue]")

    db = get_db()
    try:
        stats = build_families(db, config)

        console.print(f"\n[bold green]Aggregation Complete![/bold green]")
        console.print(f"Families created: {stats['families_created']}")
        console.print(f"Requirements clustered: {stats['requirements_clustered']}")

    finally:
        db.close()


@app.command()
def ask(
    question: str = typer.Argument(..., help="Question to answer"),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON",
    ),
    top_k: int = typer.Option(
        20,
        "--top-k",
        help="Number of results to return",
    ),
):
    """Ask a question and get a structured answer with citations."""
    import json

    from marianalyzer.qa.answer_engine import answer_question

    config = get_config()
    setup_logging(config.log_file, config.log_level)

    db = get_db()
    try:
        response = answer_question(question, db, config, top_k=top_k)

        if json_output:
            console.print(json.dumps(response.model_dump(), indent=2))
        else:
            console.print(f"\n[bold cyan]Question:[/bold cyan] {response.query}")
            console.print(f"\n[bold green]Answer:[/bold green]\n{response.answer}")

            if response.evidence:
                console.print(f"\n[bold yellow]Evidence ({len(response.evidence)} sources):[/bold yellow]")
                for i, ev in enumerate(response.evidence[:10], 1):
                    console.print(f"\n{i}. [dim]{ev.get('citation', 'N/A')}[/dim]")
                    console.print(f"   {ev.get('chunk_text', '')[:200]}...")

    finally:
        db.close()


@app.command()
def status():
    """Show system status and statistics."""
    config = get_config()
    setup_logging(config.log_file, config.log_level)

    db = get_db()
    try:
        # Get counts
        doc_count = db.count_documents()
        chunk_count = db.count_chunks()
        req_count = db.count_requirements()
        family_count = db.count_families()

        # Create stats table
        table = Table(title="RFP RAG Status")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="green", justify="right")

        table.add_row("Documents", str(doc_count))
        table.add_row("Chunks", str(chunk_count))
        table.add_row("Requirements", str(req_count))
        table.add_row("Requirement Families", str(family_count))

        console.print(table)

        # Show paths
        console.print(f"\n[bold]Data Directory:[/bold] {config.data_dir}")
        console.print(f"[bold]Database:[/bold] {config.db_path}")
        console.print(f"[bold]Ollama Host:[/bold] {config.ollama_host}")
        console.print(f"[bold]LLM Model:[/bold] {config.llm_model}")

    finally:
        db.close()


@app.command(name="list-families")
def list_families(
    top: int = typer.Option(
        20,
        "--top",
        help="Number of top families to show",
    ),
):
    """List top requirement families."""
    config = get_config()
    setup_logging(config.log_file, config.log_level)

    db = get_db()
    try:
        families = db.get_top_families(limit=top)

        if not families:
            console.print("[yellow]No families found. Run 'aggregate' first.[/yellow]")
            return

        table = Table(title=f"Top {len(families)} Requirement Families")
        table.add_column("Rank", style="cyan", justify="right")
        table.add_column("Canonical Text", style="white")
        table.add_column("Members", style="green", justify="right")
        table.add_column("Documents", style="blue", justify="right")

        for i, family in enumerate(families, 1):
            table.add_row(
                str(i),
                family.canonical_text[:80] + ("..." if len(family.canonical_text) > 80 else ""),
                str(family.member_count),
                str(family.doc_count),
            )

        console.print(table)

    finally:
        db.close()


if __name__ == "__main__":
    app()
