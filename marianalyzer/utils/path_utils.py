"""Cross-platform path utilities."""

import platform
from pathlib import Path
from typing import Union


def normalize_path(path: Union[str, Path]) -> Path:
    """Convert to Path object with resolved separators."""
    return Path(path).resolve()


def relative_to_root(path: Path, root: Path) -> Path:
    """Get relative path from root, handling cross-platform differences."""
    try:
        return path.relative_to(root)
    except ValueError:
        # If path is not relative to root, return absolute
        return path.resolve()


def ensure_dir_exists(path: Path) -> None:
    """Create directory if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)


def is_supported_file(path: Path) -> bool:
    """Check if file extension is supported."""
    supported_extensions = {".pdf", ".docx", ".xlsx"}
    return path.suffix.lower() in supported_extensions


def get_file_type(path: Path) -> str:
    """Get file type from extension."""
    extension = path.suffix.lower()
    type_mapping = {
        ".pdf": "pdf",
        ".docx": "docx",
        ".xlsx": "xlsx",
    }
    return type_mapping.get(extension, "unknown")


def get_platform_info() -> dict[str, str]:
    """Get platform information for logging."""
    return {
        "system": platform.system(),
        "machine": platform.machine(),
        "python_version": platform.python_version(),
    }
