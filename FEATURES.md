# Multi-Pattern Document Analyzer - Feature Guide

## Overview

The document analyzer has been extended to support **multiple pattern types** beyond just requirements. You can now extract and analyze:

1. **Requirements** - Must/shall/should statements
2. **Success Points** - Achievements, completions, proven capabilities
3. **Failure Points** - Issues, gaps, weaknesses, concerns
4. **Risks** - Potential threats, vulnerabilities, uncertainties
5. **Constraints** - Limitations, restrictions, boundaries

## Quick Start

### 1. Extract All Pattern Types

```bash
marianalyzer extract all
```

This will extract all pattern types in one command.

### 2. Extract Specific Patterns

```bash
# Extract success points
marianalyzer extract success_points

# Extract failure points
marianalyzer extract failure_points

# Extract risks
marianalyzer extract risks

# Extract constraints
marianalyzer extract constraints

# Extract requirements (legacy)
marianalyzer extract requirements
```

### 3. Set Confidence Threshold

```bash
# Only extract patterns with confidence >= 0.8
marianalyzer extract success_points --confidence 0.8
```

## Asking Questions

The QA engine now **automatically detects** what you're asking about:

### Pattern-Specific Questions

```bash
# About successes
marianalyzer ask "What are the main success points?"
marianalyzer ask "What achievements are mentioned?"
marianalyzer ask "What proven capabilities do we have?"

# About failures
marianalyzer ask "What are the main issues?"
marianalyzer ask "What gaps have been identified?"
marianalyzer ask "What are the concerns?"

# About risks
marianalyzer ask "What risks have been identified?"
marianalyzer ask "What are the potential threats?"
marianalyzer ask "What vulnerabilities exist?"

# About constraints
marianalyzer ask "What are the limitations?"
marianalyzer ask "What constraints do we have?"
marianalyzer ask "What are the dependencies?"

# About requirements
marianalyzer ask "What are the top requirements?"
marianalyzer ask "What must be delivered?"
```

### Comparative Questions

```bash
marianalyzer ask "Compare successes and failures"
marianalyzer ask "What's the distribution of patterns?"
marianalyzer ask "Are there more risks or constraints?"
marianalyzer ask "What's the success/failure ratio?"
```

### Force Specific Pattern Type

```bash
marianalyzer ask "What are the key points?" --pattern-type success
marianalyzer ask "Tell me about problems" --pattern-type failure
```

## Viewing Patterns

### List Patterns by Type

```bash
# List success points
marianalyzer list-patterns success_points

# Show top 20 with high confidence
marianalyzer list-patterns failure_points --limit 20 --min-confidence 0.7

# List all risks
marianalyzer list-patterns risks --limit 100
```

### Check Status

```bash
marianalyzer status
```

Output includes:
```
┌─────────────────────────────┬───────┐
│ Metric                      │ Count │
├─────────────────────────────┼───────┤
│ Documents                   │    15 │
│ Chunks                      │  1234 │
│                             │       │
│ Extracted Patterns          │       │
│   Requirements (legacy)     │    45 │
│   Success Points            │    23 │
│   Failure Points            │    12 │
│   Risks                     │     8 │
│   Constraints               │     5 │
│   Total Patterns            │    93 │
│                             │       │
│ Requirement Families        │    12 │
└─────────────────────────────┴───────┘
```

## Pattern Detection Keywords

Each pattern type uses specific keywords for detection:

### Success Points
- achieved, completed, successful, exceeded, delivered
- proven, demonstrated, track record, accomplished
- effective, improved, increased, satisfied

### Failure Points
- risk, issue, failed, problem, challenge, gap
- concern, weakness, unable to, limitation
- blocker, difficulty, deficiency, lacks

### Risks
- risk, potential, possible, may occur
- likelihood, probability, threat, vulnerability
- exposure, uncertain

### Constraints
- limited to, restricted, cannot, constraint
- limitation, dependency, prerequisite
- maximum, minimum, must not exceed

## Database Schema

All patterns are stored in a unified `patterns` table:

