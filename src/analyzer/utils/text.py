"""Text utility functions."""

import re
from typing import list


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    # Convert to lowercase
    text = text.lower()
    
    # Remove special characters
    text = re.sub(r"[^\w\s]", " ", text)
    
    # Remove extra whitespace
    text = " ".join(text.split())
    
    return text


def extract_keywords(text: str, min_length: int = 3) -> list[str]:
    """Extract keywords from text."""
    # Normalize text
    normalized = normalize_text(text)
    
    # Split into words
    words = normalized.split()
    
    # Filter by length
    keywords = [w for w in words if len(w) >= min_length]
    
    # Remove common stop words (simplified list)
    stop_words = {
        "the", "and", "for", "are", "but", "not", "you", "all", "can", "her",
        "was", "one", "our", "out", "day", "get", "has", "him", "his", "how",
        "man", "new", "now", "old", "see", "two", "way", "who", "boy", "did",
        "its", "let", "put", "say", "she", "too", "use", "this", "that", "with",
        "have", "from", "they", "will", "what", "been", "more", "when", "than",
        "them", "some", "time", "into", "only", "other", "could", "their", "about",
    }
    
    keywords = [k for k in keywords if k not in stop_words]
    
    return keywords
