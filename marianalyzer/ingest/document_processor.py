"""Document processing and ingestion."""

from pathlib import Path

from marianalyzer.database import Database
from marianalyzer.models import ParsedDocument
from marianalyzer.parsers.base import get_parser
from marianalyzer.utils.logging_config import get_logger

logger = get_logger()


def process_document(
    file_path: Path,
    db: Database,
    root_folder: Path,
) -> bool:
    """Process a single document and insert into database.

    Args:
        file_path: Path to document
        db: Database instance
        root_folder: Root ingestion folder (for relative paths)

    Returns:
        True if successful, False otherwise
    """
    try:
        # Get relative path for storage
        try:
            relative_path = file_path.relative_to(root_folder)
        except ValueError:
            # If not relative to root, use filename only
            relative_path = file_path.name

        relative_path_str = str(relative_path)

        # Check if already ingested
        existing_doc = db.get_document_by_path(relative_path_str)
        if existing_doc:
            logger.info(f"Document already ingested: {relative_path_str}")
            return True

        logger.info(f"Processing: {file_path}")

        # Parse document
        parser = get_parser(file_path)
        parsed: ParsedDocument = parser.parse(file_path)

        # Update paths to be relative
        parsed.metadata.file_path = relative_path_str

        # Insert into database
        with db.transaction():
            doc_id = db.insert_document(parsed.metadata)

            # Update chunk doc_ids
            for chunk in parsed.chunks:
                chunk.doc_id = doc_id

            # Update heading doc_ids
            for heading in parsed.headings:
                heading.doc_id = doc_id

            # Insert chunks and headings
            if parsed.chunks:
                db.insert_chunks(parsed.chunks)

            if parsed.headings:
                db.insert_headings(parsed.headings)

        logger.info(
            f"Successfully processed {relative_path_str}: "
            f"{len(parsed.chunks)} chunks, {len(parsed.headings)} headings"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to process {file_path}: {e}", exc_info=True)

        # Try to mark as failed in DB
        try:
            db.update_document_status(relative_path_str, "failed")
        except Exception:
            pass

        return False


def ingest_folder(
    folder_path: Path,
    db: Database,
    recursive: bool = True,
) -> dict:
    """Ingest all documents in a folder.

    Args:
        folder_path: Root folder to ingest
        db: Database instance
        recursive: Whether to scan subdirectories

    Returns:
        Dictionary with ingestion statistics
    """
    from marianalyzer.ingest.scanner import scan_folder

    logger.info(f"Starting ingestion from: {folder_path}")

    # Scan for files
    files = scan_folder(folder_path, recursive=recursive)

    # Process each file
    stats = {
        "total_files": len(files),
        "successful": 0,
        "failed": 0,
        "skipped": 0,
    }

    for file_path in files:
        success = process_document(file_path, db, folder_path)

        if success:
            stats["successful"] += 1
        else:
            stats["failed"] += 1

    logger.info(
        f"Ingestion complete: {stats['successful']}/{stats['total_files']} successful, "
        f"{stats['failed']} failed"
    )

    return stats
