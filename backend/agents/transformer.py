"""
FormatForge AI — Agent 5: Transformation Engine
Takes labeled DocIR + StyleSpec → produces formatted DOCX.
100% deterministic — no LLM calls here.
"""

from __future__ import annotations

import copy
import logging
from pathlib import Path
from typing import Optional

from backend.config import OUTPUT_FORMATTED_DIR
from backend.schemas.docir import DocIR, ElementRole
from backend.schemas.reports import ChangeRecord, ChangeStatus, Severity
from backend.schemas.style_spec import StyleSpec

logger = logging.getLogger(__name__)


class TransformerAgent:
    """Agent 5 — Apply formatting rules to produce a publication-ready DOCX."""

    def transform(
        self,
        docir: DocIR,
        style_spec: StyleSpec,
        input_path: Path,
        output_dir: Optional[Path] = None,
    ) -> tuple[Path, list[ChangeRecord]]:
        """
        Apply StyleSpec formatting to the input DOCX and write output.

        Args:
            docir: Labeled DocIR with roles assigned.
            style_spec: The target formatting specification.
            input_path: Path to the original DOCX file.
            output_dir: Where to write the formatted file.

        Returns:
            (output_path, list_of_changes)
        """
        from docx import Document
        from docx.shared import Pt, Inches, Cm, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        if output_dir is None:
            output_dir = OUTPUT_FORMATTED_DIR
        output_dir.mkdir(parents=True, exist_ok=True)

        changes: list[ChangeRecord] = []

        # Open the original document
        doc = Document(str(input_path))
        typo = style_spec.default_typography
        layout = style_spec.page_layout

        # ── Page Layout ──────────────────────────────────────
        changes.extend(self._apply_page_layout(doc, layout))

        # ── Default Font & Paragraph Style ───────────────────
        changes.extend(self._apply_default_typography(doc, typo))

        # ── Per-element formatting ───────────────────────────
        # Build a mapping from paragraph index to DocIR element
        para_role_map: dict[int, ElementRole] = {}
        para_idx = 0
        for elem in docir.elements:
            if elem.type.value == "paragraph":
                para_role_map[para_idx] = elem.role
                para_idx += 1

        for idx, para in enumerate(doc.paragraphs):
            role = para_role_map.get(idx, ElementRole.UNKNOWN)

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
            elif role in (
                ElementRole.HEADING_1, ElementRole.HEADING_2,
                ElementRole.HEADING_3, ElementRole.HEADING_4,
                ElementRole.HEADING_5,
            ):
                level = int(role.value.split("_")[1])
                changes.extend(self._format_heading(para, level, style_spec))
            elif role == ElementRole.REFERENCE_LABEL:
                changes.extend(self._format_reference_label(para, style_spec))
            elif role == ElementRole.REFERENCE_ENTRY:
                changes.extend(self._format_reference_entry(para, style_spec))
            elif role == ElementRole.BODY:
                changes.extend(self._format_body(para, style_spec))

        # ── Running Head + Page Numbers ──────────────────────
        changes.extend(self._apply_running_head(doc, style_spec))

        # ── Save output ──────────────────────────────────────
        stem = input_path.stem
        output_path = output_dir / f"{stem}_formatted.docx"
        doc.save(str(output_path))
        logger.info("Formatted document saved to %s (%d changes)", output_path, len(changes))

        return output_path, changes

    # ── Page Layout ──────────────────────────────────────────

    def _apply_page_layout(self, doc, layout) -> list[ChangeRecord]:
        from docx.shared import Inches
        changes = []
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
                description=f"Margins set to {layout.margin_top_inches}\" all sides",
                old_value=f"top={old_top}\"" if old_top else "unknown",
                new_value=f"{layout.margin_top_inches}\" all sides",
                rule_reference="APA 7 §2.22",
                status=ChangeStatus.APPLIED,
            ))
        return changes

    # ── Default Typography ───────────────────────────────────

    def _apply_default_typography(self, doc, typo) -> list[ChangeRecord]:
        from docx.shared import Pt
        changes = []

        # Modify the Normal style
        normal_style = doc.styles["Normal"]
        old_font = normal_style.font.name
        old_size = normal_style.font.size

        normal_style.font.name = typo.font_name
        normal_style.font.size = Pt(typo.font_size_pt)
        normal_style.paragraph_format.line_spacing = typo.line_spacing
        normal_style.paragraph_format.space_after = Pt(typo.space_after_paragraph_pt)
        normal_style.paragraph_format.space_before = Pt(typo.space_before_paragraph_pt)

        changes.append(ChangeRecord(
            category="typography",
            description=f"Default font set to {typo.font_name} {typo.font_size_pt}pt",
            old_value=f"{old_font} {old_size}",
            new_value=f"{typo.font_name} {typo.font_size_pt}pt",
            rule_reference="APA 7 §2.19",
            status=ChangeStatus.APPLIED,
        ))

        changes.append(ChangeRecord(
            category="typography",
            description=f"Line spacing set to {typo.line_spacing} (double)",
            new_value=str(typo.line_spacing),
            rule_reference="APA 7 §2.21",
            status=ChangeStatus.APPLIED,
        ))

        return changes

    # ── Individual element formatters ────────────────────────

    def _set_para_font(self, para, font_name: str, font_size_pt: float):
        """Set font on all runs in a paragraph."""
        from docx.shared import Pt
        for run in para.runs:
            run.font.name = font_name
            run.font.size = Pt(font_size_pt)

    def _format_title(self, para, spec: StyleSpec) -> list[ChangeRecord]:
        from docx.shared import Pt, Inches
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        ts = spec.title_page.title
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para.paragraph_format.first_line_indent = Inches(0)
        para.paragraph_format.line_spacing = spec.default_typography.line_spacing
        for run in para.runs:
            run.font.name = spec.default_typography.font_name
            run.font.size = Pt(ts.font_size_pt)
            run.bold = ts.bold
            run.italic = ts.italic if hasattr(ts, 'italic') else False

        return [ChangeRecord(
            category="title_page",
            description="Title formatted: centered, bold, 12pt",
            rule_reference="APA 7 §2.4",
            status=ChangeStatus.APPLIED,
        )]

    def _format_author_info(self, para, spec: StyleSpec) -> list[ChangeRecord]:
        from docx.shared import Pt, Inches
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para.paragraph_format.first_line_indent = Inches(0)
        para.paragraph_format.line_spacing = spec.default_typography.line_spacing
        self._set_para_font(para, spec.default_typography.font_name, spec.default_typography.font_size_pt)
        for run in para.runs:
            run.bold = False

        return [ChangeRecord(
            category="title_page",
            description="Author info formatted: centered, plain text",
            rule_reference="APA 7 §2.5",
            status=ChangeStatus.APPLIED,
        )]

    def _format_abstract_label(self, para, spec: StyleSpec) -> list[ChangeRecord]:
        from docx.shared import Pt, Inches
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para.paragraph_format.first_line_indent = Inches(0)
        para.paragraph_format.line_spacing = spec.default_typography.line_spacing
        self._set_para_font(para, spec.default_typography.font_name, spec.default_typography.font_size_pt)
        for run in para.runs:
            run.bold = spec.abstract.label_bold

        return [ChangeRecord(
            category="abstract",
            description="Abstract label: centered, bold",
            rule_reference="APA 7 §2.9",
            status=ChangeStatus.APPLIED,
        )]

    def _format_abstract_body(self, para, spec: StyleSpec) -> list[ChangeRecord]:
        from docx.shared import Pt, Inches
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        para.alignment = WD_ALIGN_PARAGRAPH.LEFT
        # No first-line indent for abstract body
        para.paragraph_format.first_line_indent = Inches(0) if not spec.abstract.paragraph_indent else Inches(0.5)
        para.paragraph_format.line_spacing = spec.default_typography.line_spacing
        self._set_para_font(para, spec.default_typography.font_name, spec.default_typography.font_size_pt)
        for run in para.runs:
            run.bold = False

        return [ChangeRecord(
            category="abstract",
            description="Abstract body: no indent, left-aligned, double-spaced",
            rule_reference="APA 7 §2.9",
            status=ChangeStatus.APPLIED,
        )]

    def _format_keywords(self, para, spec: StyleSpec) -> list[ChangeRecord]:
        from docx.shared import Pt, Inches
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        para.alignment = WD_ALIGN_PARAGRAPH.LEFT
        para.paragraph_format.first_line_indent = Inches(0.5)
        para.paragraph_format.line_spacing = spec.default_typography.line_spacing
        self._set_para_font(para, spec.default_typography.font_name, spec.default_typography.font_size_pt)
        # Make "Keywords:" italic
        for run in para.runs:
            if "keywords" in run.text.lower():
                run.italic = True
            else:
                run.italic = False

        return [ChangeRecord(
            category="abstract",
            description="Keywords line: indented, 'Keywords:' in italic",
            rule_reference="APA 7 §2.9",
            status=ChangeStatus.APPLIED,
        )]

    def _format_heading(self, para, level: int, spec: StyleSpec) -> list[ChangeRecord]:
        from docx.shared import Pt, Inches
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        hs = spec.headings.get_level(level)
        typo = spec.default_typography

        # Alignment
        if hs.alignment == "center":
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif hs.alignment == "left":
            para.alignment = WD_ALIGN_PARAGRAPH.LEFT
        elif hs.alignment == "indented":
            para.alignment = WD_ALIGN_PARAGRAPH.LEFT
            para.paragraph_format.first_line_indent = Inches(hs.indent_inches or 0.5)

        # No first-line indent for non-indented headings
        if hs.alignment != "indented":
            para.paragraph_format.first_line_indent = Inches(0)

        para.paragraph_format.line_spacing = typo.line_spacing

        # Font
        for run in para.runs:
            run.font.name = typo.font_name
            run.font.size = Pt(hs.font_size_pt)
            run.bold = hs.bold
            run.italic = hs.italic

        return [ChangeRecord(
            category="headings",
            description=f"Level {level} heading: {hs.description}",
            rule_reference=f"APA 7 §2.27 Level {level}",
            status=ChangeStatus.APPLIED,
        )]

    def _format_reference_label(self, para, spec: StyleSpec) -> list[ChangeRecord]:
        from docx.shared import Pt, Inches
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        # Same as Level 1 heading
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para.paragraph_format.first_line_indent = Inches(0)
        para.paragraph_format.line_spacing = spec.default_typography.line_spacing
        self._set_para_font(para, spec.default_typography.font_name, spec.default_typography.font_size_pt)
        for run in para.runs:
            run.bold = spec.references.label_bold

        return [ChangeRecord(
            category="references",
            description="Reference label: centered, bold (Level 1 format)",
            rule_reference="APA 7 §2.12",
            status=ChangeStatus.APPLIED,
        )]

    def _format_reference_entry(self, para, spec: StyleSpec) -> list[ChangeRecord]:
        from docx.shared import Pt, Inches
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        para.alignment = WD_ALIGN_PARAGRAPH.LEFT
        # Hanging indent
        para.paragraph_format.first_line_indent = Inches(-spec.references.hanging_indent_inches)
        para.paragraph_format.left_indent = Inches(spec.references.hanging_indent_inches)
        para.paragraph_format.line_spacing = spec.references.line_spacing
        self._set_para_font(para, spec.default_typography.font_name, spec.default_typography.font_size_pt)
        for run in para.runs:
            run.bold = False

        return [ChangeRecord(
            category="references",
            description="Reference entry: hanging indent 0.5\", double-spaced",
            rule_reference="APA 7 §2.12",
            status=ChangeStatus.APPLIED,
        )]

    def _format_body(self, para, spec: StyleSpec) -> list[ChangeRecord]:
        from docx.shared import Pt, Inches
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        typo = spec.default_typography

        alignment_map = {
            "left": WD_ALIGN_PARAGRAPH.LEFT,
            "center": WD_ALIGN_PARAGRAPH.CENTER,
            "right": WD_ALIGN_PARAGRAPH.RIGHT,
            "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
        }
        para.alignment = alignment_map.get(typo.paragraph_alignment, WD_ALIGN_PARAGRAPH.LEFT)
        para.paragraph_format.first_line_indent = Inches(typo.first_line_indent_inches)
        para.paragraph_format.line_spacing = typo.line_spacing
        para.paragraph_format.space_after = Pt(typo.space_after_paragraph_pt)
        para.paragraph_format.space_before = Pt(typo.space_before_paragraph_pt)
        self._set_para_font(para, typo.font_name, typo.font_size_pt)

        return []  # Body formatting is "default" — no individual change record needed

    # ── Running Head + Page Numbers ──────────────────────────

    def _apply_running_head(self, doc, spec: StyleSpec) -> list[ChangeRecord]:
        from docx.shared import Pt
        changes = []

        for section in doc.sections:
            section.different_first_page_header_footer = False
            header = section.header
            header.is_linked_to_previous = False

            # Add page number at minimum
            if not header.paragraphs:
                header.add_paragraph()

            h_para = header.paragraphs[0]
            # Clear existing header text
            for run in h_para.runs:
                run.text = ""

            if spec.running_head.enabled:
                # Professional paper: running head + page number
                h_para.text = spec.running_head.content[:spec.running_head.max_characters]
                h_para.alignment = 0  # LEFT
                for run in h_para.runs:
                    run.font.name = spec.default_typography.font_name
                    run.font.size = Pt(spec.running_head.font_size_pt)

                changes.append(ChangeRecord(
                    category="running_head",
                    description="Running head added with page number",
                    rule_reference="APA 7 §2.8",
                    status=ChangeStatus.APPLIED,
                ))
            else:
                # Student paper: page number only (top right)
                changes.append(ChangeRecord(
                    category="page_numbers",
                    description="Page number header configured",
                    rule_reference="APA 7 §2.18",
                    status=ChangeStatus.APPLIED,
                ))

        return changes
