# SETUP.md — Local Setup Instructions

## A) Install Ollama
Install Ollama for macOS or Windows.
Verify:
```
ollama --version
```

## B) Pull models
```
ollama pull qwen2.5:7b-instruct
ollama pull nomic-embed-text
```

Optional:
```
ollama pull llama3.1:8b
ollama pull qwen3:4b
```

## C) Python environment
```
python -m venv .venv
```
Activate:
- macOS:
```
source .venv/bin/activate
```
- Windows:
```
.venv\Scripts\Activate.ps1
```

Upgrade pip:
```
python -m pip install --upgrade pip
```

## D) Install dependencies
```
pip install typer pydantic chromadb rank-bm25 pypdf python-docx openpyxl requests
```

## E) Environment variables
Create .env:
```
OLLAMA_HOST=http://localhost:11434
LLM_MODEL=qwen2.5:7b-instruct
EMBED_MODEL=nomic-embed-text
DATA_DIR=./.rfp_rag
```

## F) Run
```
rfp-rag ingest <folder>
rfp-rag build-index
rfp-rag extract requirements
rfp-rag aggregate
rfp-rag ask "Top 20 recurring requirements" --json
```
