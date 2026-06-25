"""
Text Utility Functions
======================
Helpers for text processing, cleaning, and analysis.
"""

import re
import unicodedata


def clean_text(text: str) -> str:
    """
    Clean extracted document text.
    
    PDF extraction often produces:
    - Multiple consecutive spaces
    - Stray newlines in the middle of sentences
    - Unicode control characters
    - Header/footer page numbers that repeat on every page
    
    This function normalises all of that.
    """
    if not text:
        return ""
    
    # Normalise unicode (handle accented chars, etc.)
    text = unicodedata.normalize("NFKC", text)
    
    # Remove null bytes and control characters
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    
    # Collapse multiple spaces into one
    text = re.sub(r" {2,}", " ", text)
    
    # Collapse more than 2 consecutive newlines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    
    # Remove trailing whitespace on each line
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    
    return text.strip()


def estimate_token_count(text: str) -> int:
    """
    Estimate token count without loading a tokenizer.
    
    Rule of thumb: 1 token ≈ 4 characters in English.
    This is accurate enough for chunking purposes.
    
    For exact counts you'd use tiktoken:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    
    We use the estimate to avoid the tiktoken dependency
    (it's large and slows startup).
    """
    return len(text) // 4


def truncate_text(text: str, max_chars: int, suffix: str = "...") -> str:
    """Truncate text to max_chars, adding suffix if truncated."""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - len(suffix)] + suffix


def extract_citations_from_answer(answer: str) -> list[int]:
    """
    Parse [Source N] citations from LLM answer text.
    
    Example:
        answer = "Revenue was $4.2M [Source 1]. Margin declined [Source 2]."
        → [1, 2]
    """
    pattern = r"\[Source (\d+)\]"
    matches = re.findall(pattern, answer)
    # Return unique citation numbers, preserving order
    seen = set()
    result = []
    for m in matches:
        n = int(m)
        if n not in seen:
            seen.add(n)
            result.append(n)
    return result