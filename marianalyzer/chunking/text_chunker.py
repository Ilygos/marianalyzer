"""Text chunking with sentence-based splitting and overlap."""

import re
from typing import List


def chunk_text(
    text: str,
    chunk_size: int = 400,
    overlap: int = 100,
) -> List[str]:
    """Chunk text into overlapping segments.

    Uses simple sentence splitting. For production, consider using
    nltk.sent_tokenize or spacy for better sentence boundary detection.

    Args:
        text: Text to chunk
        chunk_size: Target chunk size in tokens (approximate)
        overlap: Overlap between chunks in tokens (approximate)

    Returns:
        List of text chunks
    """
    # Simple sentence splitting (for production, use NLTK or spaCy)
    sentences = split_into_sentences(text)

    if not sentences:
        return []

    chunks = []
    current_chunk = []
    current_length = 0

    for sentence in sentences:
        sentence_length = len(sentence.split())

        # If adding this sentence exceeds chunk size and we have content
        if current_length + sentence_length > chunk_size and current_chunk:
            # Save current chunk
            chunks.append(" ".join(current_chunk))

            # Start new chunk with overlap
            # Keep last few sentences for overlap
            overlap_sentences = []
            overlap_length = 0
            for s in reversed(current_chunk):
                s_len = len(s.split())
                if overlap_length + s_len <= overlap:
                    overlap_sentences.insert(0, s)
                    overlap_length += s_len
                else:
                    break

            current_chunk = overlap_sentences
            current_length = overlap_length

        current_chunk.append(sentence)
        current_length += sentence_length

    # Add final chunk
    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences using simple regex.

    For production use, consider nltk.sent_tokenize or spacy.

    Args:
        text: Text to split

    Returns:
        List of sentences
    """
    # Simple sentence splitting pattern
    # Matches periods, exclamation marks, question marks followed by space or end
    sentence_endings = re.compile(r'([.!?])\s+')

    sentences = []
    last_end = 0

    for match in sentence_endings.finditer(text):
        sentence = text[last_end:match.end()].strip()
        if sentence:
            sentences.append(sentence)
        last_end = match.end()

    # Add remaining text
    if last_end < len(text):
        remaining = text[last_end:].strip()
        if remaining:
            sentences.append(remaining)

    return sentences if sentences else [text]


def count_tokens(text: str) -> int:
    """Approximate token count by splitting on whitespace.

    Args:
        text: Text to count tokens in

    Returns:
        Approximate token count
    """
    return len(text.split())
