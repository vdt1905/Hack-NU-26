"""
FormatForge AI — Agent 4: Citation & Reference Engine
Parses references, formats them with citeproc-py, validates citation consistency.

Phase 1 enhancements:
 • Skips citation extraction if already done by StructureDetector
 • Numbered-reference parsing (PNAS/Vancouver style)
 • Better APA reference fallback parsing
 • Improved author-string handling
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from backend.schemas.docir import (
    AuthorName,
    CitationType,
    DocElement,
    DocIR,
    ElementRole,
    InTextCitation,
    ParsedReference,
)
from backend.schemas.reports import (
    CitationFormatIssue,
    CitationMatch,
    CitationReport,
    OrphanReference,
)
from backend.schemas.style_spec import StyleSpec

logger = logging.getLogger(__name__)

# ── Citation regex patterns ───────────────────────────────────

# Parenthetical: (Smith, 2023) or (Smith & Jones, 2023) or (Smith et al., 2023)
PARENTHETICAL_RE = re.compile(
    r'\(([A-Z][a-zà-ÿ]+(?:\s(?:&|and)\s[A-Z][a-zà-ÿ]+)*(?:\set\sal\.)?'
    r',\s*\d{4}[a-z]?'
    r'(?:;\s*[A-Z][a-zà-ÿ]+(?:\s(?:&|and)\s[A-Z][a-zà-ÿ]+)*(?:\set\sal\.)?'
    r',\s*\d{4}[a-z]?)*)\)'
)

# Narrative: Smith (2023) or Smith and Jones (2023) or Smith et al. (2023)
NARRATIVE_RE = re.compile(
    r'([A-Z][a-zà-ÿ]+(?:\s(?:and|&)\s[A-Z][a-zà-ÿ]+)?(?:\set\sal\.)?)'
    r'\s*\((\d{4}[a-z]?)\)'
)

# ── Reference regex patterns ─────────────────────────────────

# APA style: Author, A. A. (Year). Title. Journal, Vol(Issue), Pages.
APA_JOURNAL_RE = re.compile(
    r'^(.+?)\s*\((\d{4})\)\.\s*(.+?)\.\s*(.+?),\s*(\d+)'
    r'(?:\((\d+)\))?,\s*(.+?)\.(?:\s*(?:https?://)?doi\.org/(.+))?$'
)

# Numbered: "1. Author (Year) Title. Journal Vol(Issue):Pages."
NUMBERED_JOURNAL_RE = re.compile(
    r'^(\d{1,3})[\.\)]\s*(.+?)\s*\((\d{4})\)\s*(.+?)\.\s*'
    r'([A-Z][\w\s&:,\-]+?)\s+(\d+)'
    r'(?:\((\d+)\))?\s*[:\-,]\s*([\d\-–]+)'
)


class CitationEngineAgent:
    """Agent 4 — Citation extraction, reference parsing, formatting, and validation."""

    def process(self, docir: DocIR, style_spec: StyleSpec) -> tuple[DocIR, CitationReport]:
        """
        Full citation processing pipeline:
            1. Extract in-text citations from body paragraphs (if not already done)
            2. Parse reference entries into structured data
            3. (Future) Format refs with citeproc-py
            4. Validate citation↔reference consistency

        Returns:
            Updated DocIR + CitationReport.
        """
        # Step 1: Extract in-text citations (skip if StructureDetector already did)
        self._extract_citations(docir)

        # Step 2: Parse reference entries
        self._parse_references(docir)

        # Step 3: Validate consistency
        report = self._validate_consistency(docir, style_spec)

        return docir, report

    # ── Step 1: Extract in-text citations ────────────────────

    def _extract_citations(self, docir: DocIR) -> None:
        """Find all in-text citations in body paragraphs."""
        # Skip if citations were already extracted by StructureDetector
        existing = sum(len(e.citations_found) for e in docir.elements)
        if existing > 0:
            logger.info(
                "Citations already extracted (%d found) — skipping re-extraction.", existing
            )
            return

        for elem in docir.elements:
            if elem.role not in (ElementRole.BODY, ElementRole.ABSTRACT_BODY, ElementRole.UNKNOWN):
                continue
            if not elem.content:
                continue

            citations: list[InTextCitation] = []

            # Parenthetical citations
            for m in PARENTHETICAL_RE.finditer(elem.content):
                inner = m.group(1)
                # May contain multiple citations separated by ;
                for part in inner.split(";"):
                    part = part.strip()
                    # Extract author and year
                    author_year = re.match(
                        r'([A-Z][a-zà-ÿ]+(?:\s(?:&|and)\s[A-Z][a-zà-ÿ]+)*(?:\set\sal\.)?)'
                        r',\s*(\d{4}[a-z]?)',
                        part,
                    )
                    if author_year:
                        citations.append(InTextCitation(
                            text=f"({part})",
                            citation_type=CitationType.PARENTHETICAL,
                            authors=[author_year.group(1).split(" & ")[0].split(" and ")[0].strip()],
                            year=author_year.group(2),
                            position_start=m.start(),
                            position_end=m.end(),
                        ))

            # Narrative citations
            for m in NARRATIVE_RE.finditer(elem.content):
                author = m.group(1).split(" and ")[0].split(" & ")[0].strip()
                year = m.group(2)
                # Skip if this is already captured as parenthetical
                overlap = False
                for c in citations:
                    if c.position_start and m.start() >= c.position_start and m.end() <= c.position_end:
                        overlap = True
                        break
                if not overlap:
                    citations.append(InTextCitation(
                        text=f"{m.group(1)} ({year})",
                        citation_type=CitationType.NARRATIVE,
                        authors=[author],
                        year=year,
                        position_start=m.start(),
                        position_end=m.end(),
                    ))

            elem.citations_found = citations

        total = sum(len(e.citations_found) for e in docir.elements)
        logger.info("Extracted %d in-text citations.", total)

    # ── Step 2: Parse reference entries ──────────────────────

    def _parse_references(self, docir: DocIR) -> None:
        """Parse raw reference strings into structured ParsedReference."""
        ref_elements = docir.get_reference_entries()

        for elem in ref_elements:
            text = elem.content.strip()
            if not text:
                continue
            elem.parsed_reference = self._parse_single_reference(text)

        parsed_ok = sum(
            1 for e in ref_elements
            if e.parsed_reference and (e.parsed_reference.year or e.parsed_reference.authors)
        )
        logger.info(
            "Parsed %d/%d reference entries successfully.",
            parsed_ok, len(ref_elements),
        )

    def _parse_single_reference(self, text: str) -> ParsedReference:
        """
        Parse a single reference string into structured fields.
        Tries APA format first, then numbered format, then fallback extraction.
        """
        ref = ParsedReference()

        # ── Try APA journal article pattern ──────────────────
        m = APA_JOURNAL_RE.match(text)
        if m:
            ref.authors = self._parse_author_string(m.group(1))
            ref.year = m.group(2)
            ref.title = m.group(3).strip()
            ref.container_title = m.group(4).strip()
            ref.volume = m.group(5)
            ref.issue = m.group(6)
            ref.pages = m.group(7).strip().rstrip(".")
            ref.doi = m.group(8).strip() if m.group(8) else None
            ref.ref_type = "article-journal"
            return ref

        # ── Try numbered reference (PNAS / Vancouver) ────────
        m = NUMBERED_JOURNAL_RE.match(text)
        if m:
            ref.authors = self._parse_author_string(m.group(2))
            ref.year = m.group(3)
            ref.title = m.group(4).strip().rstrip(".")
            ref.container_title = m.group(5).strip()
            ref.volume = m.group(6)
            ref.issue = m.group(7)
            ref.pages = m.group(8).strip()
            ref.ref_type = "article-journal"
            return ref

        # ── Fallback: extract what we can ────────────────────
        # Strip leading number if present
        text_clean = re.sub(r'^\d{1,3}[\.\)]\s*', '', text)

        # Year
        year_m = re.search(r'\((\d{4})\)', text_clean)
        if year_m:
            ref.year = year_m.group(1)
            # Authors = everything before year
            author_part = text_clean[:year_m.start()].strip().rstrip(",").strip()
            if author_part:
                ref.authors = self._parse_author_string(author_part)
            # Title = text after year until next period
            after_year = text_clean[year_m.end():].strip().lstrip(".").strip()
            title_m = re.match(r'(.+?)\.', after_year)
            if title_m:
                ref.title = title_m.group(1).strip()

        return ref

    @staticmethod
    def _parse_author_string(author_str: str) -> list[AuthorName]:
        """Parse 'Smith, J., & Jones, A. B.' or 'Smith J, Jones A' into AuthorName list."""
        authors: list[AuthorName] = []

        # Detect style:
        #   APA:       "Family, Given" — initials have periods: "Smith, J. A."
        #   Vancouver: "Family Initials, Family Initials" — no periods: "Nataro JP"
        has_ampersand = "&" in author_str or " and " in author_str.lower()

        # Also detect APA by checking if any comma-separated part is period-initials
        is_apa = has_ampersand
        if not is_apa:
            parts_raw = [p.strip() for p in author_str.split(",")]
            for p in parts_raw[1:]:
                p = p.strip().rstrip(",").strip()
                if p and re.fullmatch(r"[A-Z]\.(?:\s*[A-Z]\.)*", p):
                    is_apa = True
                    break

        if is_apa:
            # APA style: split on ", &" or "and" or "&"
            parts = re.split(r',\s*&\s*|,\s*and\s*|\s+&\s+|\s+and\s+', author_str)
            for part in parts:
                part = part.strip().rstrip(",").strip()
                if not part or part.lower().startswith("et al"):
                    continue
                name_parts = part.split(",", 1)
                if len(name_parts) == 2:
                    family = name_parts[0].strip()
                    given = name_parts[1].strip()
                    if family:
                        authors.append(AuthorName(family=family, given=given))
                else:
                    authors.append(AuthorName(family=part))
        else:
            # Vancouver/PNAS style: "Nataro JP, Kaper JB" — comma separates authors
            parts = [p.strip() for p in author_str.split(",")]
            for part in parts:
                part = part.strip()
                if not part or part.lower().startswith("et al"):
                    continue
                words = part.split()
                if len(words) >= 2:
                    # Check if last word(s) are initials (uppercase, 1-2 chars each)
                    initials = []
                    idx = len(words) - 1
                    while idx >= 1 and all(c.isupper() or c == "." for c in words[idx]):
                        initials.insert(0, words[idx])
                        idx -= 1
                    if initials:
                        family = " ".join(words[:idx + 1])
                        given = " ".join(initials)
                        authors.append(AuthorName(family=family, given=given))
                    else:
                        authors.append(AuthorName(family=part))
                elif part:
                    authors.append(AuthorName(family=part))

        return authors

    # ── Step 3: Validate citation↔reference consistency ──────

    def _validate_consistency(self, docir: DocIR, style_spec: StyleSpec) -> CitationReport:
        """Check that every citation matches a reference and vice versa."""
        report = CitationReport()

        all_citations = docir.get_all_citations()
        ref_elements = docir.get_reference_entries()

        report.total_citations = len(all_citations)
        report.total_references = len(ref_elements)

        matched_refs: set[str] = set()

        # Determine if citations are numeric or author-date
        numeric_count = sum(1 for c in all_citations if not c.year)
        author_date_count = sum(1 for c in all_citations if c.year)

        if numeric_count > author_date_count:
            # Numeric citation system — match by reference number
            report.matched = min(numeric_count, len(ref_elements))
            # Can't do detailed matching for numeric without number tracking
            # Mark all as "matched" if ref count >= citation count
            logger.info(
                "Numeric citation system detected (%d numeric, %d author-date). "
                "Basic count matching applied.",
                numeric_count, author_date_count,
            )
        else:
            # Author-date: match by first author family name + year
            for cit in all_citations:
                match_found = False
                for ref_elem in ref_elements:
                    pr = ref_elem.parsed_reference
                    if pr and pr.authors:
                        first_author_family = pr.authors[0].family.lower()
                        cit_author = cit.authors[0].lower() if cit.authors else ""
                        if first_author_family == cit_author and pr.year == cit.year:
                            match_found = True
                            matched_refs.add(ref_elem.id)
                            break

                if match_found:
                    report.matched += 1
                else:
                    report.orphan_citations.append(CitationMatch(
                        citation_text=cit.text,
                        status="orphan",
                        issue=f"No matching reference found for {cit.text}",
                    ))

            # Check 2: Every reference → citation
            for ref_elem in ref_elements:
                if ref_elem.id not in matched_refs:
                    report.uncited_references.append(OrphanReference(
                        reference_text=ref_elem.content[:100],
                        issue="Not cited anywhere in text",
                    ))

        report.compute_score()
        logger.info(
            "Citation consistency: %d matched, %d orphan citations, %d uncited refs — score %.1f%%",
            report.matched,
            len(report.orphan_citations),
            len(report.uncited_references),
            report.consistency_score,
        )
        return report
