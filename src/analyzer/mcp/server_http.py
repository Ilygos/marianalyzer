"""HTTP MCP server implementation for Cloud Run."""

import os
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from ..config import get_config
from ..store import ChromaStore, SQLiteStore
from ..utils import generate_embedding
from ..validation import score_draft, validate_draft


# FastAPI app
app = FastAPI(
    title="Analyzer MCP Server",
    description="MCP server for document analysis and validation",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class PlaybookRequest(BaseModel):
    company_id: str
    doc_type: str


class RetrieveRequest(BaseModel):
    company_id: str
    query: str
    k: int = 5


class ValidateRequest(BaseModel):
    company_id: str
    doc_type: str
    draft_text: str


class ScoreRequest(BaseModel):
    company_id: str
    doc_type: str
    draft_text: str


class ToolListResponse(BaseModel):
    tools: list[Dict[str, Any]]


# Health check
@app.get("/")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "analyzer-mcp"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


# MCP tools as REST endpoints
@app.get("/tools", response_model=ToolListResponse)
async def list_tools():
    """List available MCP tools."""
    return {
        "tools": [
            {
                "name": "get_company_playbook",
                "description": "Get the company playbook including typical outline, requirement families, and glossary",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "company_id": {"type": "string", "description": "Company identifier"},
                        "doc_type": {"type": "string", "description": "Document type (e.g., offer_deck, rfp)"},
                    },
                    "required": ["company_id", "doc_type"],
                },
            },
            {
                "name": "retrieve_company_examples",
                "description": "Retrieve cited examples from historical company documents",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "company_id": {"type": "string", "description": "Company identifier"},
                        "query": {"type": "string", "description": "Search query"},
                        "k": {"type": "integer", "description": "Number of results to return", "default": 5},
                    },
                    "required": ["company_id", "query"],
                },
            },
            {
                "name": "validate_draft",
                "description": "Validate a draft document against company playbook",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "company_id": {"type": "string", "description": "Company identifier"},
                        "doc_type": {"type": "string", "description": "Document type"},
                        "draft_text": {"type": "string", "description": "The draft document text"},
                    },
                    "required": ["company_id", "doc_type", "draft_text"],
                },
            },
            {
                "name": "score_draft",
                "description": "Score a draft document against company playbook",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "company_id": {"type": "string", "description": "Company identifier"},
                        "doc_type": {"type": "string", "description": "Document type"},
                        "draft_text": {"type": "string", "description": "The draft document text"},
                    },
                    "required": ["company_id", "doc_type", "draft_text"],
                },
            },
        ]
    }


@app.post("/tools/get_company_playbook")
async def get_company_playbook(request: PlaybookRequest):
    """Get company playbook."""
    try:
        config = get_config()
        store = SQLiteStore(config.db_path)
        
        playbook = store.get_playbook(request.company_id, request.doc_type)
        
        if not playbook:
            raise HTTPException(
                status_code=404,
                detail=f"No playbook found for company {request.company_id} and doc_type {request.doc_type}"
            )
        
        # Get requirement families
        families = store.get_requirement_families_by_company(request.company_id)
        family_dict = {f.family_id: f for f in families}
        
        # Build response
        response = {
            "company_id": request.company_id,
            "doc_type": request.doc_type,
            "typical_outline": [
                {
                    "section_name": s.section_name,
                    "frequency": s.frequency,
                    "required": s.required,
                }
                for s in playbook.typical_outline
            ],
            "top_requirement_families": [
                {
                    "family_id": fid,
                    "title": family_dict[fid].title if fid in family_dict else "Unknown",
                    "canonical_text": family_dict[fid].canonical_text if fid in family_dict else "",
                }
                for fid in playbook.top_requirement_families[:10]
            ],
            "glossary_terms": playbook.glossary_terms,
        }
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/retrieve_company_examples")
async def retrieve_company_examples(request: RetrieveRequest):
    """Retrieve company examples."""
    try:
        config = get_config()
        sqlite_store = SQLiteStore(config.db_path)
        chroma_store = ChromaStore(config.chroma_path)
        
        # Generate query embedding
        query_embedding = generate_embedding(request.query)
        
        # Search ChromaDB
        results = chroma_store.search_chunks(request.company_id, query_embedding, top_k=request.k)
        
        # Build response with citations
        examples = []
        for i in range(len(results["ids"][0])):
            chunk_id = results["ids"][0][i]
            text = results["documents"][0][i]
            metadata = results["metadatas"][0][i]
            distance = results["distances"][0][i] if "distances" in results else None
            
            examples.append({
                "chunk_id": chunk_id,
                "text": text,
                "doc_id": metadata["doc_id"],
                "path": metadata.get("path", "unknown"),
                "locator": metadata.get("locator", "{}"),
                "similarity": 1 - distance if distance else None,
            })
        
        response = {
            "company_id": request.company_id,
            "query": request.query,
            "examples": examples,
        }
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/validate_draft")
async def validate_draft_endpoint(request: ValidateRequest):
    """Validate draft."""
    try:
        result = validate_draft(request.company_id, request.doc_type, request.draft_text)
        return result.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/score_draft")
async def score_draft_endpoint(request: ScoreRequest):
    """Score draft."""
    try:
        result = score_draft(request.company_id, request.doc_type, request.draft_text)
        return result.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def main():
    """Start the HTTP server."""
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(
        "analyzer.mcp.server_http:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
