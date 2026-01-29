"""MCP server implementation."""

import asyncio
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from ..config import get_config
from ..store import ChromaStore, SQLiteStore
from ..utils import generate_embedding
from ..validation import score_draft, validate_draft


# Initialize MCP server
app = Server("analyzer")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="get_company_playbook",
            description="Get the company playbook including typical outline, requirement families, and glossary",
            inputSchema={
                "type": "object",
                "properties": {
                    "company_id": {"type": "string", "description": "Company identifier"},
                    "doc_type": {"type": "string", "description": "Document type (e.g., offer_deck, rfp)"},
                },
                "required": ["company_id", "doc_type"],
            },
        ),
        Tool(
            name="retrieve_company_examples",
            description="Retrieve cited examples from historical company documents",
            inputSchema={
                "type": "object",
                "properties": {
                    "company_id": {"type": "string", "description": "Company identifier"},
                    "doc_type": {"type": "string", "description": "Document type"},
                    "query": {"type": "string", "description": "Search query"},
                    "k": {"type": "integer", "description": "Number of results to return", "default": 5},
                },
                "required": ["company_id", "query"],
            },
        ),
        Tool(
            name="validate_draft",
            description="Validate a draft document against company playbook",
            inputSchema={
                "type": "object",
                "properties": {
                    "company_id": {"type": "string", "description": "Company identifier"},
                    "doc_type": {"type": "string", "description": "Document type"},
                    "draft_text": {"type": "string", "description": "The draft document text"},
                },
                "required": ["company_id", "doc_type", "draft_text"],
            },
        ),
        Tool(
            name="score_draft",
            description="Score a draft document against company playbook",
            inputSchema={
                "type": "object",
                "properties": {
                    "company_id": {"type": "string", "description": "Company identifier"},
                    "doc_type": {"type": "string", "description": "Document type"},
                    "draft_text": {"type": "string", "description": "The draft document text"},
                },
                "required": ["company_id", "doc_type", "draft_text"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    
    if name == "get_company_playbook":
        return await get_company_playbook(
            company_id=arguments["company_id"],
            doc_type=arguments["doc_type"],
        )
    
    elif name == "retrieve_company_examples":
        return await retrieve_company_examples(
            company_id=arguments["company_id"],
            query=arguments["query"],
            k=arguments.get("k", 5),
        )
    
    elif name == "validate_draft":
        return await validate_draft_tool(
            company_id=arguments["company_id"],
            doc_type=arguments["doc_type"],
            draft_text=arguments["draft_text"],
        )
    
    elif name == "score_draft":
        return await score_draft_tool(
            company_id=arguments["company_id"],
            doc_type=arguments["doc_type"],
            draft_text=arguments["draft_text"],
        )
    
    else:
        raise ValueError(f"Unknown tool: {name}")


async def get_company_playbook(company_id: str, doc_type: str) -> list[TextContent]:
    """Get company playbook."""
    config = get_config()
    store = SQLiteStore(config.db_path)
    
    playbook = store.get_playbook(company_id, doc_type)
    
    if not playbook:
        return [TextContent(
            type="text",
            text=f"No playbook found for company {company_id} and doc_type {doc_type}",
        )]
    
    # Get requirement families
    families = store.get_requirement_families_by_company(company_id)
    family_dict = {f.family_id: f for f in families}
    
    # Build response
    response = {
        "company_id": company_id,
        "doc_type": doc_type,
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
    
    return [TextContent(
        type="text",
        text=str(response),
    )]


async def retrieve_company_examples(
    company_id: str,
    query: str,
    k: int = 5,
) -> list[TextContent]:
    """Retrieve company examples."""
    config = get_config()
    sqlite_store = SQLiteStore(config.db_path)
    chroma_store = ChromaStore(config.chroma_path)
    
    # Generate query embedding
    query_embedding = generate_embedding(query)
    
    # Search ChromaDB
    results = chroma_store.search_chunks(company_id, query_embedding, top_k=k)
    
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
        "company_id": company_id,
        "query": query,
        "examples": examples,
    }
    
    return [TextContent(
        type="text",
        text=str(response),
    )]


async def validate_draft_tool(
    company_id: str,
    doc_type: str,
    draft_text: str,
) -> list[TextContent]:
    """Validate draft."""
    result = validate_draft(company_id, doc_type, draft_text)
    
    return [TextContent(
        type="text",
        text=result.model_dump_json(indent=2),
    )]


async def score_draft_tool(
    company_id: str,
    doc_type: str,
    draft_text: str,
) -> list[TextContent]:
    """Score draft."""
    result = score_draft(company_id, doc_type, draft_text)
    
    return [TextContent(
        type="text",
        text=result.model_dump_json(indent=2),
    )]


def serve_mcp() -> None:
    """Start the MCP server."""
    asyncio.run(stdio_server(app))
