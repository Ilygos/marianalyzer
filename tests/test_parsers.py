"""Tests for document parsers."""

import pytest

from marianalyzer.chunking.text_chunker import chunk_text, split_into_sentences


def test_split_into_sentences():
    """Test sentence splitting."""
    text = "This is sentence one. This is sentence two! This is sentence three?"
    sentences = split_into_sentences(text)

    assert len(sentences) == 3
    assert "sentence one" in sentences[0]
    assert "sentence two" in sentences[1]
    assert "sentence three" in sentences[2]


def test_chunk_text_basic():
    """Test basic text chunking."""
    text = " ".join(["Word"] * 100)  # 100 words
    chunks = chunk_text(text, chunk_size=30, overlap=10)

    # Should create multiple chunks
    assert len(chunks) > 1

    # Each chunk should be reasonable size
    for chunk in chunks:
        word_count = len(chunk.split())
        assert word_count > 0
        assert word_count <= 50  # Allow some flexibility


def test_chunk_text_short():
    """Test chunking short text."""
    text = "Short text."
    chunks = chunk_text(text, chunk_size=100)

    # Short text should be single chunk
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_empty():
    """Test chunking empty text."""
    chunks = chunk_text("")

    assert len(chunks) == 0


class TestBaseParser:
    """Tests for base parser functionality."""

    def test_get_parser_pdf(self, temp_dir):
        """Test getting PDF parser."""
        from marianalyzer.parsers.base import get_parser

        pdf_path = temp_dir / "test.pdf"
        pdf_path.touch()

        parser = get_parser(pdf_path)

        assert parser is not None
        assert parser.supports_format(".pdf")

    def test_get_parser_docx(self, temp_dir):
        """Test getting DOCX parser."""
        from marianalyzer.parsers.base import get_parser

        docx_path = temp_dir / "test.docx"
        docx_path.touch()

        parser = get_parser(docx_path)

        assert parser is not None
        assert parser.supports_format(".docx")

    def test_get_parser_xlsx(self, temp_dir):
        """Test getting XLSX parser."""
        from marianalyzer.parsers.base import get_parser

        xlsx_path = temp_dir / "test.xlsx"
        xlsx_path.touch()

        parser = get_parser(xlsx_path)

        assert parser is not None
        assert parser.supports_format(".xlsx")

    def test_get_parser_unsupported(self, temp_dir):
        """Test unsupported file type."""
        from marianalyzer.parsers.base import get_parser

        txt_path = temp_dir / "test.txt"
        txt_path.touch()

        with pytest.raises(ValueError, match="No parser available"):
            get_parser(txt_path)


class TestDatabase:
    """Tests for database operations."""

    def test_database_connection(self, test_db):
        """Test database connection."""
        assert test_db.conn is not None

    def test_insert_document(self, test_db):
        """Test inserting a document."""
        from marianalyzer.models import Document

        doc = Document(
            file_path="test.pdf",
            file_hash="abc123",
            file_type="pdf",
            file_size=1024,
        )

        doc_id = test_db.insert_document(doc)

        assert doc_id is not None
        assert doc_id > 0

    def test_get_document_by_path(self, test_db):
        """Test retrieving document by path."""
        from marianalyzer.models import Document

        doc = Document(
            file_path="test.pdf",
            file_hash="abc123",
            file_type="pdf",
            file_size=1024,
        )

        test_db.insert_document(doc)

        retrieved = test_db.get_document_by_path("test.pdf")

        assert retrieved is not None
        assert retrieved.file_path == "test.pdf"
        assert retrieved.file_hash == "abc123"

    def test_count_documents(self, test_db):
        """Test counting documents."""
        from marianalyzer.models import Document

        assert test_db.count_documents() == 0

        doc = Document(
            file_path="test.pdf",
            file_hash="abc123",
            file_type="pdf",
            file_size=1024,
        )

        test_db.insert_document(doc)

        assert test_db.count_documents() == 1
