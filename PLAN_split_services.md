# PLAN.md — Split‑Service Deployment (Ollama + Vector DB + MCP API)

## 1) Target outcome
Deploy the system as **three services** so you can scale and secure each part independently:

1. **Model Service (Ollama)**  
   Hosts local LLM + embedding model behind an HTTP endpoint.

2. **Data Service (SQL + Vector DB)**  
   Stores parsed chunks, extracted requirements, and embeddings (Chroma + SQLite/DuckDB/Postgres).

3. **Tool Gateway (MCP Server)**  
   Exposes safe, high-level tools to Claude Code (search, top recurring, fetch evidence) and talks to (1) and (2).

This split is designed so that:
- Claude Code never gets raw filesystem access on the server.
- Retrieval/aggregation are deterministic (DB), while LLM usage is bounded.
- You can swap models or DB implementations without changing the MCP contract.

---

## 2) Service responsibilities

### 2.1 Model Service (Ollama)
**Responsibilities**
- `POST /api/embeddings` for embedding generation
- `POST /api/generate` for extraction labeling and optional synthesis

**Models (defaults)**
- LLM: `qwen2.5:7b-instruct`
- Embeddings: `nomic-embed-text`

**Notes**
- Prefer a GPU VM for interactive LLM use.
- Embeddings can run on CPU if needed (slower).

### 2.2 Data Service (SQL + Chroma)
**Responsibilities**
- Store documents/chunks/locators and extracted structured items (requirements, headings)
- Provide fast aggregations: top recurring requirements, topic stats, outline diffs
- Provide semantic retrieval (Chroma) for “find evidence” queries

**Recommended storage**
- SQL: SQLite or DuckDB for single-node MVP; Postgres for multi-user/scale
- Vector: Chroma server with persistent volume

### 2.3 Tool Gateway (MCP Server)
**Responsibilities**
- Implements MCP tools used by Claude Code
- Authn/authz checks (token / API key)
- Translates tool calls into DB queries and/or model calls
- Returns **structured JSON** with **citations**

**Example MCP tools**
- `top_recurring_requirements(n, filters)`
- `search_requirements(query, filters)`
- `get_document_outline(doc_id)`
- `fetch_evidence(evidence_id)`
- `diff_outline(doc_id, baseline="centroid")`

---

## 3) Network & security (minimum viable)
- Put **Tool Gateway** behind HTTPS (reverse proxy like Caddy/Nginx)
- Only Tool Gateway is public; Model + DB services stay private (VPC/subnet)
- Use token auth from Claude Code → Tool Gateway
- Add strict allowlist for tools; never expose “read arbitrary file”

---

## 4) Deployment topology (cloud)
You can deploy on Azure/AWS/GCP using the same shape:

### Option A (simpler): 3 VMs
- VM1 (GPU): Ollama
- VM2 (CPU + disk): SQL + Chroma
- VM3 (CPU): MCP gateway

### Option B (containerized): Kubernetes / ECS / Cloud Run + GPU
- Ollama on a GPU-capable node pool
- Chroma + SQL with persistent volumes
- MCP gateway as stateless deployment

MVP recommendation: **Option A** (3 VMs) to start; containerize after you validate the workflow.

---

## 5) Local development that mirrors split services
Use Docker Compose (or 3 local processes) to mimic production:

- `ollama` (local install is fine; Docker also possible)
- `chroma` container with persistence
- `mcp-gateway` python service
- `worker` job for ingestion/extraction (can run on demand)

This makes macOS/Windows dev consistent.

---

## 6) Ingestion/extraction workflow (incremental)
1. `ingest(folder)` → parse docs into chunks with locators
2. `embed(chunks)` → call Ollama embeddings → upsert into Chroma
3. `extract_requirements(chunks)` → LLM JSON extraction → upsert into SQL
4. `aggregate()` → cluster requirement families + compute counts

**Incremental update rule**
- Use file hash; only reprocess changed files
- On file change: delete previous chunks/reqs for that `doc_id`, then reinsert

---

## 7) Suggested stack (implementation)
- Language: Python 3.11+
- CLI: Typer
- SQL: SQLite/DuckDB (MVP), Postgres (later)
- Vector: Chroma server
- BM25: rank-bm25 (optional but recommended)
- API: FastAPI for MCP gateway
- Schemas: Pydantic models

---

## 8) Trial / “no infra purchase” ways to test split deployment
You can test the split architecture without paid infra using:

### 8.1 Run everything locally (best for correctness)
- macOS/Windows can run Ollama + Chroma + MCP gateway locally.
- This validates architecture and MCP contract before cloud.

### 8.2 Use cloud free trials/credits (short-term, minimal spend)
Common starting credits (subject to change):
- **Google Cloud**: $300 free credits for new customers.
- **Azure**: $200 credit for an Azure free account (typically 30 days).
- **AWS**: AWS Free Tier updates include sign-up credits and earned credits (example: up to $200).
Use these to spin up small VMs and a modest disk, then shut down.

### 8.3 Use “free GPU / low-cost” developer platforms (for quick PoCs)
If you only need a temporary GPU to test throughput:
- Colab/Kaggle-like environments can run CPU/GPU notebooks (ops overhead, not production).
- This is good for benchmarking embeddings/LLM latency, less good for long-running services.

**Recommendation:** start with local split via Docker/localhost, then deploy on one cloud using free credits.

---

## 9) Concrete deliverables for Claude Code
Ask Claude Code to implement in this order:

1. **Core data model + parsers**
   - DOCX/XLSX/PDF to canonical chunk format
   - Locators (page/sheet/cell/section)

2. **Data service**
   - SQL schema + migrations
   - Chroma collection + upsert/delete by doc_id

3. **Worker pipeline**
   - ingest → embed → extract → aggregate
   - incremental updates (hash based)

4. **MCP gateway**
   - Tools returning JSON with evidence
   - Auth + rate limits
   - Logging/tracing for retrieval/extraction

5. **Smoke tests**
   - ingest sample corpus
   - `top_recurring_requirements(20)` returns stable output
   - `fetch_evidence()` returns correct locator/snippet

---

## 10) Operational checklist (MVP)
- Backups: SQL db + Chroma persistent directory
- Observability: structured logs + request IDs
- Cost control: auto-shutdown test VMs; keep disks small
- Security: private network for model/db; public only for gateway
