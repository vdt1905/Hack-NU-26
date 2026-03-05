"""
FormatForge AI — Agent 3: Structure Detector
Labels every DocIR element with a semantic role (title, heading, body, etc.).

Phase 1 — Multi-pass heuristic detection:
  Pass 1  Style-name detection (Word built-in styles)
  Pass 2  Section keyword matching (Results, Discussion, Methods, …)
  Pass 3  Reference section detection (numbered + alphabetical)
  Pass 4  Title detection (position-based)
  Pass 5  Author / affiliation detection
  Pass 6  Abstract detection (positional)
  Pass 7  Keywords detection
  Pass 8  Fill remaining UNKNOWN → BODY
  Pass 9  Extract in-text citations (numeric + author-date)
  Pass 10 (optional) LLM fallback for remaining UNKNOWN
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from backend.schemas.docir import (
    CitationType,
    DocElement,
    DocIR,
    ElementRole,
    ElementType,
    InTextCitation,
)

logger = logging.getLogger(__name__)

# ── Section heading keywords ──────────────────────────────────

SECTION_KEYWORDS: dict[str, ElementRole] = {
    "abstract": ElementRole.ABSTRACT_LABEL,
    "introduction": ElementRole.HEADING_1,
    "background": ElementRole.HEADING_1,
    "literature review": ElementRole.HEADING_1,
    "related work": ElementRole.HEADING_1,
    "theoretical framework": ElementRole.HEADING_1,
    "methods": ElementRole.HEADING_1,
    "methodology": ElementRole.HEADING_1,
    "materials and methods": ElementRole.HEADING_1,
    "experimental methods": ElementRole.HEADING_1,
    "experimental procedures": ElementRole.HEADING_1,
    "study design": ElementRole.HEADING_2,
    "participants": ElementRole.HEADING_2,
    "procedure": ElementRole.HEADING_2,
    "measures": ElementRole.HEADING_2,
    "data analysis": ElementRole.HEADING_2,
    "data collection": ElementRole.HEADING_2,
    "results": ElementRole.HEADING_1,
    "findings": ElementRole.HEADING_1,
    "results and discussion": ElementRole.HEADING_1,
    "discussion": ElementRole.HEADING_1,
    "general discussion": ElementRole.HEADING_1,
    "conclusion": ElementRole.HEADING_1,
    "conclusions": ElementRole.HEADING_1,
    "summary": ElementRole.HEADING_1,
    "significance": ElementRole.HEADING_1,
    "implications": ElementRole.HEADING_2,
    "limitations": ElementRole.HEADING_2,
    "future work": ElementRole.HEADING_2,
    "future directions": ElementRole.HEADING_2,
    "future research": ElementRole.HEADING_2,
    "data availability": ElementRole.HEADING_2,
    "ethical considerations": ElementRole.HEADING_2,
    "acknowledgements": ElementRole.HEADING_1,
    "acknowledgments": ElementRole.HEADING_1,
    "references": ElementRole.REFERENCE_LABEL,
    "bibliography": ElementRole.REFERENCE_LABEL,
    "works cited": ElementRole.REFERENCE_LABEL,
    "appendix": ElementRole.APPENDIX,
    "appendix a": ElementRole.APPENDIX,
    "appendix b": ElementRole.APPENDIX,
    "appendix c": ElementRole.APPENDIX,
    "appendices": ElementRole.APPENDIX,
    "supplementary material": ElementRole.APPENDIX,
    "supplementary materials": ElementRole.APPENDIX,
    "supporting information": ElementRole.APPENDIX,
}

# Compiled keyword regex for quick look-up
KEYWORDS_PATTERN = re.compile(r"^keywords?\s*[:\-–]", re.IGNORECASE)

# Affiliation / institution patterns
AFFILIATION_RE = re.compile(
    r"(?:university|department|school|institute|college|laboratory|"
    r"center|centre|faculty|hospital|academy|national\s+institutes?|"
    r"research\s+council)",
    re.IGNORECASE,
)

# Numbered reference at start of line:  "1. Author" or "1 Author"
NUMBERED_REF_RE = re.compile(r"^\d{1,3}[\.\)]\s*[A-Z]")

# ── Citation regex patterns ───────────────────────────────────

# Numeric:  (1)  (2, 3)  (1–5)  (1, 2, 5–8)
NUMERIC_CITATION_RE = re.compile(
    r"\((\d{1,3}(?:\s*[,;–\-]\s*\d{1,3})*)\)"
)

# Author-date parenthetical:  (Smith, 2023)  (Smith & Jones, 2023; Doe, 2021)
AUTHOR_DATE_PAREN_RE = re.compile(
    r"\(([A-Z][a-zà-ÿ]+(?:\s(?:&|and)\s[A-Z][a-zà-ÿ]+)*(?:\set\sal\.)?"
    r",\s*\d{4}[a-z]?"
    r"(?:;\s*[A-Z][a-zà-ÿ]+(?:\s(?:&|and)\s[A-Z][a-zà-ÿ]+)*(?:\set\sal\.)?"
    r",\s*\d{4}[a-z]?)*)\)"
)

# Author-date narrative:  Smith (2023)  Smith and Jones (2023)
AUTHOR_DATE_NARR_RE = re.compile(
    r"([A-Z][a-zà-ÿ]+(?:\s(?:and|&)\s[A-Z][a-zà-ÿ]+)?(?:\set\sal\.)?)"
    r"\s*\((\d{4}[a-z]?)\)"
)

# Figure / table cross-references (to ignore during numeric-citation extraction)
FIG_TABLE_PREFIX_RE = re.compile(r"(?:Fig\.?|Figure|Table|Tab\.?|Eq\.?)\s*$", re.IGNORECASE)


class StructureDetectorAgent:
    """Agent 3 — Detect and label the structural roles of document elements."""

    def __init__(self, use_llm: bool = False):
        """
        Args:
            use_llm: If True, run LLM fallback for remaining UNKNOWN elements.
        """
        self.use_llm = use_llm

    # ── Public API ───────────────────────────────────────────

    def detect(self, docir: DocIR) -> DocIR:
        """
        Label every element in the DocIR with a semantic role.

        Returns the same DocIR with `role` & `role_confidence` updated.
        """
        elements = docir.elements
        if not elements:
            return docir

        # Multi-pass detection (order matters)
        self._pass1_style_names(elements)
        self._pass2_section_keywords(elements)
        self._pass3_reference_section(elements)
        self._pass4_title_detection(elements)
        self._pass5_author_affiliation(elements)
        self._pass6_abstract_detection(elements)
        self._pass7_keywords_detection(elements)
        self._pass8_fill_remaining(elements)
        self._pass9_extract_citations(elements)

        if self.use_llm:
            self._pass10_llm_fallback(elements)

        labelled = sum(1 for e in elements if e.role != ElementRole.UNKNOWN)
        total = len(elements)
        logger.info(
            "Structure detection complete — %d/%d elements labelled (%.0f%%)",
            labelled, total, 100 * labelled / total if total else 0,
        )
        return docir

    # ── Pass 1: Word style-name detection ────────────────────

    def _pass1_style_names(self, elements: list[DocElement]) -> None:
        """Use built-in Word style names (Title, Heading 1, …) when available."""
        for elem in elements:
            if elem.type != ElementType.PARAGRAPH:
                continue
            style = (elem.original_style_name or "").lower()

            if "title" in style and "subtitle" not in style:
                elem.role = ElementRole.TITLE
                elem.role_confidence = 0.92
            elif "heading" in style:
                level = self._extract_heading_level(style)
                elem.role = self._heading_role(level)
                elem.role_confidence = 0.88
            elif "abstract" in style:
                elem.role = ElementRole.ABSTRACT_BODY
                elem.role_confidence = 0.85

    # ── Pass 2: Section keyword matching ─────────────────────

    def _pass2_section_keywords(self, elements: list[DocElement]) -> None:
        """Match short standalone paragraphs to known section names."""
        for elem in elements:
            if elem.type != ElementType.PARAGRAPH:
                continue
            if elem.role != ElementRole.UNKNOWN:
                continue

            text = elem.content.strip()
            if not text:
                continue

            word_count = len(text.split())
            text_lower = text.lower().strip()

            # Try exact match (with/without trailing period)
            for candidate in (text_lower, text_lower.rstrip(".")):
                if word_count <= 8 and candidate in SECTION_KEYWORDS:
                    elem.role = SECTION_KEYWORDS[candidate]
                    elem.role_confidence = 0.85
                    break

            # ACKNOWLEDGMENTS header (sometimes all-caps with period)
            if elem.role == ElementRole.UNKNOWN:
                upper = text.upper().rstrip(".")
                if upper in ("ACKNOWLEDGMENTS", "ACKNOWLEDGEMENTS") and word_count <= 3:
                    elem.role = ElementRole.HEADING_1
                    elem.role_confidence = 0.85

    # ── Pass 3: Reference section ────────────────────────────

    def _pass3_reference_section(self, elements: list[DocElement]) -> None:
        """Detect reference-label and mark subsequent entries."""

        # 1. Find the first element already labelled as REFERENCE_LABEL
        ref_label_idx = self._find_role_index(elements, ElementRole.REFERENCE_LABEL)

        # 2. If not found, try to locate by numbered-reference pattern
        if ref_label_idx is None:
            ref_label_idx = self._detect_reference_start_by_pattern(elements)

        if ref_label_idx is None:
            return

        # 3. Mark entries after the label
        for i in range(ref_label_idx + 1, len(elements)):
            elem = elements[i]
            if elem.type != ElementType.PARAGRAPH:
                continue
            text = elem.content.strip()
            if not text:
                continue
            # Stop at another major heading / appendix
            if elem.role in (
                ElementRole.HEADING_1, ElementRole.HEADING_2,
                ElementRole.APPENDIX, ElementRole.ABSTRACT_LABEL,
            ):
                break
            if elem.role == ElementRole.UNKNOWN:
                elem.role = ElementRole.REFERENCE_ENTRY
                elem.role_confidence = 0.75

    def _detect_reference_start_by_pattern(
        self, elements: list[DocElement]
    ) -> Optional[int]:
        """Walk backwards from end to find block of numbered references.

        Handles PDF-to-DOCX documents where each reference may span multiple
        paragraphs (continuation lines between numbered entries).
        """
        ref_indices: list[int] = []
        gap = 0  # non-matching lines since last numbered ref

        for i in range(len(elements) - 1, -1, -1):
            elem = elements[i]
            if elem.type != ElementType.PARAGRAPH:
                continue
            text = elem.content.strip()
            if not text:
                continue

            if NUMBERED_REF_RE.match(text):
                ref_indices.append(i)
                gap = 0
            elif ref_indices:
                # Already found some refs — track the gap
                gap += 1
                if gap > 6:
                    break
                # Stop at section headings
                text_lower = text.lower().rstrip(".")
                if text_lower in SECTION_KEYWORDS:
                    break

        if len(ref_indices) >= 3:
            first_ref_idx = min(ref_indices)
            # Look for a label paragraph just above
            for j in range(max(0, first_ref_idx - 5), first_ref_idx):
                jtext = elements[j].content.strip().lower().rstrip(".")
                if jtext in ("references", "bibliography", "works cited"):
                    elements[j].role = ElementRole.REFERENCE_LABEL
                    elements[j].role_confidence = 0.80
                    return j
            # No label found → use the index before first ref as virtual label
            return first_ref_idx - 1

        return None

    # ── Pass 4: Title detection ──────────────────────────────

    def _pass4_title_detection(self, elements: list[DocElement]) -> None:
        """Identify the paper title from the first paragraphs."""

        # Skip if a title is already detected (e.g. from style names)
        if any(e.role == ElementRole.TITLE for e in elements):
            return

        # Find the first heading / abstract / reference label
        first_heading_idx = self._first_section_index(elements)
        search_limit = min(first_heading_idx, 15)  # only look in first 15 elements

        title_started = False
        for i in range(search_limit):
            elem = elements[i]
            if elem.type != ElementType.PARAGRAPH or elem.role != ElementRole.UNKNOWN:
                continue
            text = elem.content.strip()
            if not text:
                if title_started:
                    break  # blank line ends title
                continue

            if not title_started:
                # First non-empty UNKNOWN paragraph
                if not self._looks_like_author(text):
                    elem.role = ElementRole.TITLE
                    elem.role_confidence = 0.70
                    title_started = True
                else:
                    break  # very first thing is author-like → no title detected
            else:
                # Title continuation (wrapped lines common in PDF→DOCX)
                if self._looks_like_author(text):
                    break
                words = text.split()
                if len(words) <= 20 and not text[0].isdigit():
                    elem.role = ElementRole.TITLE
                    elem.role_confidence = 0.60
                else:
                    break

    # ── Pass 5: Author & affiliation ─────────────────────────

    def _pass5_author_affiliation(self, elements: list[DocElement]) -> None:
        """Detect author names and institutional affiliations after the title."""

        # Find title zone end
        title_end = -1
        for i, elem in enumerate(elements):
            if elem.role == ElementRole.TITLE:
                title_end = i
        if title_end < 0:
            return

        first_heading_idx = self._first_section_index(elements, after=title_end + 1)
        author_zone_end = min(title_end + 30, first_heading_idx)

        for i in range(title_end + 1, author_zone_end):
            elem = elements[i]
            if elem.type != ElementType.PARAGRAPH or elem.role != ElementRole.UNKNOWN:
                continue
            text = elem.content.strip()
            if not text:
                continue

            # Author names (short, comma-separated, proper nouns)
            if self._looks_like_author(text):
                elem.role = ElementRole.AUTHOR_INFO
                elem.role_confidence = 0.60
                continue

            # Affiliation (university / department / institute …)
            if AFFILIATION_RE.search(text):
                elem.role = ElementRole.AUTHOR_INFO
                elem.role_confidence = 0.55
                continue

            # Single-character superscript markers: "a", "b", "1"
            if len(text) <= 2 and (text.isalpha() or text.isdigit()):
                elem.role = ElementRole.AUTHOR_INFO
                elem.role_confidence = 0.40
                continue

            # Editor / date metadata
            tl = text.lower()
            if tl.startswith("edited by") or tl.startswith("received") or tl.startswith("approved"):
                elem.role = ElementRole.AUTHOR_INFO
                elem.role_confidence = 0.50
                continue

            # Stop when we hit a long body-like paragraph
            if len(text.split()) > 25:
                break

    # ── Pass 6: Abstract detection ───────────────────────────

    def _pass6_abstract_detection(self, elements: list[DocElement]) -> None:
        """Identify abstract paragraphs between front-matter and first heading."""

        # End of title / author zone
        front_matter_end = 0
        for i, elem in enumerate(elements):
            if elem.role in (ElementRole.TITLE, ElementRole.AUTHOR_INFO):
                front_matter_end = i

        # Find first non-abstract heading after front matter
        first_heading_idx = self._first_section_index(
            elements, after=front_matter_end + 1, skip_abstract_label=True,
        )
        if first_heading_idx <= front_matter_end + 1:
            return  # nothing between front matter and heading

        # If an ABSTRACT_LABEL exists, mark paragraphs after it
        abstract_label_idx = None
        for i in range(front_matter_end + 1, first_heading_idx):
            if elements[i].role == ElementRole.ABSTRACT_LABEL:
                abstract_label_idx = i
                break

        start = (abstract_label_idx + 1) if abstract_label_idx is not None else (front_matter_end + 1)

        abstract_started = False
        for i in range(start, first_heading_idx):
            elem = elements[i]
            if elem.type != ElementType.PARAGRAPH or elem.role != ElementRole.UNKNOWN:
                continue
            text = elem.content.strip()
            if not text:
                continue
            # Skip very short lines unless abstract already started
            if len(text.split()) < 4 and not abstract_started:
                continue
            # Skip keywords lines
            if KEYWORDS_PATTERN.match(text):
                continue

            elem.role = ElementRole.ABSTRACT_BODY
            elem.role_confidence = 0.55 if abstract_label_idx else 0.45
            abstract_started = True

    # ── Pass 7: Keywords ─────────────────────────────────────

    def _pass7_keywords_detection(self, elements: list[DocElement]) -> None:
        """Detect keyword lines (e.g. 'Keywords: term1 | term2 | …')."""
        for elem in elements:
            if elem.type != ElementType.PARAGRAPH:
                continue
            text = elem.content.strip()
            if not text:
                continue

            if KEYWORDS_PATTERN.match(text):
                elem.role = ElementRole.KEYWORDS
                elem.role_confidence = 0.85
                continue

            # Pipe-separated terms between front-matter and first heading
            if elem.role in (ElementRole.UNKNOWN, ElementRole.ABSTRACT_BODY) and "|" in text:
                parts = [p.strip() for p in text.split("|")]
                if 3 <= len(parts) <= 12 and all(len(p.split()) <= 6 for p in parts if p):
                    elem.role = ElementRole.KEYWORDS
                    elem.role_confidence = 0.60

    # ── Pass 8: Fill remaining → BODY ────────────────────────

    def _pass8_fill_remaining(self, elements: list[DocElement]) -> None:
        """Assign BODY to all remaining UNKNOWN paragraphs with content."""
        in_references = False
        for elem in elements:
            if elem.role == ElementRole.REFERENCE_LABEL:
                in_references = True
                continue
            if in_references and elem.role in (
                ElementRole.HEADING_1, ElementRole.HEADING_2, ElementRole.APPENDIX,
            ):
                in_references = False

            if elem.type != ElementType.PARAGRAPH:
                continue

            if elem.role == ElementRole.UNKNOWN:
                text = elem.content.strip()
                if not text:
                    elem.role_confidence = 0.0
                elif in_references:
                    elem.role = ElementRole.REFERENCE_ENTRY
                    elem.role_confidence = 0.60
                else:
                    elem.role = ElementRole.BODY
                    elem.role_confidence = 0.30

    # ── Pass 9: Citation extraction ──────────────────────────

    def _pass9_extract_citations(self, elements: list[DocElement]) -> None:
        """Extract in-text citations from body and abstract paragraphs."""
        total_citations = 0

        for elem in elements:
            if elem.role not in (
                ElementRole.BODY, ElementRole.ABSTRACT_BODY,
            ):
                continue
            if not elem.content:
                continue

            citations: list[InTextCitation] = []

            # ── Numeric citations: (1), (2, 3), (1–5) ───────
            for m in NUMERIC_CITATION_RE.finditer(elem.content):
                inner = m.group(1).strip()
                # Ignore figure / table cross-references
                pre_text = elem.content[max(0, m.start() - 8): m.start()]
                if FIG_TABLE_PREFIX_RE.search(pre_text):
                    continue
                # Ignore standalone 4-digit years (could be date, not citation)
                if re.fullmatch(r"\d{4}", inner):
                    continue

                citations.append(InTextCitation(
                    text=m.group(0),
                    citation_type=CitationType.PARENTHETICAL,
                    authors=[],
                    year=None,
                    position_start=m.start(),
                    position_end=m.end(),
                ))

            # ── Author-date parenthetical: (Smith, 2023) ────
            for m in AUTHOR_DATE_PAREN_RE.finditer(elem.content):
                inner = m.group(1)
                for part in inner.split(";"):
                    part = part.strip()
                    ay = re.match(
                        r"([A-Z][a-zà-ÿ]+(?:\s(?:&|and)\s[A-Z][a-zà-ÿ]+)*"
                        r"(?:\set\sal\.)?),\s*(\d{4}[a-z]?)",
                        part,
                    )
                    if ay:
                        citations.append(InTextCitation(
                            text=f"({part})",
                            citation_type=CitationType.PARENTHETICAL,
                            authors=[ay.group(1).split(" & ")[0].split(" and ")[0].strip()],
                            year=ay.group(2),
                            position_start=m.start(),
                            position_end=m.end(),
                        ))

            # ── Author-date narrative: Smith (2023) ──────────
            for m in AUTHOR_DATE_NARR_RE.finditer(elem.content):
                author = m.group(1).split(" and ")[0].split(" & ")[0].strip()
                year = m.group(2)
                overlap = any(
                    c.position_start is not None
                    and c.position_start <= m.start() < (c.position_end or 0)
                    for c in citations
                )
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
            total_citations += len(citations)

        logger.info("Extracted %d in-text citations.", total_citations)

    # ── Pass 10: LLM fallback (optional) ─────────────────────

    def _pass10_llm_fallback(self, elements: list[DocElement]) -> None:
        """Use LLM to classify remaining UNKNOWN elements."""
        unknowns = [
            (i, e) for i, e in enumerate(elements)
            if e.role == ElementRole.UNKNOWN and e.content.strip()
        ]
        if not unknowns:
            return

        try:
            from backend.llm.client import get_llm_client
            from backend.llm.prompts import STRUCTURE_CLASSIFY_SYSTEM, STRUCTURE_CLASSIFY_USER

            client = get_llm_client()

            for idx, elem in unknowns[:20]:  # limit LLM calls
                ctx_start = max(0, idx - 2)
                ctx_end = min(len(elements), idx + 3)
                context_lines = []
                for j in range(ctx_start, ctx_end):
                    prefix = ">>> " if j == idx else "    "
                    context_lines.append(
                        f"{prefix}[{elements[j].role.value}] "
                        f"{elements[j].content[:100]}"
                    )
                context = "\n".join(context_lines)

                font_info = f"{elem.formatting.font_name or '?'} " \
                            f"{elem.formatting.font_size_pt or '?'}pt"
                if elem.formatting.bold:
                    font_info += " bold"
                if elem.formatting.italic:
                    font_info += " italic"

                user_prompt = STRUCTURE_CLASSIFY_USER.format(
                    context=context,
                    target=elem.content[:200],
                    style_name=elem.original_style_name or "Normal",
                    font_info=font_info,
                )

                try:
                    result = client.chat_json(
                        system_prompt=STRUCTURE_CLASSIFY_SYSTEM,
                        user_prompt=user_prompt,
                        temperature=0.1,
                        max_tokens=100,
                    )
                    role_str = result.get("role", "unknown")
                    confidence = float(result.get("confidence", 0.5))
                    try:
                        elem.role = ElementRole(role_str)
                        elem.role_confidence = confidence
                    except ValueError:
                        pass
                except Exception as exc:
                    logger.debug("LLM classify failed for %s: %s", elem.id, exc)
        except Exception as exc:
            logger.warning("LLM fallback unavailable: %s", exc)

    # ── Helper utilities ─────────────────────────────────────

    @staticmethod
    def _extract_heading_level(style: str) -> int:
        m = re.search(r"(\d)", style)
        return int(m.group(1)) if m else 1

    @staticmethod
    def _heading_role(level: int) -> ElementRole:
        mapping = {
            1: ElementRole.HEADING_1,
            2: ElementRole.HEADING_2,
            3: ElementRole.HEADING_3,
            4: ElementRole.HEADING_4,
            5: ElementRole.HEADING_5,
        }
        return mapping.get(level, ElementRole.HEADING_1)

    @staticmethod
    def _find_role_index(elements: list[DocElement], role: ElementRole) -> Optional[int]:
        """Return the index of the first element with the given role, or None."""
        for i, e in enumerate(elements):
            if e.role == role:
                return i
        return None

    def _first_section_index(
        self,
        elements: list[DocElement],
        after: int = 0,
        skip_abstract_label: bool = False,
    ) -> int:
        """Return index of the first heading / label after *after*, or len(elements)."""
        heading_roles = {
            ElementRole.HEADING_1, ElementRole.HEADING_2, ElementRole.HEADING_3,
            ElementRole.HEADING_4, ElementRole.HEADING_5,
            ElementRole.REFERENCE_LABEL, ElementRole.ABSTRACT_LABEL,
            ElementRole.APPENDIX,
        }
        for i in range(after, len(elements)):
            if elements[i].role in heading_roles:
                if skip_abstract_label and elements[i].role == ElementRole.ABSTRACT_LABEL:
                    continue
                return i
        return len(elements)

    @staticmethod
    def _looks_like_author(text: str) -> bool:
        """Heuristic: does this text look like an author-name line?"""
        if len(text) <= 2:
            return True
        words = text.split()
        if len(words) > 25:
            return False
        # "Smith, J." or "Smith, J. A." pattern
        if re.search(r"[A-Z][a-z]+,?\s+[A-Z]\.", text):
            return True
        # Superscript-like markers adjacent to names  ("Sadia Ahmad a")
        if re.search(r"[a-z]\s*,\s*[A-Z]", text) and len(words) <= 15:
            return True
        # Trailing single-char superscript: "Ghadah Alsharif a", "Mohammad Islam b"
        if (re.search(r"[A-Z][a-z]+\s+[a-z]$", text)
                and 2 <= len(words) <= 8):
            return True
        # "and" connecting proper names
        if " and " in text and len(words) <= 15:
            if re.search(r"[A-Z][a-z]+ (?:and|&) [A-Z][a-z]+", text):
                return True
        return False

    @staticmethod
    def _is_heading_like(elem: DocElement) -> bool:
        """Quick check if element looks like a heading."""
        heading_roles = {
            ElementRole.HEADING_1, ElementRole.HEADING_2, ElementRole.HEADING_3,
            ElementRole.HEADING_4, ElementRole.HEADING_5,
            ElementRole.REFERENCE_LABEL, ElementRole.ABSTRACT_LABEL,
        }
        if elem.role in heading_roles:
            return True
        if elem.formatting.bold and len(elem.content.split()) <= 10:
            return True
        return False
