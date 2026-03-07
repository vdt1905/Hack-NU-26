"""
DocLing AI — Citation Parser Utilities
Regex patterns for extracting in-text citations.

Supports:
 • Author-date parenthetical: (Smith, 2023), (Smith & Jones, 2023; Doe, 2021)
 • Author-date narrative:     Smith (2023), Smith et al. (2023)
 • Numeric parenthetical:     (1), (2, 3), (1-5), (1, 3, 7-9)
"""

import re

# ── Author-date parenthetical citations ──────────────────────
# (Smith, 2023)  (Smith & Jones, 2023)  (Smith et al., 2023)
# (Smith, 2023; Jones, 2021)

PARENTHETICAL_SINGLE = re.compile(
    r'\('
    r'([A-Z][a-zà-ÿ]+(?:\s(?:&|and)\s[A-Z][a-zà-ÿ]+)*(?:\set\sal\.)?)'
    r',\s*(\d{4}[a-z]?)'
    r'(?:,\s*(?:p|pp|para)\.\s*[\d\-]+)?'
    r'\)'
)

PARENTHETICAL_MULTI = re.compile(
    r'\('
    r'(?:[A-Z][a-zà-ÿ]+(?:\s(?:&|and)\s[A-Z][a-zà-ÿ]+)*(?:\set\sal\.)?'
    r',\s*\d{4}[a-z]?'
    r'(?:;\s*)?){2,}'
    r'\)'
)

# ── Author-date narrative citations ──────────────────────────
# Smith (2023)  Smith and Jones (2023)  Smith et al. (2023)

NARRATIVE = re.compile(
    r'([A-Z][a-zà-ÿ]+(?:\s(?:and|&)\s[A-Z][a-zà-ÿ]+)?(?:\set\sal\.)?)'
    r'\s*\((\d{4}[a-z]?)\)'
)

# ── Numeric citations ────────────────────────────────────────
# (1), (2, 3), (1-5), (1, 3, 7-9)

NUMERIC_SINGLE = re.compile(
    r'\((\d{1,3})\)'
)

NUMERIC_MULTI = re.compile(
    r'\((\d{1,3}(?:\s*[-–,]\s*\d{1,3})+)\)'
)

NUMERIC_ANY = re.compile(
    r'\((\d{1,3}(?:\s*[-–,]\s*\d{1,3})*)\)'
)

# ── Figure / table references (to exclude from citation matching) ─
FIG_TABLE_PREFIX = re.compile(
    r'(?:Fig\.?|Figure|Table|Tab\.?|Eq\.?|Equation)\s*$',
    re.IGNORECASE,
)

# ── Quick citation presence check ────────────────────────────
HAS_CITATION_AUTHOR_DATE = re.compile(
    r'\([A-Z][a-z]+.*?\d{4}\)|[A-Z][a-z]+\s*\(\d{4}\)'
)

# Backwards-compatible alias
HAS_CITATION = HAS_CITATION_AUTHOR_DATE

HAS_CITATION_NUMERIC = re.compile(
    r'\(\d{1,3}(?:\s*[-–,]\s*\d{1,3})*\)'
)


def has_citations(text: str) -> bool:
    """Quick check whether text contains any citation-like patterns (author-date or numeric)."""
    return bool(HAS_CITATION_AUTHOR_DATE.search(text) or HAS_CITATION_NUMERIC.search(text))


def has_author_date_citations(text: str) -> bool:
    """Check for author-date citation patterns specifically."""
    return bool(HAS_CITATION_AUTHOR_DATE.search(text))


def has_numeric_citations(text: str) -> bool:
    """Check for numeric citation patterns specifically."""
    return bool(HAS_CITATION_NUMERIC.search(text))


def is_figure_reference(text: str, match_start: int) -> bool:
    """Check if a numeric match is actually a figure/table reference, not a citation."""
    prefix = text[max(0, match_start - 10):match_start]
    return bool(FIG_TABLE_PREFIX.search(prefix))
