"""Prompt templates for LLM tasks."""

# Requirement extraction prompt
REQUIREMENT_EXTRACTION_PROMPT = """You are analyzing a document chunk to extract requirements.

A requirement is a statement that specifies what must/should/may be done or what conditions must be met.
Keywords: must, shall, should, required, mandatory, may, optional, needs to, has to

Analyze the following chunk and extract structured information in JSON format:

{
  "is_requirement": true/false,
  "req_text": "exact text of requirement if found, null otherwise",
  "modality": "must" | "should" | "may" | null,
  "topic": "brief topic classification (e.g., security, performance, compliance)" | null,
  "entities": ["entity1", "entity2"] | null,
  "confidence": 0.0-1.0
}

Guidelines:
- is_requirement: true if the chunk contains a clear requirement statement
- req_text: the exact requirement text (may be subset of chunk)
- modality: the requirement strength (must > should > may)
- topic: general category or domain
- entities: mentioned standards, technologies, or specific terms (e.g., "GDPR", "HTTPS", "ISO 27001")
- confidence: how confident you are this is a genuine requirement (0.0-1.0)

Chunk:
{chunk_text}

JSON output:
"""

# Requirement normalization prompt
REQUIREMENT_NORMALIZATION_PROMPT = """Normalize the following requirement text for clustering.

Remove:
- Specific numbers, dates, and quantities (replace with placeholders)
- Company/project-specific names
- Unnecessary adjectives and adverbs

Keep:
- Core meaning and intent
- Keywords and technical terms
- Modal verbs (must, should, may)

Original requirement:
{req_text}

Normalized requirement:
"""

# Requirement family canonical text generation
FAMILY_CANONICAL_PROMPT = """You have a cluster of similar requirements. Generate a single canonical statement that captures the common intent.

Requirements:
{requirements}

Generate a concise canonical requirement that:
1. Captures the shared meaning
2. Uses generic terminology (no specific project names)
3. Preserves the modal strength (must/should/may)
4. Is clear and actionable

Canonical requirement:
"""

# QA prompt with structured output
QA_PROMPT = """You are a helpful assistant analyzing RFP (Request for Proposal) documents.

Based on the following context from document chunks, answer the user's question.

Context:
{context}

Question: {question}

Provide a structured answer in JSON format:

{{
  "answer": "comprehensive answer to the question",
  "key_points": ["point 1", "point 2", "point 3"],
  "citations": ["chunk_id_1", "chunk_id_2"]
}}

Guidelines:
- Only use information from the provided context
- Include citations to relevant chunks
- If you cannot answer from the context, state that clearly
- Be concise but comprehensive

JSON output:
"""

# Clustering/similarity prompt (for edge cases)
SIMILARITY_PROMPT = """Determine if these two requirements express the same underlying need.

Requirement 1: {req1}

Requirement 2: {req2}

Respond with JSON:

{
  "are_similar": true/false,
  "confidence": 0.0-1.0,
  "explanation": "brief explanation"
}

JSON output:
"""
