"""Pytest configuration and fixtures."""

import tempfile
from pathlib import Path

import pytest

from marianalyzer.config import Config, reset_config
from marianalyzer.database import Database


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_db(temp_dir):
    """Create a test database in memory."""
    db_path = temp_dir / "test.db"
    db = Database(db_path)
    db.connect()
    db.create_schema()
    yield db
    db.close()


@pytest.fixture
def test_config(temp_dir):
    """Create a test configuration."""
    reset_config()

    config = Config(
        data_dir=temp_dir / ".rfp_rag",
        ollama_host="http://localhost:11434",
        llm_model="qwen2.5:7b-instruct",
        embed_model="nomic-embed-text",
    )
    config.ensure_directories()

    yield config

    reset_config()


@pytest.fixture
def sample_pdf(temp_dir):
    """Path to sample PDF fixture."""
    # In a real test suite, you would have actual sample files
    # For now, return a placeholder path
    return temp_dir / "sample.pdf"


@pytest.fixture
def sample_docx(temp_dir):
    """Path to sample DOCX fixture."""
    return temp_dir / "sample.docx"


@pytest.fixture
def sample_xlsx(temp_dir):
    """Path to sample XLSX fixture."""
    return temp_dir / "sample.xlsx"


@pytest.fixture
def mock_ollama_client(monkeypatch):
    """Mock Ollama client for testing without Ollama running."""
    from marianalyzer.llm.ollama_client import OllamaClient

    class MockOllamaClient:
        def check_health(self):
            return True

        def generate(self, prompt, model, **kwargs):
            return '{"is_requirement": true, "confidence": 0.9, "modality": "must"}'

        def generate_json(self, prompt, model, **kwargs):
            return {
                "is_requirement": True,
                "req_text": "The system must support HTTPS encryption.",
                "modality": "must",
                "topic": "security",
                "entities": ["HTTPS"],
                "confidence": 0.9,
            }

        def embed(self, texts, model):
            # Return dummy embeddings (768-dimensional)
            return [[0.1] * 768 for _ in texts]

    # Monkeypatch the OllamaClient class
    monkeypatch.setattr("rfp_rag.llm.ollama_client.OllamaClient", MockOllamaClient)

    return MockOllamaClient()
