"""Base data models for the analyzer."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ChunkType(str, Enum):
    """Type of chunk."""
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    SHEET_RANGE = "sheet_range"
    PAGE_BLOCK = "page_block"


class Locator(BaseModel):
    """Location information for a chunk."""
    page: Optional[int] = None
    sheet: Optional[str] = None
    cell_range: Optional[str] = None
    paragraph_index: Optional[int] = None
    line_number: Optional[int] = None


class Document(BaseModel):
    """Document metadata."""
    doc_id: str
    company_id: str
    path: str
    type: str  # pdf, docx, xlsx
    sha256: str
    mtime: float
    size: int
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Chunk(BaseModel):
    """Canonical chunk representation."""
    chunk_id: str
    doc_id: str
    company_id: str
    chunk_type: ChunkType
    text: str
    structure_path: list[str] = Field(default_factory=list)
    locator: Locator
    raw_table: Optional[list[list[str]]] = None  # For table chunks


class Heading(BaseModel):
    """Heading extracted from document."""
    heading_id: str
    doc_id: str
    company_id: str
    heading_text: str
    heading_norm: str  # Normalized for comparison
    level: int
    locator: Locator


class Requirement(BaseModel):
    """Extracted requirement."""
    req_id: str
    doc_id: str
    chunk_id: str
    company_id: str
    req_text: str
    modality: str  # must, shall, should, required, etc.
    topic: Optional[str] = None
    entities: list[str] = Field(default_factory=list)
    req_norm: str  # Normalized for clustering
    confidence: float = 1.0
    evidence: dict[str, Any] = Field(default_factory=dict)


class RequirementFamily(BaseModel):
    """Clustered requirement family."""
    family_id: str
    company_id: str
    title: str
    canonical_text: str
    member_count: int = 0
    embedding: Optional[list[float]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class GlossaryEntry(BaseModel):
    """Glossary term entry."""
    company_id: str
    term: str
    preferred_term: str
    notes: Optional[str] = None
    frequency: int = 0


class PlaybookSection(BaseModel):
    """Section in the company playbook."""
    section_name: str
    frequency: float  # How often it appears (0-1)
    required: bool
    typical_subsections: list[str] = Field(default_factory=list)


class Playbook(BaseModel):
    """Company playbook."""
    company_id: str
    doc_type: str
    typical_outline: list[PlaybookSection] = Field(default_factory=list)
    top_requirement_families: list[str] = Field(default_factory=list)  # family_ids
    glossary_terms: list[str] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# MCP Response Models

class EvidenceExample(BaseModel):
    """Example citation for evidence."""
    path: str
    locator: dict[str, Any]
    chunk_id: str


class Evidence(BaseModel):
    """Evidence for a validation issue."""
    family_id: str
    canonical_text: str
    examples: list[EvidenceExample] = Field(default_factory=list)


class ValidationIssue(BaseModel):
    """Validation issue found in draft."""
    severity: str  # high, medium, low
    type: str  # missing_section, missing_requirement, terminology, consistency, specificity
    message: str
    recommended_fix: Optional[str] = None
    evidence: list[Evidence] = Field(default_factory=list)


class ValidationResponse(BaseModel):
    """Response from validate_draft tool."""
    company_id: str
    doc_type: str
    issues: list[ValidationIssue] = Field(default_factory=list)


class ScoreResponse(BaseModel):
    """Response from score_draft tool."""
    company_id: str
    doc_type: str
    scores: dict[str, float] = Field(default_factory=dict)
    missing: dict[str, list[str]] = Field(default_factory=dict)
