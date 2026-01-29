# PLAN.md — MVP‑1 Company-Specific Generation Quality Booster (No Outcome Labels)

## 0) Objective
Build a **company-specific analyzer** that learns patterns from historical documents (RFP/call-for-offer decks and annexes) and exposes them to a document generator (Claude Code or other) to improve generation quality.

MVP‑1 focuses on:
- **Company playbook** (structure + recurring requirements + terminology)
- **Retrieval of historical exemplars** (cited)
- **Draft validation + quality scoring**
- **MCP tools** for seamless integration

**Explicitly out of scope (MVP‑1):**
- win/loss prediction
- outcome-based ranking
- CRM integration

---

## 1) Target Users & Integration
### 1.1 Primary user
- Your friend’s **document generator** system

### 1.2 Integration method
- Provide an **MCP server** (Tool Gateway) exposing high-level tools.
- Generator calls MCP tools to:
  - fetch company playbook
  - retrieve examples
  - validate drafts
  - score drafts

---

## 2) Inputs / Outputs
### 2.1 Inputs
- `company_id`
- Folder containing documents:
  - `.pdf`, `.docx`, `.xlsx`
  - annexes included (subfolders)
- Optional metadata file (recommended):
  - `company.json` with doc types and folder mapping

### 2.2 Outputs
- SQLite DB: chunks, requirements, headings, playbook artifacts
- ChromaDB: embeddings for chunks and requirements
- MCP endpoints: tools returning JSON with citations

---

## 3) Core Deliverables (MVP‑1)
### 3.1 MCP Server (required)
Expose tools (minimum):

1) `get_company_playbook(company_id, doc_type)`
- Returns:
  - typical outline
  - required/optional sections
  - top recurring requirement families by topic
  - glossary / preferred terminology
  - clause library (if extracted)

2) `retrieve_company_examples(company_id, doc_type, query, k)`
- Returns top‑k cited snippets from historical docs.

3) `validate_draft(company_id, doc_type, draft_text_or_chunks)`
- Returns:
  - issues list (severity, type, message, recommended_fix)
  - evidence references (family IDs + example citations)

4) `score_draft(company_id, doc_type, draft_text_or_chunks)`
- Returns:
  - numeric scores
  - missing sections / missing requirement families
  - terminology compliance indicators

### 3.2 Offline Pipeline CLI (required)
Commands:
- `analyzer ingest <company_id> <folder>`
- `analyzer build-index <company_id>`
- `analyzer extract requirements <company_id>`
- `analyzer build-playbook <company_id>`
- `analyzer serve-mcp`

---

## 4) Architecture (MVP‑1)
### 4.1 High-level components
1) **Ingestor**
- Recursively scans folder
- Detects file type
- Computes hash for incremental updates

2) **Parsers**
- DOCX: headings/paragraphs/tables
- XLSX: sheets + ranges + table extraction
- PDF: page text extraction (OCR optional later)

3) **Chunk Store**
Canonical chunk representation with locators.

4) **Index Layer**
- Vector index (Chroma)
- Optional lexical index (BM25)

5) **Extraction Pipeline**
LLM-assisted requirement extraction with strict JSON schema.

6) **Playbook Builder**
Aggregates headings/requirements into company playbook.

7) **Validator + Scorer**
Deterministic checks + playbook-based checks.

8) **MCP Gateway**
Secure interface to the generator.

---

## 5) Data Model
### 5.1 Canonical chunk schema
Each chunk:
- `chunk_id`
- `doc_id`
- `company_id`
- `chunk_type`: `heading | paragraph | table | sheet_range | page_block`
- `text`
- `structure_path`: e.g. `["2 Scope", "2.3 Requirements"]`
- `locator`: page/sheet/cell indices
- `raw_table` (optional JSON grid)

### 5.2 SQLite tables
Minimum:
- `documents(doc_id, company_id, path, type, sha256, mtime, size, created_at)`
- `chunks(chunk_id, doc_id, company_id, chunk_type, text, structure_path_json, locator_json, raw_table_json)`
- `headings(heading_id, doc_id, company_id, heading_text, heading_norm, level, locator_json)`
- `requirements(req_id, doc_id, chunk_id, company_id, req_text, modality, topic, entities_json, req_norm, confidence, evidence_json)`
- `req_families(family_id, company_id, title, canonical_text, embedding_json, created_at)`
- `req_family_members(family_id, req_id)`
- `glossary(company_id, term, preferred_term, notes, frequency)`
- `playbook(company_id, doc_type, playbook_json, updated_at)`

### 5.3 Vector DB collections
- `chunks_<company_id>`
- `requirements_<company_id>` (optional but recommended)

---

## 6) Models (Local, Ollama)
### 6.1 LLM
Default:
- `qwen2.5:7b-instruct`

Fallbacks:
- `llama3.1:8b`
- `qwen3:4b`

### 6.2 Embeddings
- `nomic-embed-text`

---

## 7) Pipeline Stages (Implementation Plan)
### Stage A — Ingestion (deterministic)
**Input:** folder  
**Output:** `documents`, `chunks`, `headings`

Steps:
- recursive scan
- parse files into chunks
- assign locators
- store in SQLite
- incremental updates via hash:
  - unchanged: skip
  - changed: delete doc_id chunks/reqs then reinsert

Acceptance criteria:
- can ingest 200+ docs reliably
- citations can point to correct page/sheet/section

---

