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

# Success point extraction prompt
SUCCESS_POINT_EXTRACTION_PROMPT = """You are analyzing a document chunk to extract success indicators, achievements, or positive outcomes.

Success points include:
- Completed milestones or deliverables
- Met or exceeded objectives/targets
- Positive performance indicators
- Successful past projects or implementations
- Proven capabilities or expertise
- Competitive advantages or strengths
- Satisfied client testimonials or results

Keywords: achieved, completed, successful, exceeded, delivered, proven, demonstrated, track record, accomplished, satisfied, effective, improved, increased

Analyze the following chunk and extract structured information in JSON format:

{
  "is_success_point": true/false,
  "point_text": "exact text describing the success" | null,
  "category": "achievement" | "milestone" | "outcome" | "capability" | "testimonial" | null,
  "topic": "brief topic (e.g., project delivery, performance, quality)" | null,
  "entities": ["entity1", "entity2"] | null,
  "confidence": 0.0-1.0
}

Guidelines:
- is_success_point: true if chunk describes a positive outcome or achievement
- point_text: the exact text describing the success
- category: type of success indicator
- topic: general domain or area
- entities: specific projects, metrics, standards, or technologies mentioned
- confidence: how confident you are this is a genuine success point

Chunk:
{chunk_text}

JSON output:
"""

# Failure point extraction prompt
FAILURE_POINT_EXTRACTION_PROMPT = """You are analyzing a document chunk to extract failure indicators, risks, issues, or concerns.

Failure points include:
- Identified risks or potential problems
- Past failures or unsuccessful attempts
- Unmet requirements or capability gaps
- Blockers or impediments
- Technical debt or limitations
- Concerns or weaknesses
- Areas needing improvement

Keywords: risk, issue, failed, problem, challenge, gap, concern, weakness, unable to, limitation, blocker, difficulty, deficiency, lacks, insufficient

Analyze the following chunk and extract structured information in JSON format:

{
  "is_failure_point": true/false,
  "point_text": "exact text describing the failure/risk" | null,
  "category": "risk" | "issue" | "gap" | "blocker" | "weakness" | null,
  "severity": "high" | "medium" | "low" | null,
  "topic": "brief topic (e.g., security, technical, resource)" | null,
  "entities": ["entity1", "entity2"] | null,
  "confidence": 0.0-1.0
}

Guidelines:
- is_failure_point: true if chunk describes a failure, risk, or concern
- point_text: the exact text describing the issue
- category: type of failure/risk
- severity: impact level if mentioned or can be inferred
- topic: general domain or area
- entities: specific systems, processes, or standards mentioned
- confidence: how confident you are this is a genuine failure point

Chunk:
{chunk_text}

JSON output:
"""

# Risk extraction prompt (more specific than failure points)
RISK_EXTRACTION_PROMPT = """You are analyzing a document chunk to extract risk statements.

A risk is a potential future event or condition that could negatively impact objectives.

Keywords: risk, potential, possible, may occur, likelihood, probability, threat, vulnerability, exposure, uncertain

Analyze the following chunk and extract structured information in JSON format:

{
  "is_risk": true/false,
  "risk_text": "exact description of the risk" | null,
  "category": "technical" | "financial" | "schedule" | "resource" | "external" | "compliance" | null,
  "severity": "critical" | "high" | "medium" | "low" | null,
  "likelihood": "high" | "medium" | "low" | null,
  "topic": "brief topic" | null,
  "entities": ["entity1", "entity2"] | null,
  "confidence": 0.0-1.0
}

Guidelines:
- is_risk: true if chunk describes a potential negative event
- risk_text: exact description of the risk
- category: type of risk
- severity: potential impact if risk occurs
- likelihood: probability of occurrence if mentioned
- entities: related systems, processes, or standards
- confidence: how confident you are this is a genuine risk

Chunk:
{chunk_text}

JSON output:
"""

# Constraint extraction prompt
CONSTRAINT_EXTRACTION_PROMPT = """You are analyzing a document chunk to extract constraints or limitations.

Constraints include:
- Technical limitations or restrictions
- Budget or resource constraints
- Time or schedule constraints
- Regulatory or compliance restrictions
- Environmental or operational constraints
- Dependencies or prerequisites

Keywords: limited to, restricted, cannot, constraint, limitation, dependency, prerequisite, maximum, minimum, boundary, must not exceed, within

Analyze the following chunk and extract structured information in JSON format:

{
  "is_constraint": true/false,
  "constraint_text": "exact text describing the constraint" | null,
  "category": "technical" | "budget" | "schedule" | "regulatory" | "resource" | "operational" | null,
  "severity": "hard" | "soft" | null,
  "topic": "brief topic" | null,
  "entities": ["entity1", "entity2"] | null,
  "confidence": 0.0-1.0
}

Guidelines:
- is_constraint: true if chunk describes a limitation or restriction
- constraint_text: exact description of the constraint
- category: type of constraint
- severity: "hard" for absolute limits, "soft" for flexible constraints
- entities: related standards, regulations, or systems
- confidence: how confident you are this is a genuine constraint

Chunk:
{chunk_text}

JSON output:
"""

# Generic pattern extraction prompt (flexible for any pattern type)
GENERIC_PATTERN_EXTRACTION_PROMPT = """You are analyzing a document chunk to extract {pattern_type} patterns.

{pattern_description}

Keywords: {keywords}

Analyze the following chunk and extract structured information in JSON format:

{{
  "is_pattern": true/false,
  "pattern_text": "exact text" | null,
  "category": "{categories}" | null,
  "topic": "brief topic" | null,
  "entities": ["entity1", "entity2"] | null,
  "confidence": 0.0-1.0,
  "metadata": {{}} | null
}}

Chunk:
{chunk_text}

JSON output:
"""
