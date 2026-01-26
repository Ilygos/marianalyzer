# Marianalyzer

Local RAG system for analyzing and extracting insights from documents using Ollama models. Supports PDF, DOCX, and XLSX files with intelligent requirement extraction and pattern clustering.

## Features

- **Multi-format support**: PDF, DOCX, XLSX documents
- **Local-first**: Runs entirely on your machine using Ollama
- **Pattern extraction**: Automatically identifies key requirements and specifications
- **Intelligent clustering**: Groups similar patterns and requirements across documents
- **Structured Q&A**: Ask questions and get JSON responses with citations
- **Citation tracking**: Every claim backed by file path + page/section/cell references

## Requirements

- Python 3.10+
- [Ollama](https://ollama.ai/) running locally
- 8GB+ VRAM (Windows) or 32GB+ unified memory (macOS)

## Installation

1. Clone the repository:
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
# Edit .env with your Ollama settings
```

5. Pull required Ollama models:
```bash
ollama pull qwen2.5:7b-instruct
ollama pull nomic-embed-text
```

## Usage

### 1. Ingest Documents

```bash
marianalyzer ingest ./my_documents
```

Recursively scans and parses PDF, DOCX, and XLSX files.

### 2. Build Indexes

```bash
marianalyzer build-index
```

Creates BM25 and vector indexes for hybrid search.

### 3. Extract Patterns

```bash
marianalyzer extract requirements
```

Identifies and structures key requirements using LLM.

### 4. Aggregate Similar Patterns

```bash
marianalyzer aggregate
```

Clusters similar requirements into semantic families.

### 5. Ask Questions

```bash
marianalyzer ask "What are the top 20 recurring requirements?" --json
```

Get structured answers with citations.

### Check Status

```bash
marianalyzer status
```

View system statistics and database counts.

## Architecture

```
Ingest → Parse → Chunk → Index → Extract → Aggregate → Q&A
```

- **Ingest**: Recursive folder scanning with deduplication
- **Parse**: Format-specific parsers (PDF/DOCX/XLSX)
- **Chunk**: Sentence-based chunking with overlap
- **Index**: Hybrid BM25 + vector search
- **Extract**: LLM-based pattern and requirement extraction
- **Aggregate**: Semantic clustering and family generation
- **Q&A**: Retrieval-augmented generation with precise citations

## Project Structure

```
marianalyzer/
├── cli.py              # CLI commands and entry points
├── config.py           # Configuration management
├── database.py         # SQLite database operations
├── ingest/             # Document ingestion pipeline
├── parsers/            # PDF, DOCX, XLSX parsers
├── chunking/           # Intelligent text chunking
├── indexing/           # BM25 + ChromaDB vector search
├── llm/                # Ollama LLM & embedding integration
├── extraction/         # Pattern and requirement extraction
├── aggregation/        # Semantic clustering and grouping
├── qa/                 # Question answering with RAG
└── utils/              # Logging, citations, path utilities
```

## Development

Run tests:
```bash
pytest tests/ -v
```

Format code:
```bash
black marianalyzer/
ruff check marianalyzer/
```

## License

MIT
