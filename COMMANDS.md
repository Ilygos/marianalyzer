# Command Reference

Complete reference for all `marianalyzer` CLI commands.

## Installation

```bash
pip install -e .
```

## Configuration

Create `.env` file:
```bash
cp .env.example .env
```

Edit `.env`:
```
OLLAMA_HOST=http://localhost:11434
LLM_MODEL=qwen2.5:7b-instruct
EMBED_MODEL=nomic-embed-text
DATA_DIR=./.rfp_rag
```

## Core Commands

### ingest

Ingest documents from a folder.

```bash
marianalyzer ingest <folder> [OPTIONS]
```

**Arguments:**
- `folder` - Path to folder containing documents (required)

**Options:**
- `--recursive` / `--no-recursive` - Scan subdirectories (default: true)

**Examples:**
```bash
# Ingest all documents recursively
marianalyzer ingest ./documents

# Ingest only top-level documents
marianalyzer ingest ./documents --no-recursive
```

### build-index

Build BM25 and vector indexes for search.

```bash
marianalyzer build-index
```

**Examples:**
```bash
marianalyzer build-index
```

### extract

Extract patterns from ingested documents.

```bash
marianalyzer extract <pattern> [OPTIONS]
```

**Arguments:**
- `pattern` - Pattern type to extract:
  - `requirements` - Must/shall/should statements
  - `success_points` - Achievements and accomplishments
  - `failure_points` - Issues, gaps, and weaknesses
  - `risks` - Potential threats and vulnerabilities
  - `constraints` - Limitations and restrictions
  - `all` - Extract all pattern types

**Options:**
- `--confidence`, `-c` - Minimum confidence threshold (0.0-1.0)

**Examples:**
```bash
# Extract all pattern types
marianalyzer extract all

# Extract only high-confidence success points
marianalyzer extract success_points --confidence 0.8

# Extract risks with default confidence
marianalyzer extract risks
```

### aggregate

Cluster similar patterns into families.

```bash
marianalyzer aggregate
```

**Examples:**
```bash
marianalyzer aggregate
```

### ask

Ask questions about the documents.

```bash
marianalyzer ask <question> [OPTIONS]
```

**Arguments:**
- `question` - Your question (required)

**Options:**
- `--json` - Output as JSON
- `--top-k` - Number of results to return (default: 20)
- `--pattern-type`, `-p` - Force specific pattern type (success, failure, risk, constraint, requirement)

**Examples:**
```bash
# Ask about successes
marianalyzer ask "What are the main success points?"

# Ask about risks with JSON output
marianalyzer ask "What risks exist?" --json

# Force pattern type
marianalyzer ask "What are the issues?" --pattern-type failure

# Comparative analysis
marianalyzer ask "Compare successes and failures"

# Get more results
marianalyzer ask "What are the requirements?" --top-k 50
```

### status

Show system statistics.

```bash
marianalyzer status
```

**Examples:**
```bash
marianalyzer status
```

**Output:**
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
└─────────────────────────────┴───────┘

Data Directory: ./.rfp_rag
Database: ./.rfp_rag/rfp_rag.db
Ollama Host: http://localhost:11434
LLM Model: qwen2.5:7b-instruct
```

### list-families

List top requirement families.

```bash
marianalyzer list-families [OPTIONS]
```

**Options:**
- `--top` - Number of families to show (default: 20)

**Examples:**
```bash
# Show top 20 families
marianalyzer list-families

# Show top 50 families
marianalyzer list-families --top 50
```

### list-patterns

List extracted patterns by type.

```bash
marianalyzer list-patterns <pattern_type> [OPTIONS]
```

**Arguments:**
- `pattern_type` - Type of patterns to list (required):
  - `success_points`
  - `failure_points`
  - `risks`
  - `constraints`

**Options:**
- `--limit`, `-n` - Maximum number to show (default: 50)
- `--min-confidence`, `-c` - Minimum confidence (0.0-1.0, default: 0.0)

**Examples:**
```bash
# List all success points
marianalyzer list-patterns success_points

# List top 20 high-confidence failure points
marianalyzer list-patterns failure_points --limit 20 --min-confidence 0.8

# List all risks
marianalyzer list-patterns risks --limit 100
```

**Output:**
```
┌────┬──────────────────────────────────────┬────────────┬────────────┐
│  # │ Pattern Text                         │ Category   │ Confidence │
├────┼──────────────────────────────────────┼────────────┼────────────┤
│  1 │ Successfully delivered 15 projects   │ achievement│       0.92 │
│  2 │ Proven track record in cloud deploy  │ capability │       0.88 │
└────┴──────────────────────────────────────┴────────────┴────────────┘
```

## Complete Workflow

```bash
# 1. Ingest documents
marianalyzer ingest ./documents --recursive

# 2. Build search indexes
marianalyzer build-index

# 3. Extract all patterns
marianalyzer extract all

# 4. Check status
marianalyzer status

# 5. Aggregate patterns
marianalyzer aggregate

# 6. Explore results
marianalyzer list-patterns success_points --limit 20
marianalyzer list-patterns failure_points --limit 20
marianalyzer list-patterns risks

# 7. Ask questions
marianalyzer ask "What are the key success factors?"
marianalyzer ask "What are the main risks?"
marianalyzer ask "Compare positives and negatives"

# 8. Export results
marianalyzer ask "What are all the success points?" --json > success.json
marianalyzer list-patterns failure_points --limit 100 > failures.txt
```

## Global Options

All commands respect these environment variables (from `.env`):

```bash
OLLAMA_HOST=http://localhost:11434
LLM_MODEL=qwen2.5:7b-instruct
EMBED_MODEL=nomic-embed-text
DATA_DIR=./.rfp_rag
CHUNK_SIZE=400
CHUNK_OVERLAP=100
REQUIREMENT_CONFIDENCE_THRESHOLD=0.7
CLUSTERING_THRESHOLD=0.85
LOG_LEVEL=INFO
```

## Tips

1. **Start small** - Test with a few documents first
2. **Check status often** - Monitor extraction progress
3. **Use confidence thresholds** - Filter low-quality extractions
4. **Export results** - Use `--json` for downstream processing
5. **Ask natural questions** - The system detects intent automatically

## Troubleshooting

### "Ollama is not running"
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama if needed
ollama serve
```

### "No patterns found"
```bash
# Make sure you've run extraction first
marianalyzer extract all

# Check status
marianalyzer status
```

### "Database not found"
```bash
# Run ingest to create database
marianalyzer ingest ./documents
```

## Help

Get help for any command:
```bash
marianalyzer --help
marianalyzer extract --help
marianalyzer ask --help
```
