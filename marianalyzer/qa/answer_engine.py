"""Question answering engine with structured JSON output."""

from typing import List

from marianalyzer.config import Config
from marianalyzer.database import Database
from marianalyzer.llm.ollama_client import OllamaClient
from marianalyzer.llm.prompts import QA_PROMPT
from marianalyzer.models import Chunk, QueryResponse
from marianalyzer.qa.retriever import HybridRetriever
from marianalyzer.utils.logging_config import get_logger

logger = get_logger()


def answer_question(
    question: str,
    db: Database,
    config: Config,
    top_k: int = 20,
) -> QueryResponse:
    """Answer a question using RAG.

    Args:
        question: User question
        db: Database instance
        config: Configuration
        top_k: Number of chunks to retrieve

    Returns:
        QueryResponse with structured answer
    """
    logger.info(f"Answering question: {question}")

    # Retrieve relevant chunks
    retriever = HybridRetriever(config)
    results = retriever.retrieve(question, top_k=top_k)

    if not results:
        logger.warning("No relevant chunks found")
        return QueryResponse(
            query=question,
            answer="I couldn't find any relevant information in the documents to answer this question.",
            evidence=[],
        )

    # Build context from chunks
    context_parts = []
    evidence = []

    for i, (chunk, score) in enumerate(results, start=1):
        context_parts.append(f"[{i}] {chunk.chunk_text}")

        evidence.append({
            "chunk_id": chunk.id,
            "chunk_text": chunk.chunk_text,
            "citation": chunk.citation,
            "relevance_score": float(score),
        })

    context = "\n\n".join(context_parts)

    # Generate answer using LLM
    ollama_client = OllamaClient(config.ollama_host)

    prompt = QA_PROMPT.format(
        context=context,
        question=question,
    )

    try:
        response_json = ollama_client.generate_json(
            prompt=prompt,
            model=config.llm_model,
            temperature=0.5,
        )

        # Extract answer and citations
        answer = response_json.get("answer", "")
        key_points = response_json.get("key_points", [])
        cited_ids = response_json.get("citations", [])

        # Filter evidence to only cited chunks
        if cited_ids:
            cited_evidence = [
                ev for ev in evidence
                if f"chunk_id_{ev['chunk_id']}" in cited_ids or str(ev['chunk_id']) in cited_ids
            ]
        else:
            # If no citations, include all evidence
            cited_evidence = evidence

        # Create response
        response = QueryResponse(
            query=question,
            answer=answer,
            evidence=cited_evidence,
            metadata={
                "key_points": key_points,
                "num_chunks_retrieved": len(results),
                "num_chunks_cited": len(cited_evidence),
            },
        )

        logger.info(f"Generated answer with {len(cited_evidence)} citations")

        return response

    except Exception as e:
        logger.error(f"Failed to generate answer: {e}")

        # Fallback: return simple response
        return QueryResponse(
            query=question,
            answer=f"I found relevant information but encountered an error generating a structured answer: {str(e)}",
            evidence=evidence[:10],  # Return top 10 chunks
        )


def answer_with_families(
    question: str,
    db: Database,
    config: Config,
    top_n: int = 20,
) -> QueryResponse:
    """Answer a question about requirement families.

    Special handler for queries like "top 20 recurring requirements".

    Args:
        question: User question
        db: Database instance
        config: Configuration
        top_n: Number of families to return

    Returns:
        QueryResponse with family information
    """
    logger.info(f"Answering family question: {question}")

    # Get top families
    families = db.get_top_families(limit=top_n)

    if not families:
        return QueryResponse(
            query=question,
            answer="No requirement families have been created yet. Run 'rfp-rag aggregate' first.",
            evidence=[],
        )

    # Format answer
    answer_parts = [f"Here are the top {len(families)} recurring requirements:\n"]

    evidence = []

    for i, family in enumerate(families, start=1):
        answer_parts.append(
            f"{i}. {family.canonical_text}\n"
            f"   - Appears {family.member_count} times across {family.doc_count} documents"
        )

        evidence.append({
            "family_id": family.id,
            "canonical_text": family.canonical_text,
            "member_count": family.member_count,
            "doc_count": family.doc_count,
            "citation": f"family_{family.id}",
            "relevance_score": family.doc_count / max(f.doc_count for f in families),
        })

    answer = "\n".join(answer_parts)

    return QueryResponse(
        query=question,
        answer=answer,
        evidence=evidence,
        metadata={
            "type": "family_query",
            "num_families": len(families),
        },
    )
