# Document Analyzer - MVP1

Company-specific document analyzer that learns patterns from historical documents (RFP/call-for-offer decks and annexes) and exposes them via MCP tools to improve document generation quality.

## Features

- **Company Playbook**: Learn typical structure, recurring requirements, and terminology from historical documents
- **Retrieval of Historical Exemplars**: Cite relevant examples from past documents
- **Draft Validation**: Check drafts against company patterns and standards
- **Quality Scoring**: Score drafts on structure, requirements coverage, terminology, and specificity
- **MCP Integration**: Expose tools for seamless integration with document generators
- **Local-first**: Runs entirely on your machine using Ollama
- **Cloud-ready**: Deploy to Google Cloud Run with GPU-accelerated Ollama

## MVP-1 Scope

**In scope:**
- Company playbook (structure + recurring requirements + terminology)
- Retrieval of historical exemplars (cited)
- Draft validation + quality scoring
- MCP tools for integration

**Out of scope:**
- Win/loss prediction
- Outcome-based ranking
- CRM integration

## Requirements

- Python 3.10+
- [Ollama](https://ollama.ai/) running locally
- 8GB+ RAM recommended

## Installation

1. Clone the repository and navigate to the directory:
```bash
cd document_analyzer
```

2. Create virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -e .
```

4. Set up environment:
```bash
cp .env.example .env
# Edit .env with your Ollama settings if needed
```

5. Pull required Ollama models:
```bash
ollama pull qwen2.5:7b-instruct
ollama pull nomic-embed-text
```

## GCP Deployment

Deploy to Google Cloud Run for production use with GPU-accelerated Ollama.

### Quick Deploy

```bash
# 1. Setup GCP project
./deploy/setup-gcp.sh

# 2. Deploy Ollama service (with GPU)
./deploy/deploy-ollama.sh

# 3. Deploy Analyzer service
./deploy/deploy-analyzer.sh
```

### Features

- **GPU-Accelerated**: Ollama runs on NVIDIA L4 GPU for faster inference
- **Auto-scaling**: Both services scale to zero when not in use
- **IAM Authentication**: Secure service-to-service communication
- **HTTP API**: MCP tools exposed via REST endpoints
- **GCS Storage**: Optional Google Cloud Storage for documents

See [DEPLOY_GCP.md](DEPLOY_GCP.md) for detailed deployment instructions, configuration, monitoring, and troubleshooting.

### Testing Cloud Deployment

```bash
# Get service URL
ANALYZER_URL=$(gcloud run services describe analyzer \
  --region=us-central1 \
  --format='value(status.url)')

# Get auth token
TOKEN=$(gcloud auth print-identity-token)

# Test MCP tools
curl -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"company_id":"acme","doc_type":"offer_deck"}' \
  $ANALYZER_URL/tools/get_company_playbook
```

## Usage

### Quick Start - Complete Pipeline

Process all documents for a company in one command:

```bash
analyzer process-all <company_id> <folder_path> [--doc-type offer_deck]
```

This runs all pipeline stages: ingest, index, extract, and build playbook.

### Individual Pipeline Stages

#### 1. Ingest Documents

```bash
analyzer ingest <company_id> <folder_path>
```

Recursively scans and parses PDF, DOCX, and XLSX files. Supports incremental updates (only processes changed files).

Options:
- `--force, -f`: Force re-ingestion of all files

#### 2. Build Vector Index

```bash
analyzer build-index <company_id>
```

Generates embeddings and builds ChromaDB index for semantic search.

Options:
- `--batch-size`: Number of chunks to embed at once (default: 50)

#### 3. Extract Requirements

```bash
analyzer extract <company_id>
```

Uses LLM to extract requirements and specifications from documents.

#### 4. Build Playbook

```bash
analyzer build-playbook <company_id> [--doc-type general]
```

Aggregates patterns into a company playbook including:
- Typical document outline
- Required vs optional sections
- Top recurring requirement families
- Preferred terminology

Options:
- `--doc-type`: Document type (e.g., "offer_deck", "rfp", "general")

### MCP Server

Start the MCP server to expose tools:

**Local (stdio):**
```bash
analyzer serve-mcp
```

**HTTP API (for cloud deployments):**
```bash
python -m analyzer.mcp.server_http
```

The HTTP server exposes MCP tools as REST endpoints on port 8080 (or `$PORT`).

#### Available MCP Tools

1. **get_company_playbook**
   - Returns typical outline, requirement families, and glossary
   - Parameters: `company_id`, `doc_type`

2. **retrieve_company_examples**
   - Returns cited snippets from historical documents
   - Parameters: `company_id`, `query`, `k` (number of results)

3. **validate_draft**
   - Returns validation issues with severity and recommended fixes
   - Parameters: `company_id`, `doc_type`, `draft_text`

4. **score_draft**
   - Returns quality scores and missing elements
   - Parameters: `company_id`, `doc_type`, `draft_text`

### Configuration

View current configuration:

```bash
analyzer config
```

Configuration can be set via environment variables or `.env` file:

```bash
# Paths
DATA_DIR=~/.analyzer/data
DB_PATH=~/.analyzer/data/analyzer.db
CHROMA_PATH=~/.analyzer/data/chroma

