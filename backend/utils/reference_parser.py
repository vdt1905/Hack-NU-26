"""
FormatForge AI — Reference Parser Utilities
Parse raw reference strings into structured CSL-JSON.
"""

import re
from typing import Optional

from backend.schemas.docir import AuthorName, ParsedReference


# ── Journal article regex ────────────────────────────────────
# Author, A. A. (Year). Title of article. Title of Journal, Vol(Issue), Pages.
JOURNAL_RE = re.compile(
    r'^(.+?)\s*\((\d{4})\)\.\s*(.+?)\.\s*'
    r'([A-Z][\w\s&:,]+?),\s*(\d+)'
    r'(?:\((\d+)\))?,\s*([\d\-–]+)'
    r'\.(?:\s*(?:https?://)?doi\.org/(.+?))?\.?\s*$'
)

# ── Book regex ───────────────────────────────────────────────
# Author, A. A. (Year). Title of book (Edition). Publisher.
BOOK_RE = re.compile(
    r'^(.+?)\s*\((\d{4})\)\.\s*(.+?)(?:\((.+?)\))?\.?\s*([A-Z][\w\s&]+)\.?\s*$'
)


def parse_reference(text: str) -> ParsedReference:
    """Parse a raw reference string into structured ParsedReference."""
    text = text.strip()
    ref = ParsedReference()

    # Try journal pattern
    m = JOURNAL_RE.match(text)
    if m:
        ref.authors = _parse_authors(m.group(1))
        ref.year = m.group(2)
        ref.title = m.group(3).strip()
        ref.container_title = m.group(4).strip()
        ref.volume = m.group(5)
        ref.issue = m.group(6)
        ref.pages = m.group(7)
        ref.doi = m.group(8).strip() if m.group(8) else None
        ref.ref_type = "article-journal"
        return ref

    # Fallback: extract basic fields
    year_m = re.search(r'\((\d{4})\)', text)
    if year_m:
        ref.year = year_m.group(1)
        auth_part = text[:year_m.start()].strip().rstrip(",").strip()
        ref.authors = _parse_authors(auth_part)

        after = text[year_m.end():].strip().lstrip(".").strip()
        title_m = re.match(r'(.+?)\.', after)
        if title_m:
            ref.title = title_m.group(1).strip()

    return ref


def _parse_authors(author_str: str) -> list[AuthorName]:
    """Parse 'Smith, J., & Jones, A.' into list of AuthorName."""
    authors = []
    parts = re.split(r',\s*&\s*|,\s*and\s*|\s+&\s+|\s+and\s+', author_str)
    for part in parts:
        part = part.strip().rstrip(",").strip()
        if not part:
            continue
        segments = part.split(",", 1)
        if len(segments) == 2:
            authors.append(AuthorName(family=segments[0].strip(), given=segments[1].strip()))
        else:
            authors.append(AuthorName(family=part))
    return authors


def reference_to_csl_json(ref: ParsedReference, cite_id: str = "ref1") -> dict:
    """Convert a ParsedReference to CSL-JSON item format."""
    item: dict = {
        "id": cite_id,
        "type": ref.ref_type or "article-journal",
    }
    if ref.authors:
        item["author"] = [
            {"family": a.family, "given": a.given or ""}
            for a in ref.authors
        ]
    if ref.year:
        item["issued"] = {"date-parts": [[int(ref.year)]]}
    if ref.title:
        item["title"] = ref.title
    if ref.container_title:
        item["container-title"] = ref.container_title
    if ref.volume:
        item["volume"] = ref.volume
    if ref.issue:
        item["issue"] = ref.issue
    if ref.pages:
        item["page"] = ref.pages
    if ref.doi:
        item["DOI"] = ref.doi
    if ref.publisher:
        item["publisher"] = ref.publisher
    return item
