"""PDF document parser using PyPDF."""

import hashlib
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from marianalyzer.chunking.text_chunker import chunk_text
from marianalyzer.models import Chunk, Document, Heading, ParsedDocument
from marianalyzer.parsers.base import BaseParser
from marianalyzer.utils.citations import format_citation
from marianalyzer.utils.logging_config import get_logger

logger = get_logger()


class PDFParser(BaseParser):
    """Parser for PDF documents."""

    def supports_format(self, extension: str) -> bool:
        """Check if extension is .pdf."""
        return extension.lower() == ".pdf"

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse PDF document.

        Args:
            file_path: Path to PDF file

        Returns:
            ParsedDocument with chunks and metadata
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        logger.info(f"Parsing PDF: {file_path}")

        try:
            reader = PdfReader(str(file_path))

            # Extract metadata
            metadata = self._extract_metadata(reader, file_path)

            # Extract text from each page
            chunks = []
            chunk_index = 0

            for page_num, page in enumerate(reader.pages, start=1):
                text = page.extract_text()

                if not text.strip():
                    continue

                # Chunk the page text
                page_chunks = chunk_text(text)

                for chunk_text_content in page_chunks:
                    citation = format_citation(
                        file_path=str(file_path.name),
                        page=page_num,
                    )

                    chunk = Chunk(
                        doc_id=0,  # Will be set when inserting to DB
                        chunk_index=chunk_index,
                        chunk_text=chunk_text_content,
                        chunk_type="paragraph",
                        citation=citation,
                        metadata={"page": page_num},
                    )
                    chunks.append(chunk)
                    chunk_index += 1

            logger.info(f"Extracted {len(chunks)} chunks from {len(reader.pages)} pages")

            # Create document metadata
            file_hash = self._compute_file_hash(file_path)
            doc = Document(
                file_path=str(file_path.name),
                file_hash=file_hash,
                file_type="pdf",
                file_size=file_path.stat().st_size,
                metadata=metadata,
            )

            return ParsedDocument(
                metadata=doc,
                chunks=chunks,
                headings=[],  # PDF heading extraction not implemented yet
            )

        except Exception as e:
            logger.error(f"Failed to parse PDF {file_path}: {e}")
            raise

    def _extract_metadata(self, reader: PdfReader, file_path: Path) -> dict[str, Any]:
        """Extract PDF metadata."""
        metadata = {
            "num_pages": len(reader.pages),
        }

        if reader.metadata:
            metadata.update({
                "title": reader.metadata.get("/Title", ""),
                "author": reader.metadata.get("/Author", ""),
                "subject": reader.metadata.get("/Subject", ""),
                "creator": reader.metadata.get("/Creator", ""),
            })

        return metadata

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
