"""Requirement extraction using LLM."""

import json
import re
from typing import Dict, Optional

from tqdm import tqdm

from marianalyzer.config import Config
from marianalyzer.database import Database
from marianalyzer.extraction.normalizer import normalize_requirement
from marianalyzer.llm.ollama_client import OllamaClient
from marianalyzer.llm.prompts import REQUIREMENT_EXTRACTION_PROMPT
from marianalyzer.models import ExtractionResult, Requirement
from marianalyzer.utils.logging_config import get_logger

logger = get_logger()


def has_requirement_keywords(text: str) -> bool:
    """Pre-filter: check if text contains requirement keywords.

    Args:
        text: Text to check

    Returns:
        True if contains requirement keywords
    """
    keywords = r'\b(must|shall|should|required|mandatory|may|optional|needs?\s+to|has\s+to)\b'
    return bool(re.search(keywords, text, re.IGNORECASE))


def extract_requirement_from_chunk(
    chunk_text: str,
    ollama_client: OllamaClient,
    llm_model: str,
) -> Optional[ExtractionResult]:
    """Extract requirement from a single chunk using LLM.

    Args:
        chunk_text: Chunk text to analyze
        ollama_client: Ollama client instance
        llm_model: LLM model name

    Returns:
        ExtractionResult if successful, None otherwise
    """
    prompt = REQUIREMENT_EXTRACTION_PROMPT.format(chunk_text=chunk_text)

    try:
        response_json = ollama_client.generate_json(
            prompt=prompt,
            model=llm_model,
            temperature=0.3,  # Lower temperature for more deterministic extraction
        )

        # Parse into ExtractionResult
        result = ExtractionResult(**response_json)
        return result

    except Exception as e:
        logger.warning(f"Failed to extract requirement: {e}")
        return None


def extract_requirements(db: Database, config: Config) -> Dict[str, int]:
    """Extract requirements from all chunks in database.

    Args:
        db: Database instance
        config: Configuration

    Returns:
        Statistics dictionary
    """
    logger.info("Starting requirement extraction")

    # Load all chunks
    chunks = db.get_all_chunks()

    if not chunks:
        logger.warning("No chunks found in database")
        return {"extracted": 0, "chunks_processed": 0}

    # Initialize Ollama client
    ollama_client = OllamaClient(config.ollama_host)

    # Check Ollama health
    if not ollama_client.check_health():
        raise RuntimeError("Ollama is not running or not accessible")

    stats = {
        "chunks_processed": 0,
        "chunks_with_keywords": 0,
        "extracted": 0,
        "failed": 0,
    }

    # Process each chunk
    for chunk in tqdm(chunks, desc="Extracting requirements"):
        stats["chunks_processed"] += 1

        # Pre-filter: skip chunks without requirement keywords
        if not has_requirement_keywords(chunk.chunk_text):
            continue

        stats["chunks_with_keywords"] += 1

        # Extract using LLM
        result = extract_requirement_from_chunk(
            chunk_text=chunk.chunk_text,
            ollama_client=ollama_client,
            llm_model=config.llm_model,
        )

        if not result or not result.is_requirement:
            continue

        # Check confidence threshold
        if result.confidence < config.requirement_confidence_threshold:
            logger.debug(f"Skipping low-confidence requirement (confidence={result.confidence})")
            continue

        # Normalize requirement text
        req_norm = normalize_requirement(result.req_text)

        # Create requirement object
        requirement = Requirement(
            chunk_id=chunk.id,
            req_text=result.req_text,
            req_norm=req_norm,
            modality=result.modality,
            topic=result.topic,
            entities=result.entities,
            confidence=result.confidence,
        )

        try:
            # Insert into database
            req_id = db.insert_requirement(requirement)
            stats["extracted"] += 1

            logger.debug(f"Extracted requirement {req_id}: {result.req_text[:80]}...")

        except Exception as e:
            logger.error(f"Failed to insert requirement: {e}")
            stats["failed"] += 1

    logger.info(
        f"Extraction complete: {stats['extracted']} requirements from "
        f"{stats['chunks_with_keywords']} candidate chunks "
        f"({stats['chunks_processed']} total chunks)"
    )

    return stats
