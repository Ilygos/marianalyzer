"""Pattern-aware question answering engine."""

from typing import Dict, List, Optional

from marianalyzer.config import Config
from marianalyzer.database import Database
from marianalyzer.llm.ollama_client import OllamaClient
from marianalyzer.models import Pattern, QueryResponse
from marianalyzer.qa.retriever import HybridRetriever
from marianalyzer.utils.logging_config import get_logger

logger = get_logger()


# Question type detection patterns
QUESTION_PATTERNS = {
    "success": [
        "success",
        "achievement",
        "accomplishment",
        "completed",
        "delivered",
        "proven",
        "strength",
        "advantage",
        "positive",
    ],
    "failure": [
        "failure",
        "problem",
        "issue",
        "concern",
        "weakness",
        "gap",
        "challenge",
        "difficulty",
    ],
    "risk": [
        "risk",
        "threat",
        "potential problem",
        "vulnerability",
        "exposure",
        "uncertain",
    ],
    "constraint": [
        "constraint",
        "limitation",
        "restriction",
        "boundary",
        "dependency",
        "prerequisite",
    ],
    "requirement": [
        "requirement",
        "must",
        "shall",
        "should",
        "mandatory",
        "needed",
    ],
}


def detect_question_type(question: str) -> Optional[str]:
    """Detect the type of question based on keywords.

    Args:
        question: User's question

    Returns:
        Question type or None if no clear type detected
    """
    question_lower = question.lower()

    # Count matches for each pattern type
    scores = {}
    for pattern_type, keywords in QUESTION_PATTERNS.items():
        score = sum(1 for kw in keywords if kw in question_lower)
        if score > 0:
            scores[pattern_type] = score

    if not scores:
        return None

    # Return type with highest score
    return max(scores, key=scores.get)


def answer_pattern_question(
    question: str,
    db: Database,
    config: Config,
    pattern_type: Optional[str] = None,
    top_k: int = 20,
) -> QueryResponse:
    """Answer a question about specific pattern types.

    Args:
        question: User question
        db: Database instance
        config: Configuration
        pattern_type: Specific pattern type to query (auto-detected if None)
        top_k: Number of patterns to include

    Returns:
        QueryResponse with pattern-specific answer
    """
    # Auto-detect pattern type if not specified
    if pattern_type is None:
        pattern_type = detect_question_type(question)

    logger.info(f"Answering pattern question (type: {pattern_type}): {question}")

    # Map question types to pattern types
    pattern_type_mapping = {
        "success": "success_point",
        "failure": "failure_point",
        "risk": "risk",
        "constraint": "constraint",
        "requirement": "requirement",
    }

    # Get patterns of the detected type
    if pattern_type and pattern_type in pattern_type_mapping:
        db_pattern_type = pattern_type_mapping[pattern_type]

        if db_pattern_type == "requirement":
            # Use legacy requirements table
            patterns = db.get_all_requirements()
            pattern_dicts = [
                {
                    "text": p.req_text,
                    "topic": p.topic,
                    "confidence": p.confidence,
                    "entities": p.entities,
                }
                for p in patterns
            ]
        else:
            # Use new patterns table
            patterns = db.get_patterns_by_type(db_pattern_type)
            pattern_dicts = [
                {
                    "text": p.pattern_text,
                    "category": p.category,
                    "severity": p.severity,
                    "topic": p.topic,
                    "confidence": p.confidence,
                    "entities": p.entities,
                }
                for p in patterns
            ]

        if not patterns:
            return QueryResponse(
                query=question,
                answer=f"No {pattern_type} patterns have been extracted yet. "
                f"Run 'marianalyzer extract {db_pattern_type}' first.",
                evidence=[],
            )

        # Sort by confidence
        pattern_dicts = sorted(pattern_dicts, key=lambda x: x["confidence"], reverse=True)
        pattern_dicts = pattern_dicts[:top_k]

        # Format answer
        pattern_name = pattern_type.replace("_", " ").title()
        answer_parts = [f"Here are the top {len(pattern_dicts)} {pattern_name}:\n"]

        evidence = []
        for i, p in enumerate(pattern_dicts, 1):
            answer_parts.append(
                f"{i}. {p['text']}\n"
                f"   - Confidence: {p['confidence']:.2f}"
            )

            if p.get("category"):
                answer_parts[-1] += f", Category: {p['category']}"
            if p.get("severity"):
                answer_parts[-1] += f", Severity: {p['severity']}"
            if p.get("topic"):
                answer_parts[-1] += f", Topic: {p['topic']}"

            evidence.append({
                "pattern_text": p["text"],
                "confidence": p["confidence"],
                "category": p.get("category"),
                "severity": p.get("severity"),
                "topic": p.get("topic"),
                "entities": p.get("entities"),
            })

        answer = "\n".join(answer_parts)

        return QueryResponse(
            query=question,
            answer=answer,
            evidence=evidence,
            metadata={
                "pattern_type": pattern_type,
                "num_patterns": len(pattern_dicts),
            },
        )

    else:
        # Fall back to general QA if no specific pattern type detected
        from marianalyzer.qa.answer_engine import answer_question

        return answer_question(question, db, config, top_k)