### Stage B — Index build (vector + optional BM25)
**Input:** chunks  
**Output:** Chroma collections

Steps:
- embed chunk texts using Ollama embeddings
- upsert into Chroma with metadata:
  - `company_id`, `doc_id`, `path`, `locator`, `structure_path`
- optional BM25 index for exact match terms

Acceptance criteria:
- `retrieve_company_examples` returns relevant cited snippets

---

### Stage C — Requirement extraction (LLM bounded)
**Input:** chunks  
**Output:** `requirements` rows

Requirement definition (v1):
- sentence/bullet containing: must/shall/required/should (+ configurable list)
- table row with requirement-like headers

Steps:
- heuristic candidate detection
- LLM extraction prompt returns JSON list of requirements
- validate JSON schema
- store requirement rows with evidence locators

Acceptance criteria:
- extraction runs chunk-by-chunk (no global context)
- requirements are stored with evidence

---

### Stage D — Requirement family clustering (recurring patterns)
**Input:** requirements  
**Output:** `req_families` + membership

Steps:
- deterministic normalization `req_norm`
- candidate grouping via lexical signature (simhash/minhash)
- embedding similarity clustering within group
- choose medoid as canonical text
- optional: LLM titles for families (short label)

Acceptance criteria:
- stable “Top recurring requirements” list per company

---

### Stage E — Playbook builder
**Input:** headings + requirement families  
**Output:** `playbook` table

Playbook content:
- typical outline per `doc_type`
- required/optional sections (frequency-based)
- top requirement families by topic
- glossary (preferred terminology)

Acceptance criteria:
- `get_company_playbook` returns consistent JSON

---

### Stage F — Draft validation + scoring
**Input:** draft text (or draft chunks)  
**Output:** issues + scores

Validation checks:
1) Structure
- missing required sections
- wrong ordering (optional)

2) Requirement coverage
- missing top families for relevant topics

3) Terminology compliance
- detect non-preferred variants

4) Consistency checks (deterministic)
- conflicting numbers across sections
- contradictory SLA values
- missing deadlines/owners where expected

5) Specificity heuristics
- too many TBD / vague terms
- missing numbers/dates in critical sections

Scoring outputs:
- `structure_alignment_score`
- `requirement_coverage_score`
- `terminology_score`
- `consistency_score`
- `specificity_score`
- `overall_quality_score` (weighted)

Acceptance criteria:
- validator returns actionable JSON issues with severity

---

## 8) MCP Tool Contracts (JSON)
### 8.1 validate_draft response
```json
{
  "company_id": "acme",
  "doc_type": "offer_deck",
  "issues": [
    {
      "severity": "high",
      "type": "missing_section",
      "message": "Missing section: Security / Compliance",
      "recommended_fix": "Add Security section including ISO27001 clause family REQF-0012",
      "evidence": [
        {
          "family_id": "REQF-0012",
          "canonical_text": "Vendor must provide ISO 27001 certification or equivalent.",
          "examples": [
            {
              "path": ".../RFP_A.pdf",
              "locator": {"page": 12},
              "chunk_id": "CHUNK-..."
            }
          ]
        }
      ]
    }
  ]
}
```

### 8.2 score_draft response
```json
{
  "company_id": "acme",
  "doc_type": "offer_deck",
  "scores": {
    "structure_alignment_score": 0.82,
    "requirement_coverage_score": 0.65,
    "terminology_score": 0.91,
    "consistency_score": 0.97,
    "specificity_score": 0.54,
    "overall_quality_score": 0.76
  },
  "missing": {
    "sections": ["Security / Compliance"],
    "requirement_families": ["REQF-0012", "REQF-0044"]
  }
}
```

---

## 9) Repo Layout (recommended)
```
analyzer/
  src/
    analyzer/
      cli.py
      config.py
      models/                # pydantic schemas
      parsers/               # docx/xlsx/pdf
      store/                 # sqlite + chroma clients
      pipelines/             # ingest/embed/extract/aggregate
      playbook/              # builder + templates
      validation/            # draft validation + scoring
      mcp/                   # MCP server + tool definitions
      utils/
  tests/
  docker/
  pyproject.toml
  README.md
```

---

## 10) Milestones & Timeline
### M1 — Parsing + chunk store (1–2 weeks)
- parsers + locators
- incremental ingestion

### M2 — Retrieval (2–4 days)
- embeddings + Chroma
- retrieval API

### M3 — Requirement extraction (3–5 days)
- prompts + JSON schema validation
- table row extraction

### M4 — Aggregation + playbook (1 week)
- heading stats
- family clustering
- playbook JSON generation

### M5 — MCP gateway + tools (3–5 days)
- tools implemented
- integration examples

### M6 — Draft validation/scoring (1 week)
- deterministic checks
- playbook-based checks

---

## 11) MVP Acceptance Tests
For a sample company corpus:
- `get_company_playbook` returns:
  - typical outline
  - top families by topic
  - glossary
- `retrieve_company_examples` returns relevant cited snippets
- `validate_draft` flags missing major sections and missing recurring families
- `score_draft` outputs stable scores
- generator can call MCP tools end-to-end

---

## 12) Non-goals (MVP‑1)
- No training/fine-tuning
- No win/loss correlation
- No cloud deployment required (local-first)
- No OCR required (optional v2)

---

## 13) Next after MVP‑1
MVP‑2 adds:
- outcome labels (won/lost)
- win/loss insights and “best vs worst” exemplars
- win-likeness scoring
