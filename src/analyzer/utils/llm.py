"""LLM utility functions using Ollama."""

import json
from typing import Any, Optional

import ollama

from ..config import get_config


def get_llm_client():
    """Get Ollama client."""
    config = get_config()
    return ollama.Client(host=config.ollama_host)


def generate_completion(
    prompt: str,
    system: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    json_mode: bool = False,
) -> str:
    """Generate completion using Ollama."""
    config = get_config()
    client = get_llm_client()
    
    model = model or config.ollama_llm_model
    temperature = temperature or config.llm_temperature
    max_tokens = max_tokens or config.llm_max_tokens

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    options = {
        "temperature": temperature,
        "num_predict": max_tokens,
    }

    format_arg = "json" if json_mode else ""

    response = client.chat(
        model=model,
        messages=messages,
        options=options,
        format=format_arg,
    )

    return response["message"]["content"]


def generate_embedding(text: str, model: Optional[str] = None) -> list[float]:
    """Generate embedding using Ollama."""
    config = get_config()
    client = get_llm_client()
    
    model = model or config.ollama_embedding_model

    response = client.embeddings(
        model=model,
        prompt=text,
    )

    return response["embedding"]


def extract_json_from_response(response: str) -> Any:
    """Extract JSON from LLM response."""
    # Try to parse as-is first
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # Try to find JSON in code blocks
    if "```json" in response:
        start = response.find("```json") + 7
        end = response.find("```", start)
        json_str = response[start:end].strip()
        return json.loads(json_str)
    
    if "```" in response:
        start = response.find("```") + 3
        end = response.find("```", start)
        json_str = response[start:end].strip()
        return json.loads(json_str)

    raise ValueError("Could not extract JSON from response")