def answer_comparative_question(
    question: str,
    db: Database,
    config: Config,
) -> QueryResponse:
    """Answer comparative questions across pattern types.

    Handles questions like:
    - "What are more: successes or failures?"
    - "Compare risks and constraints"
    - "What's the balance between achievements and issues?"

    Args:
        question: User question
        db: Database instance
        config: Configuration

    Returns:
        QueryResponse with comparative analysis
    """
    logger.info(f"Answering comparative question: {question}")

    # Get counts for each pattern type
    pattern_counts = {
        "Requirements": db.count_requirements(),
        "Success Points": db.count_patterns("success_point"),
        "Failure Points": db.count_patterns("failure_point"),
        "Risks": db.count_patterns("risk"),
        "Constraints": db.count_patterns("constraint"),
    }

    # Calculate total
    total = sum(pattern_counts.values())

    if total == 0:
        return QueryResponse(
            query=question,
            answer="No patterns have been extracted yet. Run 'marianalyzer extract all' first.",
            evidence=[],
        )

    # Format answer
    answer_parts = ["Pattern Distribution Analysis:\n"]

    evidence = []
    for pattern_type, count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total * 100) if total > 0 else 0
        answer_parts.append(f"- {pattern_type}: {count} ({percentage:.1f}%)")

        evidence.append({
            "pattern_type": pattern_type,
            "count": count,
            "percentage": percentage,
        })

    answer_parts.append(f"\nTotal patterns: {total}")

    # Add insights
    max_type = max(pattern_counts, key=pattern_counts.get)
    min_type = min((k, v) for k, v in pattern_counts.items() if v > 0)

    answer_parts.append(f"\nInsights:")
    answer_parts.append(f"- Most common: {max_type} ({pattern_counts[max_type]} instances)")
    if min_type[1] > 0:
        answer_parts.append(f"- Least common: {min_type[0]} ({min_type[1]} instances)")

    # Success vs failure ratio
    success_count = pattern_counts["Success Points"]
    failure_count = pattern_counts["Failure Points"]
    if success_count > 0 or failure_count > 0:
        ratio = success_count / (failure_count + 1)  # +1 to avoid division by zero
        answer_parts.append(f"- Success/Failure ratio: {ratio:.2f}")

    answer = "\n".join(answer_parts)

    return QueryResponse(
        query=question,
        answer=answer,
        evidence=evidence,
        metadata={
            "query_type": "comparative",
            "total_patterns": total,
        },
    )


def is_comparative_question(question: str) -> bool:
    """Check if question is comparative.

    Args:
        question: User question

    Returns:
        True if question is comparative
    """
    comparative_keywords = [
        "compare",
        "comparison",
        "versus",
        "vs",
        "more than",
        "less than",
        "balance",
        "ratio",
        "distribution",
        "how many",
    ]

    question_lower = question.lower()
    return any(kw in question_lower for kw in comparative_keywords)
