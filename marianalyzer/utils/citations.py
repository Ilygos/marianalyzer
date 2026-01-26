"""Citation formatting and validation utilities."""

from typing import Optional

from marianalyzer.models import Citation, Chunk


def format_citation(
    file_path: str,
    page: Optional[int] = None,
    section: Optional[str] = None,
    sheet: Optional[str] = None,
    cell: Optional[str] = None,
) -> str:
    """Format a citation string.

    Args:
        file_path: Path to the source file
        page: Page number (for PDFs)
        section: Section identifier (for DOCX)
        sheet: Sheet name (for XLSX)
        cell: Cell reference (for XLSX)

    Returns:
        Formatted citation string
    """
    citation = Citation(
        file_path=file_path,
        page=page,
        section=section,
        sheet=sheet,
        cell=cell,
    )
    return citation.to_string()


def parse_citation(citation_str: str) -> Citation:
    """Parse a citation string into structured components.

    Args:
        citation_str: Citation string (e.g., "file.pdf#page=5")

    Returns:
        Citation object
    """
    return Citation.from_string(citation_str)


def validate_citation(citation: str, chunks: list[Chunk]) -> bool:
    """Validate that a citation refers to a real chunk.

    Args:
        citation: Citation string to validate
        chunks: List of chunks to check against

    Returns:
        True if citation is valid, False otherwise
    """
    for chunk in chunks:
        if chunk.citation == citation:
            return True
    return False


def get_citation_display_text(citation: str) -> str:
    """Get human-readable text for a citation.

    Args:
        citation: Citation string

    Returns:
        Display text (e.g., "Document.pdf, Page 5")
    """
    parsed = parse_citation(citation)

    if parsed.page is not None:
        return f"{parsed.file_path}, Page {parsed.page}"
    elif parsed.section is not None:
        return f"{parsed.file_path}, Section {parsed.section}"
    elif parsed.sheet is not None and parsed.cell is not None:
        return f"{parsed.file_path}, {parsed.sheet} Cell {parsed.cell}"
    else:
        return parsed.file_path
