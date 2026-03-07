"""
FormatForge AI — StyleSpec Schema
Defines the formatting rules for a specific journal style.
LLM interprets guidelines → StyleSpec JSON | We also hardcode APA 7 as ground truth.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# ── Page layout ───────────────────────────────────────────────

class PageLayout(BaseModel):
    margin_top_inches: float = 1.0
    margin_bottom_inches: float = 1.0
    margin_left_inches: float = 1.0
    margin_right_inches: float = 1.0
    page_width_inches: float = 8.5
    page_height_inches: float = 11.0
    orientation: str = "portrait"  # "portrait" | "landscape"
    columns: int = 1  # 1 or 2
    column_spacing_inches: float = 0.25


# ── Typography ────────────────────────────────────────────────

class DefaultTypography(BaseModel):
    font_name: str = "Times New Roman"
    font_size_pt: float = 12.0
    line_spacing: float = 2.0
    line_spacing_type: str = "double"  # "single" | "1.5" | "double" | "exact"
    paragraph_alignment: str = "left"  # "left" | "center" | "right" | "justify"
    first_line_indent_inches: float = 0.5
    space_after_paragraph_pt: float = 0.0
    space_before_paragraph_pt: float = 0.0


# ── Title page ────────────────────────────────────────────────

class TitleElementSpec(BaseModel):
    font_size_pt: float = 12.0
    bold: bool = False
    italic: bool = False
    alignment: str = "center"
    position: Optional[str] = None  # human-readable position hint


class TitlePageSpec(BaseModel):
    required: bool = True
    title: TitleElementSpec = Field(
        default_factory=lambda: TitleElementSpec(bold=True)
    )
    author_name: TitleElementSpec = Field(default_factory=TitleElementSpec)
    affiliation: TitleElementSpec = Field(default_factory=TitleElementSpec)
    course_info: Optional[TitleElementSpec] = Field(default_factory=TitleElementSpec)
    instructor: Optional[TitleElementSpec] = Field(default_factory=TitleElementSpec)
    date: Optional[TitleElementSpec] = Field(default_factory=TitleElementSpec)


# ── Abstract ──────────────────────────────────────────────────

class AbstractSpec(BaseModel):
    label: str = "Abstract"
    label_bold: bool = True
    label_alignment: str = "center"
    paragraph_indent: bool = False
    max_words: int = 250
    keywords_label: str = "Keywords:"
    keywords_italic: bool = True
    keywords_indent: bool = True


# ── Headings ──────────────────────────────────────────────────

class HeadingLevelSpec(BaseModel):
    alignment: str = "center"  # "center" | "left" | "indented"
    bold: bool = True
    italic: bool = False
    font_size_pt: float = 12.0
    case: str = "title_case"  # "title_case" | "sentence_case" | "upper"
    standalone_line: bool = True  # heading is on its own line
    ends_with_period: bool = False
    indent_inches: Optional[float] = None  # for indented headings (levels 4 & 5)
    description: str = ""


class HeadingsSpec(BaseModel):
    numbering_style: str = "none"  # "none" | "ieee" (Roman/alpha/arabic)
    level_1: HeadingLevelSpec = Field(
        default_factory=lambda: HeadingLevelSpec(
            alignment="center", bold=True, italic=False,
            description="Centered, Bold, Title Case",
        )
    )
    level_2: HeadingLevelSpec = Field(
        default_factory=lambda: HeadingLevelSpec(
            alignment="left", bold=True, italic=False,
            description="Flush Left, Bold, Title Case",
        )
    )
    level_3: HeadingLevelSpec = Field(
        default_factory=lambda: HeadingLevelSpec(
            alignment="left", bold=True, italic=True,
            description="Flush Left, Bold Italic, Title Case",
        )
    )
    level_4: HeadingLevelSpec = Field(
        default_factory=lambda: HeadingLevelSpec(
            alignment="indented", bold=True, italic=False,
            standalone_line=False, ends_with_period=True,
            indent_inches=0.5,
            description="Indented, Bold, Title Case, Period. Text on same line.",
        )
    )
    level_5: HeadingLevelSpec = Field(
        default_factory=lambda: HeadingLevelSpec(
            alignment="indented", bold=True, italic=True,
            standalone_line=False, ends_with_period=True,
            indent_inches=0.5,
            description="Indented, Bold Italic, Title Case, Period. Text on same line.",
        )
    )

    def get_level(self, level: int) -> HeadingLevelSpec:
        mapping = {
            1: self.level_1,
            2: self.level_2,
            3: self.level_3,
            4: self.level_4,
            5: self.level_5,
        }
        return mapping.get(level, self.level_1)


# ── Running head ──────────────────────────────────────────────

class RunningHeadSpec(BaseModel):
    enabled: bool = False  # False for student papers
    content: str = "SHORTENED TITLE"
    alignment: str = "left"
    page_number_alignment: str = "right"
    font_size_pt: float = 12.0
    all_caps: bool = True
    max_characters: int = 50


# ── References ────────────────────────────────────────────────

class ReferencesSpec(BaseModel):
    section_label: str = "References"
    label_bold: bool = True
    label_alignment: str = "center"
    entry_indent_type: str = "hanging"  # "hanging" | "none" | "first_line"
    hanging_indent_inches: float = 0.5
    order: str = "alphabetical_by_first_author"
    line_spacing: float = 2.0
    csl_style_name: str = "apa"  # citeproc-py style identifier


# ── Tables ────────────────────────────────────────────────────

class TablesSpec(BaseModel):
    number_label: str = "Table"
    number_bold: bool = True
    number_italic: bool = False
    title_italic: bool = True
    title_below_number: bool = True
    note_prefix: str = "Note."
    note_italic_prefix: bool = True
    horizontal_lines_only: bool = True


# ── Figures ───────────────────────────────────────────────────

class FiguresSpec(BaseModel):
    number_label: str = "Figure"
    number_bold: bool = True
    number_italic: bool = True
    title_italic: bool = True
    title_below_number: bool = True
    note_prefix: str = "Note."
    note_italic_prefix: bool = True


# ── In-text citations ────────────────────────────────────────

class InTextCitationSpec(BaseModel):
    style: str = "author-date"  # "author-date" | "numeric" | "note"
    parenthetical_format: str = "(Author, Year)"
    narrative_format: str = "Author (Year)"
    et_al_threshold: int = 3
    ampersand_in_parenthetical: bool = True
    and_in_narrative: bool = True


# ── StyleSpec — Top-level ────────────────────────────────────

class StyleSpec(BaseModel):
    """
    StyleSpec — Complete formatting specification for a journal style.
    This is what the Rule Interpreter agent produces.
    """
    style_name: str = "APA 7th Edition"
    style_id: str = "apa7"
    csl_style: str = "apa"

    page_layout: PageLayout = Field(default_factory=PageLayout)
    default_typography: DefaultTypography = Field(default_factory=DefaultTypography)
    title_page: TitlePageSpec = Field(default_factory=TitlePageSpec)
    abstract: AbstractSpec = Field(default_factory=AbstractSpec)
    headings: HeadingsSpec = Field(default_factory=HeadingsSpec)
    running_head: RunningHeadSpec = Field(default_factory=RunningHeadSpec)
    references: ReferencesSpec = Field(default_factory=ReferencesSpec)
    tables: TablesSpec = Field(default_factory=TablesSpec)
    figures: FiguresSpec = Field(default_factory=FiguresSpec)
    in_text_citations: InTextCitationSpec = Field(default_factory=InTextCitationSpec)
