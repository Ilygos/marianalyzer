"""Recursive folder scanning for document ingestion."""

from pathlib import Path
from typing import List

from marianalyzer.utils.logging_config import get_logger
from marianalyzer.utils.path_utils import is_supported_file

logger = get_logger()


def scan_folder(
    folder_path: Path,
    recursive: bool = True,
) -> List[Path]:
    """Recursively scan folder for supported documents.

    Args:
        folder_path: Root folder to scan
        recursive: Whether to scan subdirectories

    Returns:
        List of paths to supported files

    Raises:
        FileNotFoundError: If folder doesn't exist
        ValueError: If path is not a directory
    """
    if not folder_path.exists():
        raise FileNotFoundError(f"Folder not found: {folder_path}")

    if not folder_path.is_dir():
        raise ValueError(f"Path is not a directory: {folder_path}")

    logger.info(f"Scanning folder: {folder_path} (recursive={recursive})")

    files = []

    if recursive:
        # Use rglob for recursive scanning
        for file_path in folder_path.rglob("*"):
            if file_path.is_file() and is_supported_file(file_path):
                files.append(file_path)
    else:
        # Only scan immediate children
        for file_path in folder_path.glob("*"):
            if file_path.is_file() and is_supported_file(file_path):
                files.append(file_path)

    # Sort for deterministic ordering
    files.sort()

    logger.info(f"Found {len(files)} supported files")

    return files


def filter_by_extension(
    files: List[Path],
    extensions: List[str],
) -> List[Path]:
    """Filter files by extension.

    Args:
        files: List of file paths
        extensions: List of allowed extensions (e.g., ['.pdf', '.docx'])

    Returns:
        Filtered list of files
    """
    extensions_lower = [ext.lower() for ext in extensions]
    return [f for f in files if f.suffix.lower() in extensions_lower]


def get_file_stats(files: List[Path]) -> dict:
    """Get statistics about scanned files.

    Args:
        files: List of file paths

    Returns:
        Dictionary with file statistics
    """
    stats = {
        "total_files": len(files),
        "total_size": sum(f.stat().st_size for f in files),
        "by_extension": {},
    }

    for file in files:
        ext = file.suffix.lower()
        if ext not in stats["by_extension"]:
            stats["by_extension"][ext] = 0
        stats["by_extension"][ext] += 1

    return stats
