"""Table chunking utilities."""

from typing import List, Optional


def chunk_table_rows(
    rows: List[List[str]],
    headers: Optional[List[str]] = None,
    include_headers: bool = True,
) -> List[str]:
    """Chunk table data by rows.

    Each row becomes a separate chunk, with headers included for context.

    Args:
        rows: List of table rows (each row is a list of cell values)
        headers: Optional list of column headers
        include_headers: Whether to include headers in each chunk

    Returns:
        List of row text chunks
    """
    chunks = []

    # Use first row as headers if not provided
    if headers is None and rows:
        headers = rows[0]
        rows = rows[1:]

    for row in rows:
        # Skip empty rows
        if not any(cell.strip() for cell in row if cell):
            continue

        if include_headers and headers:
            # Create key-value pairs
            row_text = " | ".join(
                f"{h}: {v}"
                for h, v in zip(headers, row)
                if v and v.strip()
            )
        else:
            # Just join cell values
            row_text = " | ".join(v for v in row if v and v.strip())

        if row_text:
            chunks.append(row_text)

    return chunks


def format_table_chunk(
    headers: List[str],
    row_data: List[str],
    table_caption: Optional[str] = None,
) -> str:
    """Format a table row as a text chunk.

    Args:
        headers: Column headers
        row_data: Row cell values
        table_caption: Optional table caption

    Returns:
        Formatted text chunk
    """
    parts = []

    if table_caption:
        parts.append(f"Table: {table_caption}")

    # Create key-value pairs
    row_pairs = [
        f"{h}: {v}"
        for h, v in zip(headers, row_data)
        if v and v.strip()
    ]

    if row_pairs:
        parts.append(" | ".join(row_pairs))

    return " - ".join(parts) if parts else ""