```sql
CREATE TABLE patterns (
    id INTEGER PRIMARY KEY,
    chunk_id INTEGER,
    pattern_type TEXT,  -- 'success_point', 'failure_point', 'risk', 'constraint'
    pattern_text TEXT,
    pattern_norm TEXT,  -- Normalized for clustering
    category TEXT,      -- Type-specific categorization
    severity TEXT,      -- For risks/failures: 'high', 'medium', 'low'
    modality TEXT,      -- For requirements: 'must', 'should', 'may'
    topic TEXT,
    entities TEXT,      -- JSON array
    confidence REAL,
    metadata TEXT,      -- JSON
    extracted_at TIMESTAMP
);
```

## Example Workflows

### Analyze Document Set

```bash
# 1. Ingest documents
marianalyzer ingest ./rfp_documents

# 2. Build search indexes
marianalyzer build-index

# 3. Extract all patterns
marianalyzer extract all

# 4. Check results
marianalyzer status

# 5. Ask questions
marianalyzer ask "What are the key success factors?"
marianalyzer ask "What risks should we be aware of?"
marianalyzer ask "Compare positive and negative points"
```

### Competitive Analysis

```bash
# Extract all patterns from multiple vendor proposals
marianalyzer ingest ./vendor_proposals

# Extract patterns
marianalyzer extract all

# Compare vendors
marianalyzer ask "What are the success points?"
marianalyzer ask "What are the failure points?"
marianalyzer ask "What's the success/failure ratio?"

# Export specific patterns
marianalyzer list-patterns success_points --limit 50 > success_analysis.txt
marianalyzer list-patterns failure_points --limit 50 > issues_analysis.txt
```

### Risk Assessment

```bash
# Extract risks and constraints
marianalyzer extract risks
marianalyzer extract constraints

# Analyze
marianalyzer ask "What are the high-severity risks?"
marianalyzer ask "What constraints impact delivery?"

# List for review
marianalyzer list-patterns risks --min-confidence 0.75
marianalyzer list-patterns constraints --limit 20
```

## JSON Output

All commands support JSON output for programmatic use:

```bash
marianalyzer ask "What are the success points?" --json > results.json
```

JSON structure:
```json
{
  "query": "What are the success points?",
  "answer": "Here are the top 10 Success Points...",
  "evidence": [
    {
      "pattern_text": "Successfully delivered 15 projects on time",
      "confidence": 0.92,
      "category": "achievement",
      "topic": "project delivery"
    }
  ],
  "metadata": {
    "pattern_type": "success",
    "num_patterns": 10
  }
}
```

## Advanced Features

### Custom Confidence Thresholds

Set per-extraction:
```bash
marianalyzer extract success_points --confidence 0.9
```

Or configure globally in `.env`:
```
REQUIREMENT_CONFIDENCE_THRESHOLD=0.7
```

### Pattern Clustering (Future)

Similar patterns can be clustered into families:
```bash
marianalyzer aggregate --pattern-type success_points
```

### Multi-Language Support (Future)

The system is designed to support multiple languages through configurable keywords.

## Architecture

```
User Question
    ↓
Question Type Detection
    ├─ Comparative? → answer_comparative_question()
    ├─ Pattern-specific? → answer_pattern_question()
    └─ General? → answer_question() [hybrid retrieval]
    ↓
Database Query
    ├─ patterns table (new types)
    └─ requirements table (legacy)
    ↓
Format Response with Evidence
```

## Benefits

1. **Comprehensive Analysis** - Extract multiple insights from documents, not just requirements
2. **Automatic Detection** - Ask natural questions, system figures out what you want
3. **Comparative Insights** - Compare different pattern types across documents
4. **Confidence Scoring** - Every pattern has a confidence score from the LLM
5. **Citation Tracking** - Every pattern links back to source document and location
6. **Flexible Querying** - Ask about specific patterns or combinations

## Next Steps

- Aggregate patterns into families for trend analysis
- Export patterns to CSV/Excel for reporting
- Add pattern visualization (charts, graphs)
- Support custom pattern types via configuration
- Multi-document comparison dashboards
