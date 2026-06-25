"""
File Utility Functions
======================
Helper functions for file handling throughout the application.
Keeping these here means the main logic stays clean and testable.
"""

import hashlib
import os
import uuid
from pathlib import Path


def generate_document_id(filename: str, user_id: str) -> str:
    """
    Generate a stable, unique document ID.
    
    Why hash-based?
    - Same file uploaded twice by same user = same ID
    - Allows deduplication (don't re-embed the same file)
    - Deterministic = easy to reproduce in tests
    
    Why include user_id?
    - Two users uploading the same file get separate document IDs
    - Prevents cross-user data access
    """
    content = f"{user_id}:{filename}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def get_file_extension(filename: str) -> str:
    """
    Extract and normalise file extension.
    
    Examples:
        "report.PDF" → "pdf"
        "data.DOCX"  → "docx"
        "notes.txt"  → "txt"
    """
    return Path(filename).suffix.lstrip(".").lower()


def is_allowed_extension(filename: str, allowed: list[str]) -> bool:
    """Check if a file's extension is in the allowed list."""
    return get_file_extension(filename) in allowed


def safe_filename(filename: str) -> str:
    """
    Sanitise a filename to prevent path traversal attacks.
    
    Attack example without this:
        filename = "../../etc/passwd"
        path = upload_dir / filename
        → Writes to /etc/passwd !
    
    With this function:
        safe_filename("../../etc/passwd") → "etc_passwd"
    """
    # Remove directory separators
    name = os.path.basename(filename)
    # Replace spaces and special chars with underscores
    safe = "".join(c if c.isalnum() or c in ".-_" else "_" for c in name)
    # Remove leading dots (hidden files)
    safe = safe.lstrip(".")
    # Ensure it's not empty
    return safe or "unnamed_file"


def get_unique_filepath(upload_dir: str, filename: str) -> str:
    """
    Generate a unique file path to prevent overwriting existing files.
    
    If "report.pdf" exists, returns "report_a3f2.pdf" instead.
    """
    safe_name = safe_filename(filename)
    base, ext = os.path.splitext(safe_name)
    unique_id = str(uuid.uuid4())[:8]
    unique_name = f"{base}_{unique_id}{ext}"
    return os.path.join(upload_dir, unique_name)


def format_file_size(size_bytes: int) -> str:
    """Human-readable file size string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024**2):.1f} MB"
    else:
        return f"{size_bytes / (1024**3):.1f} GB"