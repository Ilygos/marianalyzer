"""Company-specific document analyzer with MCP integration."""

__version__ = "0.1.0"

from .config import get_config, set_config
from .models import (
    Chunk,
    Document,
    Heading,
    Playbook,
    Requirement,
    RequirementFamily,
    ValidationResponse,
    ScoreResponse,
)

__all__ = [
    "get_config",
    "set_config",
    "Chunk",
    "Document",
    "Heading",
    "Playbook",
    "Requirement",
    "RequirementFamily",
    "ValidationResponse",
    "ScoreResponse",
]
