"""Pipelines for document processing."""

from .ingest import ingest_documents
from .index import build_index
from .extract import extract_requirements
from .aggregate import build_playbook

__all__ = [
    "ingest_documents",
    "build_index",
    "extract_requirements",
    "build_playbook",
]
