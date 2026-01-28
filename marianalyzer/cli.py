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
        help="Pattern to extract: requirements, success_points, failure_points, risks, constraints, all",
    ),
    confidence: float = typer.Option(
        None,
        "--confidence",
        "-c",
        help="Minimum confidence threshold (0.0-1.0)",
    ),
):
    """Extract patterns from documents.

    Pattern types:
    - requirements: Must/shall/should statements
    - success_points: Achievements, completions, proven capabilities
    - failure_points: Issues, gaps, weaknesses, concerns
    - risks: Potential future problems or threats
    - constraints: Limitations, restrictions, boundaries
    - all: Extract all pattern types
    """
    from marianalyzer.extraction.pattern_extractor import extract_patterns, extract_all_pattern_types
    from marianalyzer.extraction.requirement_extractor import extract_requirements

    config = get_config()
    setup_logging(config.log_file, config.log_level)

    valid_patterns = ["requirements", "success_points", "failure_points", "risks", "constraints", "all"]

    if pattern not in valid_patterns:
        console.print(f"[red]Unknown pattern: {pattern}[/red]")
        console.print(f"Valid patterns: {', '.join(valid_patterns)}")
        raise typer.Exit(1)

    db = get_db()
    try:
        if pattern == "all":
            console.print("[bold blue]Extracting all pattern types...[/bold blue]\n")

            # Extract requirements first (legacy table)
            console.print("[cyan]Extracting requirements...[/cyan]")
            req_stats = extract_requirements(db, config)
            console.print(
                f"[green]Requirements: {req_stats['extracted']} extracted[/green]\n"
            )

            # Extract all new pattern types
            pattern_types = ["success_points", "failure_points", "risks", "constraints"]
            for pt in pattern_types:
                console.print(f"[cyan]Extracting {pt}...[/cyan]")
                stats = extract_patterns(db, config, pt, confidence)
                console.print(
                    f"[green]{pt.replace('_', ' ').title()}: {stats['extracted']} extracted[/green]\n"
                )

            console.print(f"[bold green]All extractions complete![/bold green]")

        elif pattern == "requirements":
            console.print("[bold blue]Extracting requirements...[/bold blue]")
            stats = extract_requirements(db, config)

            console.print(f"\n[bold green]Extraction Complete![/bold green]")
            console.print(f"Requirements extracted: {stats['extracted']}")
            console.print(f"Chunks processed: {stats['chunks_processed']}")

        else:
            # New pattern types
            pattern_name = pattern.replace("_", " ").title()
            console.print(f"[bold blue]Extracting {pattern_name}...[/bold blue]")

            stats = extract_patterns(db, config, pattern, confidence)

            console.print(f"\n[bold green]Extraction Complete![/bold green]")
            console.print(f"{pattern_name} extracted: {stats['extracted']}")
            console.print(f"Chunks processed: {stats['chunks_processed']}")
            if stats.get('skipped'):
                console.print(f"Skipped (no keywords): {stats['skipped']}")

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
    pattern_type: Optional[str] = typer.Option(
        None,
        "--pattern-type",
        "-p",
        help="Specific pattern type: success, failure, risk, constraint, requirement",
    ),
):
    """Ask a question and get a structured answer.

    The system automatically detects question type and provides relevant answers:
    - Questions about successes, achievements, strengths → Success points
    - Questions about failures, issues, problems → Failure points
    - Questions about risks, threats, vulnerabilities → Risks
    - Questions about constraints, limitations → Constraints
    - Questions about requirements → Requirements
    - Comparative questions → Distribution analysis
    - General questions → Full document search

    Examples:
        marianalyzer ask "What are the main success points?"
        marianalyzer ask "What risks have been identified?"
        marianalyzer ask "Compare successes and failures"
        marianalyzer ask "What are the top requirements?"
    """
    import json

    from marianalyzer.qa.pattern_qa import (
        answer_comparative_question,
        answer_pattern_question,
        is_comparative_question,
    )
    from marianalyzer.qa.answer_engine import answer_question

    config = get_config()
    setup_logging(config.log_file, config.log_level)

    db = get_db()
    try:
        # Determine question type and route to appropriate handler
        if is_comparative_question(question):
            response = answer_comparative_question(question, db, config)
        elif pattern_type or any(
            kw in question.lower()
            for kw in ["success", "failure", "risk", "constraint", "requirement"]
        ):
            response = answer_pattern_question(
                question, db, config, pattern_type=pattern_type, top_k=top_k
            )
        else:
            # Fall back to general QA
            response = answer_question(question, db, config, top_k=top_k)

        if json_output:
            console.print(json.dumps(response.model_dump(), indent=2))
        else:
            console.print(f"\n[bold cyan]Question:[/bold cyan] {response.query}")
            console.print(f"\n[bold green]Answer:[/bold green]\n{response.answer}")

            if response.evidence:
                console.print(
                    f"\n[bold yellow]Evidence ({len(response.evidence)} sources):[/bold yellow]"
                )
                for i, ev in enumerate(response.evidence[:10], 1):
                    if "citation" in ev:
                        console.print(f"\n{i}. [dim]{ev.get('citation', 'N/A')}[/dim]")
                        console.print(f"   {ev.get('chunk_text', '')[:200]}...")
                    elif "pattern_text" in ev:
                        console.print(f"\n{i}. {ev.get('pattern_text', '')[:150]}...")
                        if ev.get("confidence"):
                            console.print(f"   [dim]Confidence: {ev['confidence']:.2f}[/dim]")
                    elif "pattern_type" in ev:
                        console.print(
                            f"\n{i}. {ev['pattern_type']}: {ev.get('count', 0)} "
                            f"({ev.get('percentage', 0):.1f}%)"
                        )

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

        # Get pattern counts
        success_count = db.count_patterns("success_point")
        failure_count = db.count_patterns("failure_point")
        risk_count = db.count_patterns("risk")
        constraint_count = db.count_patterns("constraint")
        total_patterns = db.count_patterns()

        # Create stats table
        table = Table(title="Document Analyzer Status")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="green", justify="right")

        table.add_row("Documents", str(doc_count))
        table.add_row("Chunks", str(chunk_count))
        table.add_row("", "")  # Separator
        table.add_row("[bold]Extracted Patterns", "[bold]")
        table.add_row("  Requirements (legacy)", str(req_count))
        table.add_row("  Success Points", str(success_count))
        table.add_row("  Failure Points", str(failure_count))
        table.add_row("  Risks", str(risk_count))
        table.add_row("  Constraints", str(constraint_count))
        table.add_row("  [bold]Total Patterns", f"[bold]{total_patterns}")
        table.add_row("", "")  # Separator
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


