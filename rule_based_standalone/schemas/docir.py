"""
FormatForge AI — DocIR (Document Internal Representation) Schema
Every document gets converted to this universal format first.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Element types ──────────────────────────────────────────────

class ElementType(str, Enum):
    PARAGRAPH = "paragraph"
    TABLE = "table"
    IMAGE = "image"
    PAGE_BREAK = "page_break"
    SECTION_BREAK = "section_break"


class ElementRole(str, Enum):
    TITLE = "title"
    AUTHOR_INFO = "author_info"
    ABSTRACT_LABEL = "abstract_label"
    ABSTRACT_BODY = "abstract_body"
    KEYWORDS = "keywords"
    HEADING_1 = "heading_1"
    HEADING_2 = "heading_2"
    HEADING_3 = "heading_3"
    HEADING_4 = "heading_4"
    HEADING_5 = "heading_5"
    BODY = "body"
    BLOCK_QUOTE = "block_quote"
    REFERENCE_LABEL = "reference_label"
    REFERENCE_ENTRY = "reference_entry"
    TABLE_CAPTION = "table_caption"
    FIGURE_CAPTION = "figure_caption"
    TABLE = "table"
    FIGURE = "figure"
    APPENDIX = "appendix"
    UNKNOWN = "unknown"


# ── Run-level formatting ──────────────────────────────────────

class RunFormatting(BaseModel):
    """Formatting for a single run (contiguous text with same formatting)."""
    text: str = ""
    bold: Optional[bool] = None
    italic: Optional[bool] = None
    underline: Optional[bool] = None
    strike: Optional[bool] = None
    font_name: Optional[str] = None
    font_size_pt: Optional[float] = None
    color: Optional[str] = None  # hex color e.g. "FF0000"
    superscript: Optional[bool] = None
    subscript: Optional[bool] = None


# ── Paragraph-level formatting ────────────────────────────────

class ParagraphFormatting(BaseModel):
    """Formatting properties of a paragraph."""
    font_name: Optional[str] = None
    font_size_pt: Optional[float] = None
    bold: Optional[bool] = None
    italic: Optional[bool] = None
    alignment: Optional[str] = None  # "left", "center", "right", "justify"
    line_spacing: Optional[float] = None  # 1.0, 1.5, 2.0
    line_spacing_rule: Optional[str] = None  # "single", "double", "multiple", "exactly", "at_least"
    space_before_pt: Optional[float] = None
    space_after_pt: Optional[float] = None
    first_line_indent_inches: Optional[float] = None
    left_indent_inches: Optional[float] = None
    right_indent_inches: Optional[float] = None
    keep_together: Optional[bool] = None
    keep_with_next: Optional[bool] = None
    widow_control: Optional[bool] = None


# ── Citation ──────────────────────────────────────────────────

class CitationType(str, Enum):
    PARENTHETICAL = "parenthetical"
    NARRATIVE = "narrative"


class InTextCitation(BaseModel):
    """A single in-text citation found in a paragraph."""
    text: str  # Full matched text e.g. "(Smith, 2023)"
    citation_type: CitationType = CitationType.PARENTHETICAL
    authors: list[str] = Field(default_factory=list)  # ["Smith", "Jones"]
    year: Optional[str] = None
    page: Optional[str] = None
    position_start: Optional[int] = None
    position_end: Optional[int] = None


# ── Parsed reference ─────────────────────────────────────────

class AuthorName(BaseModel):
    family: str
    given: Optional[str] = None


class ParsedReference(BaseModel):
    """Structured data parsed from a raw reference string."""
    authors: list[AuthorName] = Field(default_factory=list)
    year: Optional[str] = None
    title: Optional[str] = None
    container_title: Optional[str] = None  # Journal / book title
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    publisher: Optional[str] = None
    edition: Optional[str] = None
    ref_type: Optional[str] = "article-journal"  # CSL type
    original_number: Optional[int] = None  # For numbered references (PNAS/Vancouver)
    formatted_apa: Optional[str] = None  # citeproc-py formatted string

    def to_csl_json(self, csl_id: Optional[str] = None) -> dict:
        """Convert to CSL-JSON dict for citeproc-py."""
        item: dict = {"type": self.ref_type or "article-journal"}
        if csl_id:
            item["id"] = csl_id
        else:
            # Generate an id from first author + year
            first_family = self.authors[0].family if self.authors else "unknown"
            item["id"] = f"{first_family.lower()}-{self.year or '0000'}"

        if self.authors:
            item["author"] = [
                {"family": a.family, "given": a.given or ""}
                for a in self.authors
            ]

        if self.year:
            item["issued"] = {"date-parts": [[int(self.year)]]}
        if self.title:
            item["title"] = self.title
        if self.container_title:
            item["container-title"] = self.container_title
        if self.volume:
            item["volume"] = self.volume
        if self.issue:
            item["issue"] = self.issue
        if self.pages:
            item["page"] = self.pages
        if self.doi:
            item["DOI"] = self.doi
        if self.url:
            item["URL"] = self.url
        if self.publisher:
            item["publisher"] = self.publisher
        if self.edition:
            item["edition"] = self.edition

        return item


# ── Table data ────────────────────────────────────────────────

class TableCell(BaseModel):
    text: str = ""
    row: int = 0
    col: int = 0
    bold: Optional[bool] = None


class TableData(BaseModel):
    rows: list[list[TableCell]] = Field(default_factory=list)
    num_rows: int = 0
    num_cols: int = 0


# ── Document element ─────────────────────────────────────────

class DocElement(BaseModel):
    """A single element in the document (paragraph, table, image, etc.)."""
    id: str = ""
    type: ElementType = ElementType.PARAGRAPH
    role: ElementRole = ElementRole.UNKNOWN
    content: str = ""
    original_style_name: Optional[str] = None
    formatting: ParagraphFormatting = Field(default_factory=ParagraphFormatting)
    runs: list[RunFormatting] = Field(default_factory=list)

    # Citation-specific
    citations_found: list[InTextCitation] = Field(default_factory=list)

    # Reference-specific
    parsed_reference: Optional[ParsedReference] = None

    # Table-specific
    table_data: Optional[TableData] = None
    table_number: Optional[int] = None

    # Figure-specific
    figure_number: Optional[int] = None

    # Caption (for tables / figures)
    caption: Optional[str] = None

    # Structure detection confidence
    role_confidence: float = 0.0  # 0.0 – 1.0


# ── Document metadata ────────────────────────────────────────

class DocMetadata(BaseModel):
    source_filename: str = ""
    source_format: str = "docx"  # "docx", "pdf", "txt"
    total_paragraphs: int = 0
    total_tables: int = 0
    total_figures: int = 0
    parsed_at: datetime = Field(default_factory=datetime.utcnow)


# ── DocIR — Top-level document representation ────────────────

class DocIR(BaseModel):
    """
    DocIR — Document Internal Representation.
    Universal structured representation of a manuscript.
    """
    metadata: DocMetadata = Field(default_factory=DocMetadata)
    elements: list[DocElement] = Field(default_factory=list)

    # ── Helper methods ──

    def get_elements_by_role(self, role: ElementRole) -> list[DocElement]:
        return [e for e in self.elements if e.role == role]

    def get_title(self) -> Optional[DocElement]:
        titles = self.get_elements_by_role(ElementRole.TITLE)
        return titles[0] if titles else None

    def get_abstract(self) -> Optional[DocElement]:
        bodies = self.get_elements_by_role(ElementRole.ABSTRACT_BODY)
        return bodies[0] if bodies else None

    def get_headings(self) -> list[DocElement]:
        heading_roles = {
            ElementRole.HEADING_1,
            ElementRole.HEADING_2,
            ElementRole.HEADING_3,
            ElementRole.HEADING_4,
            ElementRole.HEADING_5,
        }
        return [e for e in self.elements if e.role in heading_roles]

    def get_reference_entries(self) -> list[DocElement]:
        return self.get_elements_by_role(ElementRole.REFERENCE_ENTRY)

    def get_body_paragraphs(self) -> list[DocElement]:
        return self.get_elements_by_role(ElementRole.BODY)

    def get_all_citations(self) -> list[InTextCitation]:
        citations: list[InTextCitation] = []
        for elem in self.elements:
            citations.extend(elem.citations_found)
        return citations
