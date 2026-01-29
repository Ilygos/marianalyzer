"""Requirement extraction pipeline."""

import hashlib
import json
import re

from rich.console import Console
from rich.progress import track

from ..config import get_config
from ..models import Requirement
from ..store import SQLiteStore
from ..utils import generate_completion, extract_json_from_response, normalize_text

console = Console()


EXTRACTION_SYSTEM_PROMPT = """You are an expert at extracting requirements from documents.

A requirement is:
- A sentence or bullet point containing modal verbs like: must, shall, should, required, mandatory, obligatory
- A table row that specifies a requirement or constraint
- A clear specification that something is needed or expected

Extract ALL requirements from the provided text and return them as a JSON array.

For each requirement, provide:
- req_text: The exact requirement text
- modality: The modal verb (must/shall/should/required/etc.)
- topic: Brief topic/category (e.g., "security", "performance", "compliance")
- entities: List of key entities mentioned (e.g., ["ISO27001", "vendor"])
- confidence: Your confidence score (0.0-1.0)

Return ONLY a JSON array of requirements, no other text."""


def detect_requirement_candidates(text: str, keywords: list[str]) -> bool:
    """Check if text likely contains requirements."""
    text_lower = text.lower()
    for keyword in keywords:
        if keyword in text_lower:
            return True
    return False


def extract_requirements_from_chunk(
    chunk_id: str,
    doc_id: str,
    company_id: str,
    text: str,
) -> list[Requirement]:
    """Extract requirements from a single chunk using LLM."""
    
    prompt = f"""Extract all requirements from the following text:

{text}

Return a JSON array of requirements."""
    
    try:
        response = generate_completion(
            prompt=prompt,
            system=EXTRACTION_SYSTEM_PROMPT,
            json_mode=True,
        )
        
        # Parse JSON response
        requirements_data = extract_json_from_response(response)
        
        # Handle both array and object responses
        if isinstance(requirements_data, dict):
            if "requirements" in requirements_data:
                requirements_data = requirements_data["requirements"]
            else:
                requirements_data = [requirements_data]
        
        # Convert to Requirement objects
        requirements = []
        for req_data in requirements_data:
            req_id = hashlib.md5(
                f"{chunk_id}:{req_data['req_text']}".encode()
            ).hexdigest()[:16]
            
            requirement = Requirement(
                req_id=req_id,
                doc_id=doc_id,
                chunk_id=chunk_id,
                company_id=company_id,
                req_text=req_data["req_text"],
                modality=req_data.get("modality", "must"),
                topic=req_data.get("topic"),
                entities=req_data.get("entities", []),
                req_norm=normalize_text(req_data["req_text"]),
                confidence=req_data.get("confidence", 1.0),
                evidence={"source": "llm_extraction"},
            )
            requirements.append(requirement)
        
        return requirements
        
    except Exception as e:
        console.print(f"[yellow]Error extracting requirements: {e}[/yellow]")
        return []


def extract_requirements(company_id: str) -> None:
    """
    Extract requirements from all chunks for a company.
    
    Args:
        company_id: Company identifier
    """
    config = get_config()
    store = SQLiteStore(config.db_path)
    
    # Get all chunks
    chunks = store.get_chunks_by_company(company_id)
    
    console.print(f"Extracting requirements from {len(chunks)} chunks")
    
    # Filter to candidate chunks
    candidates = []
    for chunk in chunks:
        if detect_requirement_candidates(chunk.text, config.requirement_keywords):
            candidates.append(chunk)
    
    console.print(f"Found {len(candidates)} candidate chunks")
    
    total_requirements = 0
    
    for chunk in track(candidates, description="Extracting requirements"):
        requirements = extract_requirements_from_chunk(
            chunk_id=chunk.chunk_id,
            doc_id=chunk.doc_id,
            company_id=company_id,
            text=chunk.text,
        )
        
        for requirement in requirements:
            store.insert_requirement(requirement)
            total_requirements += 1
    
    console.print(f"[green]Extracted {total_requirements} requirements[/green]")
