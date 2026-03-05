"""
FormatForge AI — Text Utilities
Title case, text cleaning, and miscellaneous helpers.
"""

import re
from typing import Optional


# ── Title Case (APA style) ───────────────────────────────────
# Capitalise major words; lowercase minor words unless first/last.

MINOR_WORDS = {
    "a", "an", "and", "as", "at", "but", "by", "for", "if", "in",
    "nor", "of", "on", "or", "so", "the", "to", "up", "yet",
}


def apa_title_case(text: str) -> str:
    """
    Convert text to APA-style title case.
    Major words are capitalised; minor words are lowercase unless first or last.
    """
    words = text.split()
    result = []
    for i, word in enumerate(words):
        clean = word.strip(".:;,!?()")
        if i == 0 or i == len(words) - 1:
            result.append(word.capitalize())
        elif clean.lower() in MINOR_WORDS:
            result.append(word.lower())
        else:
            result.append(word.capitalize())
    return " ".join(result)


def clean_text(text: str) -> str:
    """Remove excessive whitespace and control characters."""
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    text = re.sub(r' +', ' ', text)
    return text.strip()


def word_count(text: str) -> int:
    """Count words in a string."""
    return len(text.split())


def truncate(text: str, max_length: int = 50) -> str:
    """Truncate text to max_length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def inches_to_emu(inches: float) -> int:
    """Convert inches to English Metric Units (EMU)."""
    return int(inches * 914400)


def emu_to_inches(emu: int) -> float:
    """Convert EMU to inches."""
    return round(emu / 914400, 3)


def pt_to_emu(pt: float) -> int:
    """Convert points to EMU."""
    return int(pt * 12700)


def emu_to_pt(emu: int) -> float:
    """Convert EMU to points."""
    return round(emu / 12700, 1)