@app.command(name="list-patterns")
def list_patterns(
    pattern_type: str = typer.Argument(
        ...,
        help="Pattern type: success_points, failure_points, risks, constraints",
    ),
    limit: int = typer.Option(
        50,
        "--limit",
        "-n",
        help="Maximum number of patterns to show",
    ),
    min_confidence: float = typer.Option(
        0.0,
        "--min-confidence",
        "-c",
        help="Minimum confidence threshold (0.0-1.0)",
    ),
):
    """List extracted patterns of a specific type."""
    config = get_config()
    setup_logging(config.log_file, config.log_level)

    valid_types = ["success_points", "failure_points", "risks", "constraints"]
    if pattern_type not in valid_types:
        console.print(f"[red]Invalid pattern type: {pattern_type}[/red]")
        console.print(f"Valid types: {', '.join(valid_types)}")
        raise typer.Exit(1)

    db = get_db()
    try:
        patterns = db.get_patterns_by_type(pattern_type)

        if not patterns:
            console.print(
                f"[yellow]No {pattern_type} found. Run 'extract {pattern_type}' first.[/yellow]"
            )
            return

        # Filter by confidence
        if min_confidence > 0:
            patterns = [p for p in patterns if p.confidence >= min_confidence]

        # Limit results
        patterns = patterns[:limit]

        # Create table
        pattern_name = pattern_type.replace("_", " ").title()
        table = Table(title=f"{pattern_name} ({len(patterns)} shown)")
        table.add_column("#", style="cyan", justify="right", width=4)
        table.add_column("Pattern Text", style="white", width=60)
        table.add_column("Category", style="yellow", width=12)
        table.add_column("Confidence", style="green", justify="right", width=10)

        for i, pattern in enumerate(patterns, 1):
            text = pattern.pattern_text[:57] + "..." if len(pattern.pattern_text) > 60 else pattern.pattern_text
            category = pattern.category or "-"
            conf_color = "green" if pattern.confidence >= 0.8 else "yellow" if pattern.confidence >= 0.6 else "red"

            table.add_row(
                str(i),
                text,
                category,
                f"[{conf_color}]{pattern.confidence:.2f}[/{conf_color}]",
            )

        console.print(table)

        # Summary stats
        if patterns:
            avg_conf = sum(p.confidence for p in patterns) / len(patterns)
            console.print(f"\n[dim]Average confidence: {avg_conf:.2f}[/dim]")

    finally:
        db.close()


if __name__ == "__main__":
    app()
