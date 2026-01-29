"""Basic tests to ensure imports work."""

import pytest


def test_imports():
    """Test that all main modules can be imported."""
    from analyzer import get_config
    from analyzer.models import Document, Chunk, Requirement, Playbook
    from analyzer.store import SQLiteStore, ChromaStore
    from analyzer.parsers import DOCXParser, XLSXParser, PDFParser
    
    assert get_config is not None


def test_config():
    """Test configuration."""
    from analyzer import get_config
    
    config = get_config()
    assert config.ollama_host == "http://localhost:11434"
    assert config.ollama_llm_model == "qwen2.5:7b-instruct"


def test_models():
    """Test model instantiation."""
    from analyzer.models import Document, Locator
    from datetime import datetime
    
    doc = Document(
        doc_id="test123",
        company_id="acme",
        path="test.pdf",
        type="pdf",
        sha256="abc123",
        mtime=123.45,
        size=1000,
        created_at=datetime.utcnow(),
    )
    
    assert doc.doc_id == "test123"
    assert doc.company_id == "acme"
