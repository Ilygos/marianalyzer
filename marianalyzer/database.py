"""SQLite database management and CRUD operations."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional

from marianalyzer.models import (
    Chunk,
    Document,
    Heading,
    Pattern,
    PatternFamily,
    PatternFamilyMember,
    Requirement,
    RequirementFamily,
    RequirementFamilyMember,
)
from marianalyzer.utils.logging_config import get_logger

logger = get_logger()


# Schema SQL
SCHEMA_SQL = """
-- documents: Source files
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL UNIQUE,
    file_hash TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,
    status TEXT DEFAULT 'indexed'
);

CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(file_hash);
CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(file_type);

-- chunks: Parsed content segments
CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_type TEXT NOT NULL,
    citation TEXT NOT NULL,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_chunks_type ON chunks(chunk_type);

-- headings: Document structure
CREATE TABLE IF NOT EXISTS headings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id INTEGER NOT NULL,
    level INTEGER NOT NULL,
    heading_text TEXT NOT NULL,
    heading_number TEXT,
    page_or_location TEXT,
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_headings_doc_id ON headings(doc_id);

-- requirements: Extracted requirements
CREATE TABLE IF NOT EXISTS requirements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chunk_id INTEGER NOT NULL,
    req_text TEXT NOT NULL,
    req_norm TEXT NOT NULL,
    modality TEXT,
    topic TEXT,
    entities TEXT,
    confidence REAL NOT NULL,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_requirements_chunk_id ON requirements(chunk_id);
CREATE INDEX IF NOT EXISTS idx_requirements_modality ON requirements(modality);
CREATE INDEX IF NOT EXISTS idx_requirements_confidence ON requirements(confidence);

-- req_families: Clustered requirement groups
CREATE TABLE IF NOT EXISTS req_families (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_text TEXT NOT NULL,
    member_count INTEGER NOT NULL,
    doc_count INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_req_families_doc_count ON req_families(doc_count DESC);

-- req_family_members: Many-to-many relationship
CREATE TABLE IF NOT EXISTS req_family_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    family_id INTEGER NOT NULL,
    requirement_id INTEGER NOT NULL,
    similarity_score REAL,
    FOREIGN KEY (family_id) REFERENCES req_families(id) ON DELETE CASCADE,
    FOREIGN KEY (requirement_id) REFERENCES requirements(id) ON DELETE CASCADE,
    UNIQUE(family_id, requirement_id)
);

CREATE INDEX IF NOT EXISTS idx_req_family_members_family ON req_family_members(family_id);
CREATE INDEX IF NOT EXISTS idx_req_family_members_requirement ON req_family_members(requirement_id);

-- patterns: Generic pattern extraction (success, failure, risk, etc.)
CREATE TABLE IF NOT EXISTS patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chunk_id INTEGER NOT NULL,
    pattern_type TEXT NOT NULL,
    pattern_text TEXT NOT NULL,
    pattern_norm TEXT NOT NULL,
    category TEXT,
    severity TEXT,
    modality TEXT,
    topic TEXT,
    entities TEXT,
    confidence REAL NOT NULL,
    metadata TEXT,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_patterns_chunk_id ON patterns(chunk_id);
CREATE INDEX IF NOT EXISTS idx_patterns_type ON patterns(pattern_type);
CREATE INDEX IF NOT EXISTS idx_patterns_confidence ON patterns(confidence);
CREATE INDEX IF NOT EXISTS idx_patterns_category ON patterns(category);

-- pattern_families: Clustered pattern groups
CREATE TABLE IF NOT EXISTS pattern_families (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_type TEXT NOT NULL,
    canonical_text TEXT NOT NULL,
    member_count INTEGER NOT NULL,
    doc_count INTEGER NOT NULL,
    average_confidence REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pattern_families_type ON pattern_families(pattern_type);
CREATE INDEX IF NOT EXISTS idx_pattern_families_doc_count ON pattern_families(doc_count DESC);

-- pattern_family_members: Many-to-many relationship
CREATE TABLE IF NOT EXISTS pattern_family_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    family_id INTEGER NOT NULL,
    pattern_id INTEGER NOT NULL,
    similarity_score REAL,
    FOREIGN KEY (family_id) REFERENCES pattern_families(id) ON DELETE CASCADE,
    FOREIGN KEY (pattern_id) REFERENCES patterns(id) ON DELETE CASCADE,
    UNIQUE(family_id, pattern_id)
);

