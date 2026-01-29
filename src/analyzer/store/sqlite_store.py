"""SQLite storage implementation."""

import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

from ..models import (
    Chunk,
    Document,
    GlossaryEntry,
    Heading,
    Playbook,
    Requirement,
    RequirementFamily,
)


class SQLiteStore:
    """SQLite database store."""

    def __init__(self, db_path: Path):
        """Initialize the SQLite store."""
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL,
                path TEXT NOT NULL,
                type TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                mtime REAL NOT NULL,
                size INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        # Chunks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                chunk_type TEXT NOT NULL,
                text TEXT NOT NULL,
                structure_path_json TEXT,
                locator_json TEXT,
                raw_table_json TEXT,
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            )
        """)

        # Headings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS headings (
                heading_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                heading_text TEXT NOT NULL,
                heading_norm TEXT NOT NULL,
                level INTEGER NOT NULL,
                locator_json TEXT,
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            )
        """)

        # Requirements table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS requirements (
                req_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                chunk_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                req_text TEXT NOT NULL,
                modality TEXT NOT NULL,
                topic TEXT,
                entities_json TEXT,
                req_norm TEXT NOT NULL,
                confidence REAL NOT NULL,
                evidence_json TEXT,
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE,
                FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id) ON DELETE CASCADE
            )
        """)

        # Requirement families table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS req_families (
                family_id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL,
                title TEXT NOT NULL,
                canonical_text TEXT NOT NULL,
                member_count INTEGER DEFAULT 0,
                embedding_json TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # Requirement family members table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS req_family_members (
                family_id TEXT NOT NULL,
                req_id TEXT NOT NULL,
                PRIMARY KEY (family_id, req_id),
                FOREIGN KEY (family_id) REFERENCES req_families(family_id) ON DELETE CASCADE,
                FOREIGN KEY (req_id) REFERENCES requirements(req_id) ON DELETE CASCADE
            )
        """)

        # Glossary table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS glossary (
                company_id TEXT NOT NULL,
                term TEXT NOT NULL,
                preferred_term TEXT NOT NULL,
                notes TEXT,
                frequency INTEGER DEFAULT 0,
                PRIMARY KEY (company_id, term)
            )
        """)

        # Playbook table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS playbook (
                company_id TEXT NOT NULL,
                doc_type TEXT NOT NULL,
                playbook_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (company_id, doc_type)
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_company ON chunks(company_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_headings_doc ON headings(doc_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_headings_company ON headings(company_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_requirements_doc ON requirements(doc_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_requirements_company ON requirements(company_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_req_families_company ON req_families(company_id)")

        conn.commit()
        conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    # Document operations

    def insert_document(self, document: Document) -> None:
        """Insert a document."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO documents 
            (doc_id, company_id, path, type, sha256, mtime, size, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document.doc_id,
                document.company_id,
                document.path,
                document.type,
                document.sha256,
                document.mtime,
                document.size,
                document.created_at.isoformat(),
            ),
        )
        conn.commit()
        conn.close()

    def get_document(self, doc_id: str) -> Optional[Document]:
        """Get a document by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE doc_id = ?", (doc_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Document(**dict(row))
        return None

    def get_documents_by_company(self, company_id: str) -> list[Document]:
        """Get all documents for a company."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE company_id = ?", (company_id,))
        rows = cursor.fetchall()
        conn.close()
        
        return [Document(**dict(row)) for row in rows]

    def delete_document(self, doc_id: str) -> None:
        """Delete a document and all related data."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
        conn.commit()
        conn.close()

    # Chunk operations

    def insert_chunk(self, chunk: Chunk) -> None:
        """Insert a chunk."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO chunks 
            (chunk_id, doc_id, company_id, chunk_type, text, 
             structure_path_json, locator_json, raw_table_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chunk.chunk_id,
                chunk.doc_id,
                chunk.company_id,
                chunk.chunk_type.value,
                chunk.text,
                json.dumps(chunk.structure_path),
                json.dumps(chunk.locator.model_dump()),
                json.dumps(chunk.raw_table) if chunk.raw_table else None,
            ),
        )
        conn.commit()
        conn.close()

    def get_chunks_by_document(self, doc_id: str) -> list[Chunk]:
        """Get all chunks for a document."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM chunks WHERE doc_id = ?", (doc_id,))
        rows = cursor.fetchall()
        conn.close()
        
        chunks = []
        for row in rows:
            row_dict = dict(row)
            row_dict["structure_path"] = json.loads(row_dict["structure_path_json"])
            row_dict["locator"] = json.loads(row_dict["locator_json"])
            if row_dict["raw_table_json"]:
                row_dict["raw_table"] = json.loads(row_dict["raw_table_json"])
            del row_dict["structure_path_json"]
            del row_dict["locator_json"]
            del row_dict["raw_table_json"]
            chunks.append(Chunk(**row_dict))
        
        return chunks

    def get_chunks_by_company(self, company_id: str) -> list[Chunk]:
        """Get all chunks for a company."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM chunks WHERE company_id = ?", (company_id,))
        rows = cursor.fetchall()
        conn.close()
        
        chunks = []
        for row in rows:
            row_dict = dict(row)
            row_dict["structure_path"] = json.loads(row_dict["structure_path_json"])
            row_dict["locator"] = json.loads(row_dict["locator_json"])
            if row_dict["raw_table_json"]:
                row_dict["raw_table"] = json.loads(row_dict["raw_table_json"])
            del row_dict["structure_path_json"]
            del row_dict["locator_json"]
            del row_dict["raw_table_json"]
            chunks.append(Chunk(**row_dict))
        
        return chunks

    # Heading operations

    def insert_heading(self, heading: Heading) -> None:
        """Insert a heading."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO headings 
            (heading_id, doc_id, company_id, heading_text, heading_norm, level, locator_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                heading.heading_id,
                heading.doc_id,
                heading.company_id,
                heading.heading_text,
                heading.heading_norm,
                heading.level,
                json.dumps(heading.locator.model_dump()),
            ),
        )
        conn.commit()
        conn.close()

    def get_headings_by_company(self, company_id: str) -> list[Heading]:
        """Get all headings for a company."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM headings WHERE company_id = ?", (company_id,))
        rows = cursor.fetchall()
        conn.close()
        
        headings = []
        for row in rows:
            row_dict = dict(row)
            row_dict["locator"] = json.loads(row_dict["locator_json"])
            del row_dict["locator_json"]
            headings.append(Heading(**row_dict))
        
        return headings

    # Requirement operations

    def insert_requirement(self, requirement: Requirement) -> None:
        """Insert a requirement."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO requirements 
            (req_id, doc_id, chunk_id, company_id, req_text, modality, 
             topic, entities_json, req_norm, confidence, evidence_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                requirement.req_id,
                requirement.doc_id,
                requirement.chunk_id,
                requirement.company_id,
                requirement.req_text,
                requirement.modality,
                requirement.topic,
                json.dumps(requirement.entities),
                requirement.req_norm,
                requirement.confidence,
                json.dumps(requirement.evidence),
            ),
        )
        conn.commit()
        conn.close()

    def get_requirements_by_company(self, company_id: str) -> list[Requirement]:
        """Get all requirements for a company."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM requirements WHERE company_id = ?", (company_id,))
        rows = cursor.fetchall()
        conn.close()
        
        requirements = []
        for row in rows:
            row_dict = dict(row)
            row_dict["entities"] = json.loads(row_dict["entities_json"])
            row_dict["evidence"] = json.loads(row_dict["evidence_json"])
            del row_dict["entities_json"]
            del row_dict["evidence_json"]
            requirements.append(Requirement(**row_dict))
        
        return requirements

    # Requirement family operations

    def insert_requirement_family(self, family: RequirementFamily) -> None:
        """Insert a requirement family."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO req_families 
            (family_id, company_id, title, canonical_text, member_count, embedding_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                family.family_id,
                family.company_id,
                family.title,
                family.canonical_text,
                family.member_count,
                json.dumps(family.embedding) if family.embedding else None,
                family.created_at.isoformat(),
            ),
        )
        conn.commit()
        conn.close()

    def add_requirement_to_family(self, family_id: str, req_id: str) -> None:
        """Add a requirement to a family."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO req_family_members (family_id, req_id) VALUES (?, ?)",
            (family_id, req_id),
        )
        conn.commit()
        conn.close()

    def get_requirement_families_by_company(self, company_id: str) -> list[RequirementFamily]:
        """Get all requirement families for a company."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM req_families WHERE company_id = ?", (company_id,))
        rows = cursor.fetchall()
        conn.close()
        
        families = []
        for row in rows:
            row_dict = dict(row)
            if row_dict["embedding_json"]:
                row_dict["embedding"] = json.loads(row_dict["embedding_json"])
            del row_dict["embedding_json"]
            families.append(RequirementFamily(**row_dict))
        
        return families

    # Glossary operations

    def insert_glossary_entry(self, entry: GlossaryEntry) -> None:
        """Insert a glossary entry."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO glossary 
            (company_id, term, preferred_term, notes, frequency)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                entry.company_id,
                entry.term,
                entry.preferred_term,
                entry.notes,
                entry.frequency,
            ),
        )
        conn.commit()
        conn.close()

    def get_glossary_by_company(self, company_id: str) -> list[GlossaryEntry]:
        """Get all glossary entries for a company."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM glossary WHERE company_id = ?", (company_id,))
        rows = cursor.fetchall()
        conn.close()
        
        return [GlossaryEntry(**dict(row)) for row in rows]

    # Playbook operations

    def insert_playbook(self, playbook: Playbook) -> None:
        """Insert or update a playbook."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO playbook 
            (company_id, doc_type, playbook_json, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                playbook.company_id,
                playbook.doc_type,
                playbook.model_dump_json(),
                playbook.updated_at.isoformat(),
            ),
        )
        conn.commit()
        conn.close()

    def get_playbook(self, company_id: str, doc_type: str) -> Optional[Playbook]:
        """Get a playbook."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT playbook_json FROM playbook WHERE company_id = ? AND doc_type = ?",
            (company_id, doc_type),
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Playbook.model_validate_json(row["playbook_json"])
        return None
