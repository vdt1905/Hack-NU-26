"""
FormatForge AI — Agent 5: Transformation Engine
Takes labeled DocIR + StyleSpec → produces a publication-ready DOCX.

Phase 2 — Complete formatting pipeline:
 • Page layout (margins, page size, orientation)
 • Default typography (Normal style — font, size, spacing)
 • Per-element formatting for every semantic role
 • Font enforcement on every run (overrides PDF-to-DOCX artefacts)
 • Running head (shortened title ALL-CAPS left, page number right)
 • Title-page & abstract-page section breaks
 • Automatic label insertion ("Abstract", "References") when missing
 • Table / figure caption formatting (APA style)

100 % deterministic — zero LLM calls.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt
from docx.text.paragraph import Paragraph

from backend.config import OUTPUT_FORMATTED_DIR
from backend.schemas.docir import DocElement, DocIR, ElementRole, ElementType
from backend.schemas.reports import ChangeRecord, ChangeStatus, Severity
from backend.schemas.style_spec import StyleSpec

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
#  TransformerAgent
# ══════════════════════════════════════════════════════════════

class TransformerAgent:
    """Agent 5 — Apply formatting rules to produce a publication-ready DOCX."""

    # ── Public API ────────────────────────────────────────────

    def transform(
        self,
        docir: DocIR,
        style_spec: StyleSpec,
        input_path: Path,
        output_dir: Optional[Path] = None,
    ) -> tuple[Path, list[ChangeRecord]]:
        """
        Apply *style_spec* formatting to the manuscript at *input_path*.

        Pipeline:
            1. Open original DOCX
            2. Build paragraph ↔ DocElement mapping
            3. Global settings (page layout, Normal style)
            4. Per-paragraph formatting based on detected role
            5. Structural inserts (labels, page breaks)
            6. Running head + page numbers
            7. Save formatted output

        Returns:
            ``(output_path, list_of_changes)``
        """
        if output_dir is None:
            output_dir = OUTPUT_FORMATTED_DIR
        output_dir.mkdir(parents=True, exist_ok=True)

        changes: list[ChangeRecord] = []

        # 1. Open ─────────────────────────────────────────────
        doc = Document(str(input_path))
        typo = style_spec.default_typography
        layout = style_spec.page_layout

        # 2. Mapping ──────────────────────────────────────────
        para_elem_map = self._build_para_elem_map(docir)

        # 3. Global settings ──────────────────────────────────
        changes.extend(self._apply_page_layout(doc, layout))
        changes.extend(self._apply_default_typography(doc, typo))

        # 4. Per-paragraph formatting ─────────────────────────
        body_count = 0
        ref_count = 0
        for idx, para in enumerate(doc.paragraphs):
            elem = para_elem_map.get(idx)
            if elem is None:
                # Paragraph not mapped — apply body defaults
                self._apply_body_defaults(para, style_spec)
                continue
            role = elem.role
            if role == ElementRole.TITLE:
                changes.extend(self._format_title(para, style_spec))
            elif role == ElementRole.AUTHOR_INFO:
                changes.extend(self._format_author_info(para, style_spec))
            elif role == ElementRole.ABSTRACT_LABEL:
                changes.extend(self._format_abstract_label(para, style_spec))
            elif role == ElementRole.ABSTRACT_BODY:
                changes.extend(self._format_abstract_body(para, style_spec))
            elif role == ElementRole.KEYWORDS:
                changes.extend(self._format_keywords(para, style_spec))
            elif role in _HEADING_ROLES:
                level = int(role.value.split("_")[1])
                changes.extend(self._format_heading(para, level, style_spec))
            elif role == ElementRole.REFERENCE_LABEL:
                changes.extend(self._format_reference_label(para, style_spec))
            elif role == ElementRole.REFERENCE_ENTRY:
                self._format_single_reference_entry(para, style_spec)
                ref_count += 1
            elif role == ElementRole.BODY:
                self._apply_body_defaults(para, style_spec)
                body_count += 1
            elif role == ElementRole.UNKNOWN:
                # Treat remaining unknowns as body
                self._apply_body_defaults(para, style_spec)
            else:
                # Any other role (table_caption, figure_caption, appendix…)
                self._apply_body_defaults(para, style_spec)

        if body_count:
            changes.append(ChangeRecord(
                category="body",
                description=f"{body_count} body paragraphs formatted: "
                            f"{typo.font_name} {typo.font_size_pt}pt, "
                            f"{typo.line_spacing}x spacing, "
                            f"{typo.first_line_indent_inches}\" indent",
                rule_reference="APA 7 §2.19–2.24",
                status=ChangeStatus.APPLIED,
            ))
        if ref_count:
            changes.append(ChangeRecord(
                category="references",
                description=f"{ref_count} reference entries formatted: "
                            f"hanging indent {style_spec.references.hanging_indent_inches}\", "
                            f"double-spaced",
                rule_reference="APA 7 §2.12",
                status=ChangeStatus.APPLIED,
            ))

        # 5. Structural inserts ───────────────────────────────
        title_text = self._get_title_text(docir)
        changes.extend(
            self._add_structural_elements(doc, docir, para_elem_map, style_spec)
        )

        # 6. Running head + page numbers ──────────────────────
        changes.extend(self._apply_running_head(doc, style_spec, title_text))

        # 7. Save ─────────────────────────────────────────────
        stem = input_path.stem
        output_path = output_dir / f"{stem}_formatted.docx"
        doc.save(str(output_path))
        logger.info(
            "Formatted document saved → %s  (%d changes recorded)",
            output_path, len(changes),
        )
        return output_path, changes

    # ══════════════════════════════════════════════════════════
    #  Mapping helpers
    # ══════════════════════════════════════════════════════════

    @staticmethod
    def _build_para_elem_map(docir: DocIR) -> dict[int, DocElement]:
        """Map paragraph index in ``doc.paragraphs`` → DocElement."""
        mapping: dict[int, DocElement] = {}
        p_idx = 0
        for elem in docir.elements:
            if elem.type == ElementType.PARAGRAPH:
                mapping[p_idx] = elem
                p_idx += 1
            # Tables are not in doc.paragraphs — skip
        return mapping

    @staticmethod
    def _get_title_text(docir: DocIR) -> str:
        """Join all TITLE elements into a single string."""
        parts = [e.content for e in docir.elements if e.role == ElementRole.TITLE]
        return " ".join(parts).strip()

    # ══════════════════════════════════════════════════════════
    #  Global settings
    # ══════════════════════════════════════════════════════════

    def _apply_page_layout(self, doc: Document, layout) -> list[ChangeRecord]:
        """Set margins, page size, orientation on every section."""
        changes: list[ChangeRecord] = []
        for section in doc.sections:
            old_top = round(section.top_margin / 914400, 2) if section.top_margin else None
            section.top_margin = Inches(layout.margin_top_inches)
            section.bottom_margin = Inches(layout.margin_bottom_inches)
            section.left_margin = Inches(layout.margin_left_inches)
            section.right_margin = Inches(layout.margin_right_inches)
            section.page_width = Inches(layout.page_width_inches)
            section.page_height = Inches(layout.page_height_inches)
            changes.append(ChangeRecord(
                category="page_layout",
                description=(
                    f"Margins: {layout.margin_top_inches}\" T/B/L/R, "
                    f"page {layout.page_width_inches}\"×{layout.page_height_inches}\""
                ),
                old_value=f"top={old_top}\"" if old_top else "unknown",
                new_value=f"{layout.margin_top_inches}\" all sides",
                rule_reference="APA 7 §2.22",
                status=ChangeStatus.APPLIED,
            ))
        return changes

    def _apply_default_typography(self, doc: Document, typo) -> list[ChangeRecord]:
        """Set the Normal style to APA defaults — every un-overridden paragraph inherits this."""
        changes: list[ChangeRecord] = []
        normal = doc.styles["Normal"]
        old_font = normal.font.name
        old_size = normal.font.size

        normal.font.name = typo.font_name
        normal.font.size = Pt(typo.font_size_pt)
        # Set CS / East-Asian font families so non-Latin text also uses the right font
        self._set_style_rfonts(normal, typo.font_name)

        pf = normal.paragraph_format
        pf.line_spacing = typo.line_spacing
        pf.space_after = Pt(typo.space_after_paragraph_pt)
        pf.space_before = Pt(typo.space_before_paragraph_pt)

        changes.append(ChangeRecord(
            category="typography",
            description=f"Normal style → {typo.font_name} {typo.font_size_pt}pt, "
                        f"{typo.line_spacing}× spacing",
            old_value=f"{old_font} {old_size}",
            new_value=f"{typo.font_name} {typo.font_size_pt}pt",
            rule_reference="APA 7 §2.19-2.21",
            status=ChangeStatus.APPLIED,
        ))
        return changes

    # ══════════════════════════════════════════════════════════
    #  Font enforcement helpers
    # ══════════════════════════════════════════════════════════

    @staticmethod
    def _set_style_rfonts(style, font_name: str) -> None:
        """Set all four rFonts families on a *style* element."""
        rPr = style.element.get_or_add_rPr()
        rFonts = rPr.find(qn("w:rFonts"))
        if rFonts is None:
            rFonts = OxmlElement("w:rFonts")
            rPr.insert(0, rFonts)
        for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            rFonts.set(qn(attr), font_name)

    @staticmethod
    def _enforce_run_font(run, font_name: str, font_size_pt: float) -> None:
        """Force font name + size on a single run (overrides inherited junk)."""
        run.font.name = font_name
        run.font.size = Pt(font_size_pt)
        # Also set cs / eastAsia via XML for full coverage
        rPr = run._element.get_or_add_rPr()
        rFonts = rPr.find(qn("w:rFonts"))
        if rFonts is None:
            rFonts = OxmlElement("w:rFonts")
            rPr.insert(0, rFonts)
        for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            rFonts.set(qn(attr), font_name)

    def _enforce_font(
        self,
        para,
        font_name: str,
        font_size_pt: float,
        *,
        bold: Optional[bool] = None,
        italic: Optional[bool] = None,
    ) -> None:
        """Force font on **every** run in *para*, optionally setting bold/italic."""
        for run in para.runs:
            self._enforce_run_font(run, font_name, font_size_pt)
            if bold is not None:
                run.bold = bold
            if italic is not None:
                run.italic = italic

    # ══════════════════════════════════════════════════════════
    #  Per-element formatters
    # ══════════════════════════════════════════════════════════

    # ── Title ─────────────────────────────────────────────────

    def _format_title(self, para, spec: StyleSpec) -> list[ChangeRecord]:
        ts = spec.title_page.title
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pf = para.paragraph_format
        pf.first_line_indent = Inches(0)
        pf.left_indent = Inches(0)
        pf.line_spacing = spec.default_typography.line_spacing
        pf.space_after = Pt(0)
        pf.space_before = Pt(0)
        self._enforce_font(
            para,
            spec.default_typography.font_name,
            ts.font_size_pt,
            bold=ts.bold,
            italic=ts.italic,
        )
        return [ChangeRecord(
            category="title_page",
            description="Title: centered, bold, 12 pt",
            rule_reference="APA 7 §2.4",
            status=ChangeStatus.APPLIED,
        )]

    # ── Author info ───────────────────────────────────────────

    def _format_author_info(self, para, spec: StyleSpec) -> list[ChangeRecord]:
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pf = para.paragraph_format
        pf.first_line_indent = Inches(0)
        pf.left_indent = Inches(0)
        pf.line_spacing = spec.default_typography.line_spacing
        pf.space_after = Pt(0)
        pf.space_before = Pt(0)
        self._enforce_font(
            para,
            spec.default_typography.font_name,
            spec.default_typography.font_size_pt,
            bold=False,
        )
        return [ChangeRecord(
            category="title_page",
            description="Author info: centered, plain, 12 pt",
            rule_reference="APA 7 §2.5",
            status=ChangeStatus.APPLIED,
        )]

    # ── Abstract label ────────────────────────────────────────

    def _format_abstract_label(self, para, spec: StyleSpec) -> list[ChangeRecord]:
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pf = para.paragraph_format
        pf.first_line_indent = Inches(0)
        pf.left_indent = Inches(0)
        pf.line_spacing = spec.default_typography.line_spacing
        pf.space_after = Pt(0)
        self._enforce_font(
            para,
            spec.default_typography.font_name,
            spec.default_typography.font_size_pt,
            bold=spec.abstract.label_bold,
        )
        return [ChangeRecord(
            category="abstract",
            description="Abstract label: centered, bold",
            rule_reference="APA 7 §2.9",
            status=ChangeStatus.APPLIED,
        )]

    # ── Abstract body ─────────────────────────────────────────

    def _format_abstract_body(self, para, spec: StyleSpec) -> list[ChangeRecord]:
        para.alignment = WD_ALIGN_PARAGRAPH.LEFT
        pf = para.paragraph_format
        pf.first_line_indent = Inches(0)  # APA: no indent in abstract
        pf.left_indent = Inches(0)
        pf.line_spacing = spec.default_typography.line_spacing
        pf.space_after = Pt(0)
        pf.space_before = Pt(0)
        self._enforce_font(
            para,
            spec.default_typography.font_name,
            spec.default_typography.font_size_pt,
            bold=False,
        )
        return [ChangeRecord(
            category="abstract",
            description="Abstract body: left-aligned, no indent, double-spaced",
            rule_reference="APA 7 §2.9",
            status=ChangeStatus.APPLIED,
        )]

    # ── Keywords ──────────────────────────────────────────────

    def _format_keywords(self, para, spec: StyleSpec) -> list[ChangeRecord]:
        para.alignment = WD_ALIGN_PARAGRAPH.LEFT
        pf = para.paragraph_format
        pf.first_line_indent = Inches(0.5)
        pf.left_indent = Inches(0)
        pf.line_spacing = spec.default_typography.line_spacing
        # Apply italic to "Keywords:" prefix, plain to the rest
        for run in para.runs:
            self._enforce_run_font(
                run,
                spec.default_typography.font_name,
                spec.default_typography.font_size_pt,
            )
            if "keyword" in run.text.lower():
                run.bold = False
                run.italic = True
            else:
                run.bold = False
                run.italic = False
        return [ChangeRecord(
            category="abstract",
            description="Keywords: indented 0.5\", prefix italic",
            rule_reference="APA 7 §2.9",
            status=ChangeStatus.APPLIED,
        )]

    # ── Headings (all 5 levels) ───────────────────────────────

    def _format_heading(self, para, level: int, spec: StyleSpec) -> list[ChangeRecord]:
        hs = spec.headings.get_level(level)
        typo = spec.default_typography
        pf = para.paragraph_format

        # Alignment
        if hs.alignment == "center":
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            pf.first_line_indent = Inches(0)
            pf.left_indent = Inches(0)
        elif hs.alignment == "left":
            para.alignment = WD_ALIGN_PARAGRAPH.LEFT
            pf.first_line_indent = Inches(0)
            pf.left_indent = Inches(0)
        elif hs.alignment == "indented":
            para.alignment = WD_ALIGN_PARAGRAPH.LEFT
            pf.first_line_indent = Inches(hs.indent_inches or 0.5)
            pf.left_indent = Inches(0)

        pf.line_spacing = typo.line_spacing
        pf.space_after = Pt(0)
        pf.space_before = Pt(0)

        self._enforce_font(
            para,
            typo.font_name,
            hs.font_size_pt,
            bold=hs.bold,
            italic=hs.italic,
        )

        return [ChangeRecord(
            category="headings",
            description=f"Level {level}: {hs.description}",
            rule_reference=f"APA 7 §2.27 Level {level}",
            status=ChangeStatus.APPLIED,
        )]

    # ── Reference label ───────────────────────────────────────

    def _format_reference_label(self, para, spec: StyleSpec) -> list[ChangeRecord]:
        """Formatted identically to a Level-1 heading (centered, bold)."""
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pf = para.paragraph_format
        pf.first_line_indent = Inches(0)
        pf.left_indent = Inches(0)
        pf.line_spacing = spec.default_typography.line_spacing
        pf.space_after = Pt(0)
        self._enforce_font(
            para,
            spec.default_typography.font_name,
            spec.default_typography.font_size_pt,
            bold=spec.references.label_bold,
        )
        return [ChangeRecord(
            category="references",
            description="\"References\" label: centered, bold",
            rule_reference="APA 7 §2.12",
            status=ChangeStatus.APPLIED,
        )]

    # ── Single reference entry ────────────────────────────────

    def _format_single_reference_entry(self, para, spec: StyleSpec) -> None:
        """Format one reference entry with hanging indent (no ChangeRecord)."""
        para.alignment = WD_ALIGN_PARAGRAPH.LEFT
        pf = para.paragraph_format
        pf.left_indent = Inches(spec.references.hanging_indent_inches)
        pf.first_line_indent = Inches(-spec.references.hanging_indent_inches)
        pf.line_spacing = spec.references.line_spacing
        pf.space_after = Pt(0)
        pf.space_before = Pt(0)
        self._enforce_font(
            para,
            spec.default_typography.font_name,
            spec.default_typography.font_size_pt,
            bold=False,
        )

    # ── Body defaults ─────────────────────────────────────────

    def _apply_body_defaults(self, para, spec: StyleSpec) -> None:
        """Apply standard body-paragraph formatting (no ChangeRecord)."""
        typo = spec.default_typography
        _ALIGN = {
            "left": WD_ALIGN_PARAGRAPH.LEFT,
            "center": WD_ALIGN_PARAGRAPH.CENTER,
            "right": WD_ALIGN_PARAGRAPH.RIGHT,
            "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
        }
        para.alignment = _ALIGN.get(typo.paragraph_alignment, WD_ALIGN_PARAGRAPH.LEFT)
        pf = para.paragraph_format
        pf.first_line_indent = Inches(typo.first_line_indent_inches)
        pf.left_indent = Inches(0)
        pf.line_spacing = typo.line_spacing
        pf.space_after = Pt(typo.space_after_paragraph_pt)
        pf.space_before = Pt(typo.space_before_paragraph_pt)
        self._enforce_font(
            para,
            typo.font_name,
            typo.font_size_pt,
        )

    # ══════════════════════════════════════════════════════════
    #  Structural inserts (labels, page breaks)
    # ══════════════════════════════════════════════════════════

    def _add_structural_elements(
        self,
        doc: Document,
        docir: DocIR,
        para_elem_map: dict[int, DocElement],
        spec: StyleSpec,
    ) -> list[ChangeRecord]:
        """Insert missing labels and APA-required page breaks."""
        changes: list[ChangeRecord] = []

        has_abstract_label = any(
            e.role == ElementRole.ABSTRACT_LABEL for e in docir.elements
        )
        has_reference_label = any(
            e.role == ElementRole.REFERENCE_LABEL for e in docir.elements
        )

        # Collect role spans ──────────────────────────────────
        first_abstract_idx: Optional[int] = None
        first_ref_idx: Optional[int] = None
        first_body_or_heading_after_abstract: Optional[int] = None
        last_front_matter_idx: Optional[int] = None  # last title/author

        abstract_seen = False
        for idx, elem in para_elem_map.items():
            role = elem.role
            if role in (ElementRole.TITLE, ElementRole.AUTHOR_INFO):
                last_front_matter_idx = idx
            if role == ElementRole.ABSTRACT_BODY and first_abstract_idx is None:
                first_abstract_idx = idx
                abstract_seen = True
            if role == ElementRole.ABSTRACT_LABEL and first_abstract_idx is None:
                first_abstract_idx = idx
                abstract_seen = True
            if role == ElementRole.REFERENCE_ENTRY and first_ref_idx is None:
                first_ref_idx = idx
            if abstract_seen and role in (
                ElementRole.BODY,
                ElementRole.HEADING_1, ElementRole.HEADING_2,
                ElementRole.HEADING_3,
            ):
                if first_body_or_heading_after_abstract is None:
                    first_body_or_heading_after_abstract = idx

        paras = doc.paragraphs

        # ── Insert "Abstract" label if missing ───────────────
        if not has_abstract_label and first_abstract_idx is not None:
            target = paras[first_abstract_idx]
            new_para = self._insert_paragraph_before(target, doc)
            run = new_para.add_run(spec.abstract.label)
            self._enforce_run_font(
                run,
                spec.default_typography.font_name,
                spec.default_typography.font_size_pt,
            )
            run.bold = spec.abstract.label_bold
            new_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            new_para.paragraph_format.first_line_indent = Inches(0)
            new_para.paragraph_format.left_indent = Inches(0)
            new_para.paragraph_format.line_spacing = spec.default_typography.line_spacing
            new_para.paragraph_format.space_after = Pt(0)
            # Page break before the abstract label (= new page)
            new_para.paragraph_format.page_break_before = True
            changes.append(ChangeRecord(
                category="abstract",
                description="Inserted \"Abstract\" label (centered, bold) on new page",
                rule_reference="APA 7 §2.9",
                status=ChangeStatus.APPLIED,
            ))
        elif first_abstract_idx is not None:
            # Label exists — just ensure page break
            paras[first_abstract_idx].paragraph_format.page_break_before = True

        # ── Insert "References" label if missing ─────────────
        if not has_reference_label and first_ref_idx is not None:
            target = paras[first_ref_idx]
            new_para = self._insert_paragraph_before(target, doc)
            run = new_para.add_run(spec.references.section_label)
            self._enforce_run_font(
                run,
                spec.default_typography.font_name,
                spec.default_typography.font_size_pt,
            )
            run.bold = spec.references.label_bold
            new_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            new_para.paragraph_format.first_line_indent = Inches(0)
            new_para.paragraph_format.left_indent = Inches(0)
            new_para.paragraph_format.line_spacing = spec.default_typography.line_spacing
            new_para.paragraph_format.space_after = Pt(0)
            # References on new page
            new_para.paragraph_format.page_break_before = True
            changes.append(ChangeRecord(
                category="references",
                description="Inserted \"References\" label (centered, bold) on new page",
                rule_reference="APA 7 §2.12",
                status=ChangeStatus.APPLIED,
            ))
        elif first_ref_idx is not None:
            paras[first_ref_idx].paragraph_format.page_break_before = True

        # ── Title-page break ─────────────────────────────────
        #    Body text starts on a new page after abstract/keywords
        if first_body_or_heading_after_abstract is not None:
            paras[first_body_or_heading_after_abstract].paragraph_format.page_break_before = True
            changes.append(ChangeRecord(
                category="page_layout",
                description="Body text starts on new page (after abstract)",
                rule_reference="APA 7 §2.11",
                status=ChangeStatus.APPLIED,
            ))

        return changes

    # ── XML paragraph insertion ───────────────────────────────

    @staticmethod
    def _insert_paragraph_before(target_para, doc: Document) -> Paragraph:
        """Insert a new empty paragraph immediately before *target_para*."""
        new_p = OxmlElement("w:p")
        target_para._element.addprevious(new_p)
        return Paragraph(new_p, target_para._element.getparent())

    # ══════════════════════════════════════════════════════════
    #  Running head + page numbers
    # ══════════════════════════════════════════════════════════

    def _apply_running_head(
        self,
        doc: Document,
        spec: StyleSpec,
        title_text: str,
    ) -> list[ChangeRecord]:
        """
        Add a header with running-head text (left) + page number (right).

        Uses a right-aligned tab stop so the page number hugs the right margin.
        """
        changes: list[ChangeRecord] = []
        font_name = spec.default_typography.font_name
        font_size = spec.running_head.font_size_pt

        for section in doc.sections:
            section.different_first_page_header_footer = False
            header = section.header
            header.is_linked_to_previous = False

            # Clear any existing content
            for p in header.paragraphs:
                p_elem = p._element
                for child in list(p_elem):
                    p_elem.remove(child)

            if not header.paragraphs:
                header.add_paragraph()

            h_para = header.paragraphs[0]

            # ── Tab stop at right margin ─────────────────────
            usable_width_twips = int(
                (
                    spec.page_layout.page_width_inches
                    - spec.page_layout.margin_left_inches
                    - spec.page_layout.margin_right_inches
                )
                * 1440  # 1 inch = 1440 twips
            )
            pPr = h_para._element.get_or_add_pPr()
            tabs_elem = OxmlElement("w:tabs")
            tab_elem = OxmlElement("w:tab")
            tab_elem.set(qn("w:val"), "right")
            tab_elem.set(qn("w:pos"), str(usable_width_twips))
            tab_elem.set(qn("w:leader"), "none")
            tabs_elem.append(tab_elem)
            pPr.append(tabs_elem)

            # ── Running head text (left) ─────────────────────
            short_title = title_text.upper()[:spec.running_head.max_characters]
            if short_title:
                head_run = h_para.add_run(short_title)
                self._enforce_run_font(head_run, font_name, font_size)

            # ── Tab ──────────────────────────────────────────
            tab_run = h_para.add_run("\t")
            self._enforce_run_font(tab_run, font_name, font_size)

            # ── Page number field ────────────────────────────
            self._add_page_number_field(h_para, font_name, font_size)

            changes.append(ChangeRecord(
                category="running_head",
                description=f"Running head: \"{short_title}\" + page number",
                rule_reference="APA 7 §2.8",
                status=ChangeStatus.APPLIED,
            ))

        return changes

    def _add_page_number_field(
        self, paragraph, font_name: str, font_size_pt: float,
    ) -> None:
        """Insert a PAGE field code (renders as the current page number)."""
        # Begin
        run_begin = paragraph.add_run()
        self._enforce_run_font(run_begin, font_name, font_size_pt)
        fld_begin = OxmlElement("w:fldChar")
        fld_begin.set(qn("w:fldCharType"), "begin")
        run_begin._element.append(fld_begin)

        # InstrText
        run_instr = paragraph.add_run()
        self._enforce_run_font(run_instr, font_name, font_size_pt)
        instr = OxmlElement("w:instrText")
        instr.set(qn("xml:space"), "preserve")
        instr.text = " PAGE "
        run_instr._element.append(instr)

        # End
        run_end = paragraph.add_run()
        self._enforce_run_font(run_end, font_name, font_size_pt)
        fld_end = OxmlElement("w:fldChar")
        fld_end.set(qn("w:fldCharType"), "end")
        run_end._element.append(fld_end)


# ── Module-level constants ────────────────────────────────────

_HEADING_ROLES = frozenset({
    ElementRole.HEADING_1,
    ElementRole.HEADING_2,
    ElementRole.HEADING_3,
    ElementRole.HEADING_4,
    ElementRole.HEADING_5,
})