CREATE INDEX IF NOT EXISTS idx_pattern_family_members_family ON pattern_family_members(family_id);
CREATE INDEX IF NOT EXISTS idx_pattern_family_members_pattern ON pattern_family_members(pattern_id);
"""


class Database:
    """SQLite database manager with CRUD operations."""

    def __init__(self, db_path: Path):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self) -> None:
        """Establish database connection with foreign keys enabled."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.row_factory = sqlite3.Row
        logger.info(f"Connected to database: {self.db_path}")

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("Database connection closed")

    def create_schema(self) -> None:
        """Create database schema."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        self.conn.executescript(SCHEMA_SQL)
        self.conn.commit()
        logger.info("Database schema created")

    @contextmanager
    def transaction(self) -> Generator[None, None, None]:
        """Context manager for database transactions."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        try:
            yield
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    # Document operations
    def insert_document(self, doc: Document) -> int:
        """Insert a document and return its ID."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        metadata_json = json.dumps(doc.metadata) if doc.metadata else None

        cursor = self.conn.execute(
            """
            INSERT INTO documents (file_path, file_hash, file_type, file_size, metadata, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (doc.file_path, doc.file_hash, doc.file_type, doc.file_size, metadata_json, doc.status),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_document_by_path(self, path: str) -> Optional[Document]:
        """Get document by file path."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        cursor = self.conn.execute("SELECT * FROM documents WHERE file_path = ?", (path,))
        row = cursor.fetchone()

        if row:
            return Document(
                id=row["id"],
                file_path=row["file_path"],
                file_hash=row["file_hash"],
                file_type=row["file_type"],
                file_size=row["file_size"],
                ingested_at=datetime.fromisoformat(row["ingested_at"]) if row["ingested_at"] else None,
                metadata=json.loads(row["metadata"]) if row["metadata"] else None,
                status=row["status"],
            )
        return None

    def get_document_by_hash(self, file_hash: str) -> Optional[Document]:
        """Get document by hash."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        cursor = self.conn.execute("SELECT * FROM documents WHERE file_hash = ?", (file_hash,))
        row = cursor.fetchone()

        if row:
            return Document(
                id=row["id"],
                file_path=row["file_path"],
                file_hash=row["file_hash"],
                file_type=row["file_type"],
                file_size=row["file_size"],
                ingested_at=datetime.fromisoformat(row["ingested_at"]) if row["ingested_at"] else None,
                metadata=json.loads(row["metadata"]) if row["metadata"] else None,
                status=row["status"],
            )
        return None

    def count_documents(self) -> int:
        """Count total documents."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        cursor = self.conn.execute("SELECT COUNT(*) FROM documents")
        return cursor.fetchone()[0]

    def update_document_status(self, file_path: str, status: str) -> None:
        """Update document status."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        self.conn.execute("UPDATE documents SET status = ? WHERE file_path = ?", (status, file_path))
        self.conn.commit()

    # Chunk operations
    def insert_chunks(self, chunks: list[Chunk]) -> None:
        """Insert multiple chunks."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        chunk_data = [
            (
                c.doc_id,
                c.chunk_index,
                c.chunk_text,
                c.chunk_type,
                c.citation,
                json.dumps(c.metadata) if c.metadata else None,
            )
            for c in chunks
        ]

        self.conn.executemany(
            """
            INSERT INTO chunks (doc_id, chunk_index, chunk_text, chunk_type, citation, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            chunk_data,
        )
        self.conn.commit()

    def get_chunks_by_doc(self, doc_id: int) -> list[Chunk]:
        """Get all chunks for a document."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        cursor = self.conn.execute(
            "SELECT * FROM chunks WHERE doc_id = ? ORDER BY chunk_index",
            (doc_id,),
        )
        rows = cursor.fetchall()

        return [
            Chunk(
                id=row["id"],
                doc_id=row["doc_id"],
                chunk_index=row["chunk_index"],
                chunk_text=row["chunk_text"],
                chunk_type=row["chunk_type"],
                citation=row["citation"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else None,
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            )
            for row in rows
        ]

    def get_all_chunks(self) -> list[Chunk]:
        """Get all chunks from database."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        cursor = self.conn.execute("SELECT * FROM chunks ORDER BY id")
        rows = cursor.fetchall()

        return [
            Chunk(
                id=row["id"],
                doc_id=row["doc_id"],
                chunk_index=row["chunk_index"],
                chunk_text=row["chunk_text"],
                chunk_type=row["chunk_type"],
                citation=row["citation"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else None,
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            )
            for row in rows
        ]

    def count_chunks(self) -> int:
        """Count total chunks."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        cursor = self.conn.execute("SELECT COUNT(*) FROM chunks")
        return cursor.fetchone()[0]

    # Heading operations
    def insert_headings(self, headings: list[Heading]) -> None:
        """Insert multiple headings."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        heading_data = [
            (h.doc_id, h.level, h.heading_text, h.heading_number, h.page_or_location)
            for h in headings
        ]

        self.conn.executemany(
            """
            INSERT INTO headings (doc_id, level, heading_text, heading_number, page_or_location)
            VALUES (?, ?, ?, ?, ?)
            """,
            heading_data,
        )
        self.conn.commit()

    # Requirement operations
    def insert_requirement(self, req: Requirement) -> int:
        """Insert a requirement and return its ID."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        entities_json = json.dumps(req.entities) if req.entities else None

        cursor = self.conn.execute(
            """
            INSERT INTO requirements (chunk_id, req_text, req_norm, modality, topic, entities, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (req.chunk_id, req.req_text, req.req_norm, req.modality, req.topic, entities_json, req.confidence),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_all_requirements(self) -> list[Requirement]:
        """Get all requirements."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        cursor = self.conn.execute("SELECT * FROM requirements ORDER BY id")
        rows = cursor.fetchall()

        return [
            Requirement(
                id=row["id"],
                chunk_id=row["chunk_id"],
                req_text=row["req_text"],
                req_norm=row["req_norm"],
                modality=row["modality"],
                topic=row["topic"],
                entities=json.loads(row["entities"]) if row["entities"] else None,
                confidence=row["confidence"],
                extracted_at=datetime.fromisoformat(row["extracted_at"]) if row["extracted_at"] else None,
            )
            for row in rows
        ]

    def count_requirements(self) -> int:
        """Count total requirements."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        cursor = self.conn.execute("SELECT COUNT(*) FROM requirements")
        return cursor.fetchone()[0]

    # Family operations
    def insert_family(self, family: RequirementFamily) -> int:
        """Insert a requirement family and return its ID."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        cursor = self.conn.execute(
            """
            INSERT INTO req_families (canonical_text, member_count, doc_count)
            VALUES (?, ?, ?)
            """,
            (family.canonical_text, family.member_count, family.doc_count),
        )
        self.conn.commit()
        return cursor.lastrowid

    def insert_family_members(self, members: list[RequirementFamilyMember]) -> None:
        """Insert family members."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        member_data = [
            (m.family_id, m.requirement_id, m.similarity_score)
            for m in members
        ]

        self.conn.executemany(
            """
            INSERT INTO req_family_members (family_id, requirement_id, similarity_score)
            VALUES (?, ?, ?)
            """,
            member_data,
        )
        self.conn.commit()

    def get_top_families(self, limit: int = 20) -> list[RequirementFamily]:
        """Get top requirement families by document count."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        cursor = self.conn.execute(
            "SELECT * FROM req_families ORDER BY doc_count DESC, member_count DESC LIMIT ?",
            (limit,),
        )
        rows = cursor.fetchall()

        return [
            RequirementFamily(
                id=row["id"],
                canonical_text=row["canonical_text"],
                member_count=row["member_count"],
                doc_count=row["doc_count"],
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            )
            for row in rows
        ]

    def count_families(self) -> int:
        """Count total families."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        cursor = self.conn.execute("SELECT COUNT(*) FROM req_families")
        return cursor.fetchone()[0]

    # Pattern operations (generic for all pattern types)
    def insert_pattern(self, pattern: Pattern) -> int:
        """Insert a pattern and return its ID."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        entities_json = json.dumps(pattern.entities) if pattern.entities else None
        metadata_json = json.dumps(pattern.metadata) if pattern.metadata else None

        cursor = self.conn.execute(
            """
            INSERT INTO patterns (
                chunk_id, pattern_type, pattern_text, pattern_norm,
                category, severity, modality, topic, entities, confidence, metadata
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pattern.chunk_id,
                pattern.pattern_type,
                pattern.pattern_text,
                pattern.pattern_norm,
                pattern.category,
                pattern.severity,
                pattern.modality,
                pattern.topic,
                entities_json,
                pattern.confidence,
                metadata_json,
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_patterns_by_type(self, pattern_type: str) -> list[Pattern]:
        """Get all patterns of a specific type."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        cursor = self.conn.execute(
            "SELECT * FROM patterns WHERE pattern_type = ? ORDER BY id",
            (pattern_type,),
        )
        rows = cursor.fetchall()

        return [
            Pattern(
                id=row["id"],
                chunk_id=row["chunk_id"],
                pattern_type=row["pattern_type"],
                pattern_text=row["pattern_text"],
                pattern_norm=row["pattern_norm"],
                category=row["category"],
                severity=row["severity"],
                modality=row["modality"],
                topic=row["topic"],
                entities=json.loads(row["entities"]) if row["entities"] else None,
                confidence=row["confidence"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else None,
                extracted_at=datetime.fromisoformat(row["extracted_at"]) if row["extracted_at"] else None,
            )
            for row in rows
        ]

    def get_all_patterns(self) -> list[Pattern]:
        """Get all patterns."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        cursor = self.conn.execute("SELECT * FROM patterns ORDER BY id")
        rows = cursor.fetchall()

        return [
            Pattern(
                id=row["id"],
                chunk_id=row["chunk_id"],
                pattern_type=row["pattern_type"],
                pattern_text=row["pattern_text"],
                pattern_norm=row["pattern_norm"],
                category=row["category"],
                severity=row["severity"],
                modality=row["modality"],
                topic=row["topic"],
                entities=json.loads(row["entities"]) if row["entities"] else None,
                confidence=row["confidence"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else None,
                extracted_at=datetime.fromisoformat(row["extracted_at"]) if row["extracted_at"] else None,
            )
            for row in rows
        ]

    def count_patterns(self, pattern_type: Optional[str] = None) -> int:
        """Count patterns, optionally filtered by type."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        if pattern_type:
            cursor = self.conn.execute(
                "SELECT COUNT(*) FROM patterns WHERE pattern_type = ?",
                (pattern_type,),
            )
        else:
            cursor = self.conn.execute("SELECT COUNT(*) FROM patterns")

        return cursor.fetchone()[0]

    # Pattern family operations
    def insert_pattern_family(self, family: PatternFamily) -> int:
        """Insert a pattern family and return its ID."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        cursor = self.conn.execute(
            """
            INSERT INTO pattern_families (
                pattern_type, canonical_text, member_count, doc_count, average_confidence
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                family.pattern_type,
                family.canonical_text,
                family.member_count,
                family.doc_count,
                family.average_confidence,
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def insert_pattern_family_members(self, members: list[PatternFamilyMember]) -> None:
        """Insert pattern family members."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        member_data = [(m.family_id, m.pattern_id, m.similarity_score) for m in members]

        self.conn.executemany(
            """
            INSERT INTO pattern_family_members (family_id, pattern_id, similarity_score)
            VALUES (?, ?, ?)
            """,
            member_data,
        )
        self.conn.commit()

    def get_top_pattern_families(
        self, pattern_type: str, limit: int = 20
    ) -> list[PatternFamily]:
        """Get top pattern families by document count."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        cursor = self.conn.execute(
            """
            SELECT * FROM pattern_families
            WHERE pattern_type = ?
            ORDER BY doc_count DESC, member_count DESC
            LIMIT ?
            """,
            (pattern_type, limit),
        )
        rows = cursor.fetchall()

        return [
            PatternFamily(
                id=row["id"],
                pattern_type=row["pattern_type"],
                canonical_text=row["canonical_text"],
                member_count=row["member_count"],
                doc_count=row["doc_count"],
                average_confidence=row["average_confidence"],
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            )
            for row in rows
        ]

    def count_pattern_families(self, pattern_type: Optional[str] = None) -> int:
        """Count pattern families, optionally filtered by type."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        if pattern_type:
            cursor = self.conn.execute(
                "SELECT COUNT(*) FROM pattern_families WHERE pattern_type = ?",
                (pattern_type,),
            )
        else:
            cursor = self.conn.execute("SELECT COUNT(*) FROM pattern_families")

        return cursor.fetchone()[0]
