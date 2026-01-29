"""Base parser interface."""

from abc import ABC, abstractmethod
from pathlib import Path

from ..models import Chunk, Heading


class Parser(ABC):
    """Base parser interface."""

    @abstractmethod
    def parse(self, file_path: Path, doc_id: str, company_id: str) -> tuple[list[Chunk], list[Heading]]:
        """
        Parse a document and return chunks and headings.
        
        Returns:
            Tuple of (chunks, headings)
        """
        pass