# Ollama settings
OLLAMA_HOST=http://localhost:11434
OLLAMA_LLM_MODEL=qwen2.5:7b-instruct
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# LLM settings
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=4096

# Chunk settings
MAX_CHUNK_SIZE=2000
CHUNK_OVERLAP=200

# Retrieval settings
DEFAULT_TOP_K=5
SIMILARITY_THRESHOLD=0.7

# Playbook settings
MIN_SECTION_FREQUENCY=0.3
REQUIRED_SECTION_THRESHOLD=0.8

# GCP settings (optional, for cloud deployment)
GCP_PROJECT_ID=your-project-id
GCP_REGION=us-central1
GCS_BUCKET=your-bucket-name
USE_GCS=false
OLLAMA_SERVICE_URL=https://ollama-xxx.run.app
USE_CLOUD_RUN_AUTH=false
```

## Architecture

### Data Flow

```
Documents → Ingest → Chunks + Headings → Index (Vector DB)
                                       ↓
                                 Extract Requirements
                                       ↓
                              Cluster into Families
                                       ↓
                                 Build Playbook
                                       ↓
                         MCP Tools (validate/score/retrieve)
```

### Components

1. **Ingestor**: Recursively scans folders, detects file types, computes hashes for incremental updates
2. **Parsers**: DOCX (headings/paragraphs/tables), XLSX (sheets/ranges), PDF (pages/text)
3. **Chunk Store**: Canonical chunk representation with locators (SQLite)
4. **Index Layer**: Vector index (ChromaDB) for semantic search
5. **Extraction Pipeline**: LLM-assisted requirement extraction with JSON schema validation
6. **Playbook Builder**: Aggregates headings/requirements into company playbook
7. **Validator + Scorer**: Deterministic and playbook-based checks
8. **MCP Gateway**: Secure interface for document generators

### Data Model

**SQLite Tables:**
- `documents`: Document metadata with hash for change detection
- `chunks`: Canonical chunks with structure paths and locators
- `headings`: Extracted headings with levels
- `requirements`: Extracted requirements with modality and topic
- `req_families`: Clustered requirement families
- `req_family_members`: Requirement-to-family mapping
- `glossary`: Preferred terminology
- `playbook`: Company playbooks by doc_type

**ChromaDB Collections:**
- `chunks_<company_id>`: Vector embeddings for semantic search

## Project Structure

```
src/analyzer/
├── cli.py              # CLI commands and entry points
├── config.py           # Configuration management
├── models/             # Pydantic data models
│   ├── __init__.py
│   └── base.py
├── parsers/            # Document parsers
│   ├── __init__.py
│   ├── base.py
│   ├── docx_parser.py
│   ├── xlsx_parser.py
│   └── pdf_parser.py
├── store/              # Storage layer
│   ├── __init__.py
│   ├── sqlite_store.py
│   └── chroma_store.py
├── pipelines/          # Processing pipelines
│   ├── __init__.py
│   ├── ingest.py
│   ├── index.py
│   ├── extract.py
│   └── aggregate.py
├── playbook/           # Playbook building (future)
├── validation/         # Draft validation and scoring
│   ├── __init__.py
│   ├── validator.py
│   └── scorer.py
├── mcp/                # MCP server
│   ├── __init__.py
│   └── server.py
└── utils/              # Utilities
    ├── __init__.py
    ├── llm.py
    └── text.py
```

## Example Workflow

```bash
# 1. Process a company's documents
analyzer process-all acme ./acme_documents --doc-type offer_deck

# 2. Start MCP server in one terminal
analyzer serve-mcp

# 3. In another terminal/application, use MCP tools to:
#    - Get company playbook
#    - Retrieve examples for inspiration
#    - Validate draft documents
#    - Score draft quality
```

## Development

Install development dependencies:
```bash
pip install -e ".[dev]"
```

Install with GCP support:
```bash
pip install -e ".[gcp]"
```

Run tests:
```bash
pytest tests/ -v
```

Format code:
```bash
black src/
ruff check src/
```

Type checking:
```bash
mypy src/
```

## Next Steps (MVP-2)

Future enhancements will include:
- Outcome labels (won/lost)
- Win/loss insights and "best vs worst" exemplars
- Win-likeness scoring
- More sophisticated requirement clustering
- Glossary term extraction
- Enhanced validation rules

## License

MIT
