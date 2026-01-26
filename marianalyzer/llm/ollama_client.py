"""Ollama API client for LLM generation and embeddings."""

import json
from typing import Any, Dict, List, Optional

import requests

from marianalyzer.utils.logging_config import get_logger

logger = get_logger()


class OllamaClient:
    """Client for interacting with Ollama API."""

    def __init__(self, host: str = "http://localhost:11434"):
        """Initialize Ollama client.

        Args:
            host: Ollama API host URL
        """
        self.host = host.rstrip("/")
        self.generate_url = f"{self.host}/api/generate"
        self.embed_url = f"{self.host}/api/embed"
        self.tags_url = f"{self.host}/api/tags"

    def check_health(self) -> bool:
        """Check if Ollama is running and accessible.

        Returns:
            True if healthy, False otherwise
        """
        try:
            response = requests.get(self.tags_url, timeout=5)
            return response.status_code == 200
        except requests.RequestException as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    def generate(
        self,
        prompt: str,
        model: str,
        system: Optional[str] = None,
        format: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate text using Ollama.

        Args:
            prompt: Input prompt
            model: Model name (e.g., 'qwen2.5:7b-instruct')
            system: Optional system prompt
            format: Optional response format ('json' for JSON mode)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text

        Raises:
            RuntimeError: If generation fails
        """
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        if system:
            payload["system"] = system

        if format:
            payload["format"] = format

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        try:
            response = requests.post(
                self.generate_url,
                json=payload,
                timeout=120,
            )
            response.raise_for_status()

            data = response.json()
            return data.get("response", "")

        except requests.RequestException as e:
            logger.error(f"Ollama generation failed: {e}")
            raise RuntimeError(f"Ollama generation failed: {e}")

    def generate_json(
        self,
        prompt: str,
        model: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """Generate JSON response with validation and retries.

        Args:
            prompt: Input prompt
            model: Model name
            system: Optional system prompt
            temperature: Sampling temperature
            max_retries: Maximum retry attempts

        Returns:
            Parsed JSON response

        Raises:
            RuntimeError: If all retries fail
        """
        for attempt in range(max_retries):
            try:
                response = self.generate(
                    prompt=prompt,
                    model=model,
                    system=system,
                    format="json",
                    temperature=temperature,
                )

                # Try to parse JSON
                return json.loads(response)

            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    raise RuntimeError(f"Failed to get valid JSON after {max_retries} attempts")

            except Exception as e:
                logger.error(f"Generation error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    raise

        raise RuntimeError("Failed to generate JSON response")

    def embed(
        self,
        texts: List[str],
        model: str,
    ) -> List[List[float]]:
        """Generate embeddings for texts.

        Args:
            texts: List of texts to embed
            model: Embedding model name (e.g., 'nomic-embed-text')

        Returns:
            List of embedding vectors

        Raises:
            RuntimeError: If embedding generation fails
        """
        if not texts:
            return []

        try:
            # Ollama embed API accepts a list of texts
            payload = {
                "model": model,
                "input": texts,
            }

            response = requests.post(
                self.embed_url,
                json=payload,
                timeout=60,
            )
            response.raise_for_status()

            data = response.json()
            embeddings = data.get("embeddings", [])

            if len(embeddings) != len(texts):
                raise RuntimeError(
                    f"Mismatch in embedding count: expected {len(texts)}, got {len(embeddings)}"
                )

            return embeddings

        except requests.RequestException as e:
            logger.error(f"Ollama embedding failed: {e}")
            raise RuntimeError(f"Ollama embedding failed: {e}")

    def list_models(self) -> List[str]:
        """List available models.

        Returns:
            List of model names
        """
        try:
            response = requests.get(self.tags_url, timeout=10)
            response.raise_for_status()

            data = response.json()
            models = data.get("models", [])
            return [m["name"] for m in models]

        except requests.RequestException as e:
            logger.error(f"Failed to list models: {e}")
            return []
