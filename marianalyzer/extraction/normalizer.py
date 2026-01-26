"""Text normalization for requirement clustering."""

import re


def normalize_requirement(text: str) -> str:
    """Normalize requirement text for clustering.

    Applies transformations to make similar requirements more comparable:
    - Lowercase
    - Remove extra whitespace
    - Remove punctuation except essential ones
    - Normalize numbers (replace with placeholder)
    - Remove articles (a, an, the)

    Args:
        text: Original requirement text

    Returns:
        Normalized text
    """
    # Lowercase
    text = text.lower()

    # Replace numbers with placeholder
    text = re.sub(r'\b\d+(\.\d+)?\b', 'NUM', text)

    # Replace dates with placeholder
    text = re.sub(r'\b\d{4}[-/]\d{2}[-/]\d{2}\b', 'DATE', text)
    text = re.sub(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b', 'DATE', text)

    # Remove articles
    text = re.sub(r'\b(a|an|the)\b', '', text)

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)

    # Remove leading/trailing punctuation
    text = text.strip('.,;:!?')

    # Normalize modal verbs
    text = re.sub(r'\bmust\s+have\b', 'must', text)
    text = re.sub(r'\bshould\s+have\b', 'should', text)
    text = re.sub(r'\bneeds?\s+to\b', 'must', text)
    text = re.sub(r'\bhas\s+to\b', 'must', text)
    text = re.sub(r'\brequired\s+to\b', 'must', text)

    # Remove extra whitespace again
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def extract_keywords(text: str) -> list[str]:
    """Extract keywords from text.

    Args:
        text: Text to extract keywords from

    Returns:
        List of keywords
    """
    # Remove stopwords (basic list)
    stopwords = {
        'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be',
        'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
        'would', 'should', 'could', 'may', 'might', 'can', 'must', 'shall',
    }

    # Tokenize
    words = re.findall(r'\b[a-z]{3,}\b', text.lower())

    # Filter stopwords
    keywords = [w for w in words if w not in stopwords]

    return keywords


def compute_similarity(text1: str, text2: str) -> float:
    """Compute simple Jaccard similarity between two texts.

    Args:
        text1: First text
        text2: Second text

    Returns:
        Similarity score (0.0-1.0)
    """
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())

    if not words1 or not words2:
        return 0.0

    intersection = words1 & words2
    union = words1 | words2

    return len(intersection) / len(union) if union else 0.0
