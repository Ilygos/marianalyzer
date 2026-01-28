"""Generic pattern extraction for various pattern types."""

import json
import re
from typing import Any, Dict, List, Optional

from tqdm import tqdm

from marianalyzer.config import Config
from marianalyzer.database import Database
from marianalyzer.extraction.normalizer import normalize_requirement
from marianalyzer.llm.ollama_client import OllamaClient
from marianalyzer.llm.prompts import (
    CONSTRAINT_EXTRACTION_PROMPT,
    FAILURE_POINT_EXTRACTION_PROMPT,
    RISK_EXTRACTION_PROMPT,
    SUCCESS_POINT_EXTRACTION_PROMPT,
)
from marianalyzer.models import Pattern
from marianalyzer.utils.logging_config import get_logger

logger = get_logger()


# Pattern type configurations
PATTERN_CONFIGS = {
    "success_point": {
        "prompt": SUCCESS_POINT_EXTRACTION_PROMPT,
        "keywords": [
            "achieved",
            "completed",
            "successful",
            "exceeded",
            "delivered",
            "proven",
            "demonstrated",
            "track record",
            "accomplished",
            "effective",
            "improved",
        ],
        "response_key": "is_success_point",
    },
    "failure_point": {
        "prompt": FAILURE_POINT_EXTRACTION_PROMPT,
        "keywords": [
            "risk",
            "issue",
            "failed",
            "problem",
            "challenge",
            "gap",
            "concern",
            "weakness",
            "unable to",
            "limitation",
            "blocker",
            "difficulty",
        ],
        "response_key": "is_failure_point",
    },
    "risk": {
        "prompt": RISK_EXTRACTION_PROMPT,
        "keywords": [
            "risk",
            "potential",
            "possible",
            "may occur",
            "likelihood",
            "probability",
            "threat",
            "vulnerability",
            "exposure",
        ],
        "response_key": "is_risk",
    },
    "constraint": {
        "prompt": CONSTRAINT_EXTRACTION_PROMPT,
        "keywords": [
            "limited to",
            "restricted",
            "cannot",
            "constraint",
            "limitation",
            "dependency",
            "prerequisite",
            "maximum",
            "minimum",
            "must not exceed",
        ],
        "response_key": "is_constraint",
    },
}


def extract_patterns(
    db: Database,
    config: Config,
    pattern_type: str,
    confidence_threshold: Optional[float] = None,
) -> Dict[str, int]:
    """Extract patterns of a specific type from all chunks.

    Args:
        db: Database instance
        config: Configuration
        pattern_type: Type of pattern to extract (success_point, failure_point, risk, constraint)
        confidence_threshold: Minimum confidence threshold (uses config default if None)

    Returns:
        Statistics dictionary
    """
    if pattern_type not in PATTERN_CONFIGS:
        raise ValueError(
            f"Unknown pattern type: {pattern_type}. "
            f"Valid types: {', '.join(PATTERN_CONFIGS.keys())}"
        )

    logger.info(f"Extracting {pattern_type} patterns")

    pattern_config = PATTERN_CONFIGS[pattern_type]
    threshold = confidence_threshold or config.requirement_confidence_threshold

    # Load all chunks
    chunks = db.get_all_chunks()

    if not chunks:
        logger.warning("No chunks found in database")
        return {"extracted": 0, "chunks_processed": 0}

    # Initialize Ollama client
    ollama_client = OllamaClient(config.ollama_host)

    # Check Ollama connectivity
    if not ollama_client.check_health():
        raise RuntimeError("Ollama is not running or not accessible")

    stats = {"extracted": 0, "chunks_processed": 0, "skipped": 0}

    # Process chunks with pattern-specific keywords pre-filtering
    for chunk in tqdm(chunks, desc=f"Extracting {pattern_type}"):
        stats["chunks_processed"] += 1

        # Pre-filter by keywords
        if not _contains_keywords(chunk.chunk_text, pattern_config["keywords"]):
            stats["skipped"] += 1
            continue

        try:
            # Use LLM to validate and extract structured data
            prompt = pattern_config["prompt"].format(chunk_text=chunk.chunk_text)

            response_json = ollama_client.generate_json(
                prompt=prompt,
                model=config.llm_model,
                temperature=0.3,
            )

            # Check if pattern was found
            is_pattern = response_json.get(pattern_config["response_key"], False)
            if not is_pattern:
                continue

            # Extract pattern data
            pattern_text = response_json.get("point_text") or response_json.get(
                "risk_text"
            ) or response_json.get("constraint_text")
            if not pattern_text:
                continue

            confidence = response_json.get("confidence", 0.0)
            if confidence < threshold:
                continue

            # Normalize text for clustering
            pattern_norm = normalize_requirement(pattern_text)

            # Create pattern object
            pattern = Pattern(
                chunk_id=chunk.id,
                pattern_type=pattern_type,
                pattern_text=pattern_text,
                pattern_norm=pattern_norm,
                category=response_json.get("category"),
                severity=response_json.get("severity"),
                modality=response_json.get("modality"),
                topic=response_json.get("topic"),
                entities=response_json.get("entities"),
                confidence=confidence,
                metadata=response_json.get("metadata"),
            )

            # Insert into database
            db.insert_pattern(pattern)
            stats["extracted"] += 1

            logger.debug(
                f"Extracted {pattern_type}: {pattern_text[:60]}... (confidence: {confidence:.2f})"
            )

        except Exception as e:
            logger.error(f"Failed to extract pattern from chunk {chunk.id}: {e}")
            continue

    logger.info(
        f"Extraction complete: {stats['extracted']} {pattern_type} patterns extracted "
        f"from {stats['chunks_processed']} chunks ({stats['skipped']} skipped)"
    )

    return stats


def _contains_keywords(text: str, keywords: List[str]) -> bool:
    """Check if text contains any of the keywords.

    Args:
        text: Text to check
        keywords: List of keywords

    Returns:
        True if any keyword is found
    """
    text_lower = text.lower()

    for keyword in keywords:
        # Use word boundaries for more accurate matching
        pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
        if re.search(pattern, text_lower):
            return True

    return False


def extract_all_pattern_types(
    db: Database,
    config: Config,
    pattern_types: Optional[List[str]] = None,
) -> Dict[str, Dict[str, int]]:
    """Extract all pattern types in sequence.

    Args:
        db: Database instance
        config: Configuration
        pattern_types: List of pattern types to extract (defaults to all)

    Returns:
        Statistics dictionary with results for each pattern type
    """
    if pattern_types is None:
        pattern_types = list(PATTERN_CONFIGS.keys())

    results = {}

    for pattern_type in pattern_types:
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Processing pattern type: {pattern_type}")
        logger.info(f"{'=' * 60}\n")

        try:
            stats = extract_patterns(db, config, pattern_type)
            results[pattern_type] = stats
        except Exception as e:
            logger.error(f"Failed to extract {pattern_type}: {e}")
            results[pattern_type] = {"error": str(e)}

    return results
