"""Pydantic models for domain objects."""

from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field


class Document(BaseModel):
    """Represents a source document."""

    id: Optional[int] = None
    file_path: str
    file_hash: str
    file_type: str  # 'pdf', 'docx', 'xlsx'
    file_size: int
    ingested_at: Optional[datetime] = None
    metadata: Optional[dict[str, Any]] = None
    status: str = "indexed"


class Chunk(BaseModel):
    """Represents a text chunk from a document."""

    id: Optional[int] = None
    doc_id: int
    chunk_index: int
    chunk_text: str
    chunk_type: str  # 'paragraph', 'table_row', 'heading'
    citation: str
    metadata: Optional[dict[str, Any]] = None
    created_at: Optional[datetime] = None


class Heading(BaseModel):
    """Represents a document heading for structure context."""

    id: Optional[int] = None
    doc_id: int
    level: int  # 1=H1, 2=H2, etc.
    heading_text: str
    heading_number: Optional[str] = None
    page_or_location: Optional[str] = None


class Requirement(BaseModel):
    """Represents an extracted requirement."""

    id: Optional[int] = None
    chunk_id: int
    req_text: str
    req_norm: str  # Normalized for clustering
    modality: Optional[str] = None  # 'must', 'should', 'may'
    topic: Optional[str] = None
    entities: Optional[list[str]] = None
    confidence: float
    extracted_at: Optional[datetime] = None


class RequirementFamily(BaseModel):
    """Represents a cluster of similar requirements."""

    id: Optional[int] = None
    canonical_text: str
    member_count: int
    doc_count: int  # Number of distinct documents
    created_at: Optional[datetime] = None


class RequirementFamilyMember(BaseModel):
    """Links a requirement to its family."""

    id: Optional[int] = None
    family_id: int
    requirement_id: int
    similarity_score: Optional[float] = None


class ParsedDocument(BaseModel):
    """Result of parsing a document."""

    metadata: Document
    chunks: list[Chunk]
    headings: list[Heading] = []


class Citation(BaseModel):
    """Structured citation to a source location."""

    file_path: str
    page: Optional[int] = None
    section: Optional[str] = None
    sheet: Optional[str] = None
    cell: Optional[str] = None

    def to_string(self) -> str:
        """Format as citation string."""
        if self.page is not None:
            return f"{self.file_path}#page={self.page}"
        elif self.section is not None:
            return f"{self.file_path}#section={self.section}"
        elif self.sheet is not None and self.cell is not None:
            return f"{self.file_path}#{self.sheet}!{self.cell}"
        else:
            return self.file_path

    @classmethod
    def from_string(cls, citation_str: str) -> "Citation":
        """Parse citation string back to structured format."""
        if "#" not in citation_str:
            return cls(file_path=citation_str)

        file_path, location = citation_str.split("#", 1)

        if location.startswith("page="):
            page_num = int(location.split("=")[1])
            return cls(file_path=file_path, page=page_num)
        elif location.startswith("section="):
            section = location.split("=")[1]
            return cls(file_path=file_path, section=section)
        elif "!" in location:
            sheet, cell = location.split("!", 1)
            return cls(file_path=file_path, sheet=sheet, cell=cell)
        else:
            return cls(file_path=file_path)


class ExtractionResult(BaseModel):
    """Result of requirement extraction from a chunk."""

    is_requirement: bool
    req_text: Optional[str] = None
    modality: Optional[str] = None
    topic: Optional[str] = None
    entities: Optional[list[str]] = None
    confidence: float = 0.0


class Pattern(BaseModel):
    """Generic pattern extracted from documents (requirements, success points, risks, etc.)."""

    id: Optional[int] = None
    chunk_id: int
    pattern_type: str  # 'requirement', 'success_point', 'failure_point', 'risk', 'constraint'
    pattern_text: str
    pattern_norm: str  # Normalized for clustering
    category: Optional[str] = None  # Type-specific categorization
    severity: Optional[str] = None  # For risks/failures: 'high', 'medium', 'low'
    modality: Optional[str] = None  # For requirements: 'must', 'should', 'may'
    topic: Optional[str] = None
    entities: Optional[list[str]] = None
    confidence: float
    metadata: Optional[dict[str, Any]] = None
    extracted_at: Optional[datetime] = None


class PatternFamily(BaseModel):
    """Represents a cluster of similar patterns."""

    id: Optional[int] = None
    pattern_type: str
    canonical_text: str
    member_count: int
    doc_count: int
    average_confidence: Optional[float] = None
    created_at: Optional[datetime] = None


class PatternFamilyMember(BaseModel):
    """Links a pattern to its family."""

    id: Optional[int] = None
    family_id: int
    pattern_id: int
    similarity_score: Optional[float] = None


class QueryResponse(BaseModel):
    """Structured response to a user query."""

    query: str
    answer: str
    evidence: list[dict[str, Any]]  # List of {chunk_text, citation, relevance_score}
    metadata: Optional[dict[str, Any]] = None
