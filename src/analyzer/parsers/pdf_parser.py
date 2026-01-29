"""PDF parser implementation."""

import hashlib
from pathlib import Path

from pypdf import PdfReader

from ..models import Chunk, ChunkType, Heading, Locator
from .base import Parser


class PDFParser(Parser):
    """Parser for PDF files."""

    def parse(self, file_path: Path, doc_id: str, company_id: str) -> tuple[list[Chunk], list[Heading]]:
        """Parse a PDF file."""
        reader = PdfReader(str(file_path))
        chunks: list[Chunk] = []
        headings: list[Heading] = []

        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text()
            
            if not text or not text.strip():
                continue

            # Create chunk for page
            chunk_id = hashlib.md5(
                f"{doc_id}:page:{page_num}".encode()
            ).hexdigest()[:16]
            
            chunk = Chunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                company_id=company_id,
                chunk_type=ChunkType.PAGE_BLOCK,
                text=text.strip(),
                structure_path=[f"Page {page_num}"],
                locator=Locator(page=page_num),
            )
            chunks.append(chunk)

        # Try to extract outline/bookmarks as headings
        if reader.outline:
            self._extract_outline_headings(reader.outline, doc_id, company_id, headings)

        return chunks, headings

    def _extract_outline_headings(
        self,
        outline,
        doc_id: str,
        company_id: str,
        headings: list[Heading],
        level: int = 1,
    ) -> None:
        """Extract headings from PDF outline/bookmarks."""
        for item in outline:
            if isinstance(item, list):
                self._extract_outline_headings(item, doc_id, company_id, headings, level + 1)
            else:
                title = item.title if hasattr(item, "title") else str(item)
                page = None
                
                if hasattr(item, "page"):
                    page_obj = item.page
                    if page_obj:
                        # Get page number
                        page = page_obj.page_number if hasattr(page_obj, "page_number") else None

                heading_id = hashlib.md5(
                    f"{doc_id}:outline:{title}:{level}".encode()
                ).hexdigest()[:16]
                
                heading = Heading(
                    heading_id=heading_id,
                    doc_id=doc_id,
                    company_id=company_id,
                    heading_text=title,
                    heading_norm=title.lower().replace(" ", "_"),
                    level=level,
                    locator=Locator(page=page) if page else Locator(),
                )
                headings.append(heading)
