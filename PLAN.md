# PLAN.md — Local RAG + Pattern Extraction App (Ollama + Cross‑platform)

## 0) Goal
Build a local-first application that:
- Recursively ingests a folder containing RFP / call-for-offer documents (PDF, DOCX, XLSX + annexes).
- Extracts structure + “requirements” (and later other patterns) into a structured store.
- Supports question answering that returns **structured JSON with citations** (file path + page/section/sheet/cell) so Claude Code can post-process and generate reports.

Primary outputs (v1):
- “Top N recurring requirements”
- “Recurring structural patterns”
- “Query + structured answer + evidence”

## 1) Constraints & Principles
- Local models via Ollama (no cloud dependency).
- Works on macOS + Windows.
- Hardware targets:
  - Windows: ~8GB VRAM
  - macOS: 32GB unified memory
- Deterministic processing first; LLM only for bounded tasks.
- Every claim backed by citations.

## 2) Model Selection (Ollama)
### LLM
- qwen2.5:7b-instruct (default)
- llama3.1:8b (alternative)
- qwen3:4b (low-memory fallback)

### Embeddings
- nomic-embed-text

## 3) System Architecture
### Components
1. Ingestor (recursive folder scan)
2. Parsers (DOCX, XLSX, PDF)
3. Chunk Store (canonical format)
4. Indexes (BM25 + vector)
5. Extraction Pipeline (requirements)
6. Aggregator (clustering, counts)
7. QA Engine (JSON answers)

## 4) Data Model (SQLite)
Tables:
- documents
- chunks
- requirements
- req_families
- req_family_members
- headings

## 5) Requirement Extraction (v1)
Definition:
- Sentences with must/shall/required/should
- Table rows with requirement-like columns

Schema:
- req_text
- modality
- topic
- entities
- req_norm
- confidence
- evidence

## 6) Aggregation
- Normalize text
- Cluster by similarity
- Count mentions and documents
- Generate canonical phrasing

## 7) CLI
Commands:
- ingest
- build-index
- extract requirements
- aggregate
- ask

## 8) MVP Milestones
M1: Parsing + chunks  
M2: Retrieval  
M3: Extraction  
M4: Aggregation  
M5: QA  
