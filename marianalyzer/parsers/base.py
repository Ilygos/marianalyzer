"""Base parser interface for document parsing."""

from abc import ABC, abstractmethod
from pathlib import Path

from marianalyzer.models import ParsedDocument


class BaseParser(ABC):
    """Abstract base class for document parsers."""

    @abstractmethod
    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse a document and return structured content with citations.

        Args:
            file_path: Path to the document file

        Returns:
            ParsedDocument containing metadata, chunks, and headings

        Raises:
            ValueError: If file format is not supported
            FileNotFoundError: If file doesn't exist
        """
        pass

    @abstractmethod
    def supports_format(self, extension: str) -> bool:
        """Check if this parser supports the given file extension.

        Args:
            extension: File extension (e.g., '.pdf', '.docx')

        Returns:
            True if supported, False otherwise
        """
        pass


def get_parser(file_path: Path) -> BaseParser:
    """Get appropriate parser for a file based on extension.

    Args:
        file_path: Path to the file

    Returns:
        Parser instance for the file type

    Raises:
        ValueError: If no parser supports the file type
    """
    from marianalyzer.parsers.docx_parser import DOCXParser
    from marianalyzer.parsers.pdf_parser import PDFParser
    from marianalyzer.parsers.xlsx_parser import XLSXParser

    extension = file_path.suffix.lower()

    parsers = [PDFParser(), DOCXParser(), XLSXParser()]

    for parser in parsers:
        if parser.supports_format(extension):
            return parser

    raise ValueError(f"No parser available for file type: {extension}")
