"""
FormatForge AI — MLA & Chicago Style Test Suite
Tests that MLA 9th Edition and Chicago 17th Edition specs load correctly
and that the transformation engine applies their unique rules.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

from backend.schemas.docir import (
    DocElement,
    DocIR,
    DocMetadata,
    ElementRole,
    ElementType,
    ParagraphFormatting,
    RunFormatting,
)
from backend.schemas.reports import ChangeRecord
from backend.schemas.style_spec import StyleSpec
from backend.agents.transformer import TransformerAgent
from backend.agents.rule_interpreter import RuleInterpreterAgent


# ══════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════

def _make_elem(
    idx: int,
    role: ElementRole,
    content: str = "",
    bold: bool = False,
    italic: bool = False,
) -> DocElement:
    return DocElement(
        id=f"elem_{idx:04d}",
        type=ElementType.PARAGRAPH,
        content=content,
        role=role,
        role_confidence=0.99,
        formatting=ParagraphFormatting(
            bold=bold,
            italic=italic,
            font_name="Calibri",
            font_size_pt=11.0,
            runs=[RunFormatting(text=content, bold=bold, italic=italic)],
        ),
    )


def _build_simple_docir() -> DocIR:
    elems = [
        _make_elem(0, ElementRole.TITLE, "Test Paper Title"),
        _make_elem(1, ElementRole.AUTHOR_INFO, "Jane Doe"),
        _make_elem(2, ElementRole.ABSTRACT_LABEL, "Abstract"),
        _make_elem(3, ElementRole.ABSTRACT_BODY,
                   "This is a test abstract for style validation."),
        _make_elem(4, ElementRole.KEYWORDS,
                   "Keywords: test, formatting, style"),
        _make_elem(5, ElementRole.HEADING_1, "Introduction"),
        _make_elem(6, ElementRole.BODY, "Body paragraph one with content."),
        _make_elem(7, ElementRole.BODY, "Body paragraph two with content."),
        _make_elem(8, ElementRole.HEADING_1, "Conclusion"),
        _make_elem(9, ElementRole.BODY, "Conclusion paragraph."),
        _make_elem(10, ElementRole.REFERENCE_LABEL, "References"),
        _make_elem(11, ElementRole.REFERENCE_ENTRY,
                   "Smith, J. (2024). Test paper. Journal of Testing, 1(1), 1-10."),
    ]
    return DocIR(
        metadata=DocMetadata(filename="test_mla_chicago.docx"),
        elements=elems,
    )


def _create_docx(docir: DocIR, path: Path) -> Path:
    doc = Document()
    for elem in docir.elements:
        if elem.type == ElementType.PARAGRAPH:
            para = doc.add_paragraph(elem.content)
            for run in para.runs:
                if elem.formatting.bold:
                    run.bold = True
                if elem.formatting.italic:
                    run.italic = True
    doc.save(str(path))
    return path


def _run_transform(docir: DocIR, spec: StyleSpec) -> tuple[Path, list[ChangeRecord], Document]:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        input_path = tmpdir / "input.docx"
        _create_docx(docir, input_path)
        agent = TransformerAgent()
        out_path, changes = agent.transform(docir, spec, input_path, output_dir=tmpdir)
        out_doc = Document(str(out_path))
        return out_path, changes, out_doc


# ══════════════════════════════════════════════════════════════
#  MLA SPEC LOADING TESTS
# ══════════════════════════════════════════════════════════════

class TestMLASpecLoading(unittest.TestCase):
    """Verify MLA 9th Edition spec loads and has correct values."""

    @classmethod
    def setUpClass(cls):
        ri = RuleInterpreterAgent()
        cls.spec = ri.get_style_spec("mla")

    def test_style_name(self):
        self.assertEqual(self.spec.style_name, "MLA 9th Edition")

    def test_style_id(self):
        self.assertEqual(self.spec.style_id, "mla")

    def test_margins_one_inch(self):
        pl = self.spec.page_layout
        self.assertEqual(pl.margin_top_inches, 1.0)
        self.assertEqual(pl.margin_bottom_inches, 1.0)
        self.assertEqual(pl.margin_left_inches, 1.0)
        self.assertEqual(pl.margin_right_inches, 1.0)

    def test_font_times_new_roman_12pt(self):
        dt = self.spec.default_typography
        self.assertEqual(dt.font_name, "Times New Roman")
        self.assertEqual(dt.font_size_pt, 12.0)

    def test_double_spacing(self):
        self.assertEqual(self.spec.default_typography.line_spacing, 2.0)

    def test_left_aligned(self):
        self.assertEqual(self.spec.default_typography.paragraph_alignment, "left")

    def test_half_inch_indent(self):
        self.assertEqual(self.spec.default_typography.first_line_indent_inches, 0.5)

    def test_no_title_page(self):
        self.assertFalse(self.spec.title_page.required)

    def test_title_not_bold(self):
        self.assertFalse(self.spec.title_page.title.bold)

    def test_title_centered(self):
        self.assertEqual(self.spec.title_page.title.alignment, "center")

    def test_no_abstract(self):
        self.assertEqual(self.spec.abstract.label, "")

    def test_works_cited_label(self):
        self.assertEqual(self.spec.references.section_label, "Works Cited")

    def test_references_hanging_indent(self):
        self.assertEqual(self.spec.references.entry_indent_type, "hanging")
        self.assertEqual(self.spec.references.hanging_indent_inches, 0.5)

    def test_running_head_enabled(self):
        self.assertTrue(self.spec.running_head.enabled)

    def test_running_head_right_aligned(self):
        self.assertEqual(self.spec.running_head.alignment, "right")

    def test_author_date_citations(self):
        self.assertEqual(self.spec.in_text_citations.style, "author-date")

    def test_heading_level1_centered_bold(self):
        h1 = self.spec.headings.level_1
        self.assertEqual(h1.alignment, "center")
        self.assertTrue(h1.bold)

    def test_heading_level2_left_bold(self):
        h2 = self.spec.headings.level_2
        self.assertEqual(h2.alignment, "left")
        self.assertTrue(h2.bold)

    def test_heading_level4_italic_not_bold(self):
        h4 = self.spec.headings.level_4
        self.assertTrue(h4.italic)
        self.assertFalse(h4.bold)


# ══════════════════════════════════════════════════════════════
#  CHICAGO SPEC LOADING TESTS
# ══════════════════════════════════════════════════════════════

class TestChicagoSpecLoading(unittest.TestCase):
    """Verify Chicago 17th Edition spec loads and has correct values."""

    @classmethod
    def setUpClass(cls):
        ri = RuleInterpreterAgent()
        cls.spec = ri.get_style_spec("chicago")

    def test_style_name(self):
        self.assertIn("Chicago", self.spec.style_name)

    def test_style_id(self):
        self.assertEqual(self.spec.style_id, "chicago")

    def test_margins_one_inch(self):
        pl = self.spec.page_layout
        self.assertEqual(pl.margin_top_inches, 1.0)
        self.assertEqual(pl.margin_bottom_inches, 1.0)

    def test_font_times_new_roman_12pt(self):
        dt = self.spec.default_typography
        self.assertEqual(dt.font_name, "Times New Roman")
        self.assertEqual(dt.font_size_pt, 12.0)

    def test_double_spacing(self):
        self.assertEqual(self.spec.default_typography.line_spacing, 2.0)

    def test_left_aligned(self):
        self.assertEqual(self.spec.default_typography.paragraph_alignment, "left")

    def test_half_inch_indent(self):
        self.assertEqual(self.spec.default_typography.first_line_indent_inches, 0.5)

    def test_title_page_required(self):
        self.assertTrue(self.spec.title_page.required)

    def test_title_bold_centered(self):
        tp = self.spec.title_page.title
        self.assertTrue(tp.bold)
        self.assertEqual(tp.alignment, "center")

    def test_abstract_label(self):
        self.assertEqual(self.spec.abstract.label, "Abstract")

    def test_bibliography_label(self):
        self.assertEqual(self.spec.references.section_label, "Bibliography")

    def test_references_hanging_indent(self):
        self.assertEqual(self.spec.references.entry_indent_type, "hanging")
        self.assertEqual(self.spec.references.hanging_indent_inches, 0.5)

    def test_no_running_head(self):
        self.assertFalse(self.spec.running_head.enabled)

    def test_note_citations(self):
        self.assertEqual(self.spec.in_text_citations.style, "note")

    def test_heading_level1_centered_bold(self):
        h1 = self.spec.headings.level_1
        self.assertEqual(h1.alignment, "center")
        self.assertTrue(h1.bold)

    def test_heading_level2_centered_italic(self):
        h2 = self.spec.headings.level_2
        self.assertEqual(h2.alignment, "center")
        self.assertTrue(h2.italic)
        self.assertFalse(h2.bold)

    def test_heading_level3_left_bold(self):
        h3 = self.spec.headings.level_3
        self.assertEqual(h3.alignment, "left")
        self.assertTrue(h3.bold)


# ══════════════════════════════════════════════════════════════
#  MLA TRANSFORMATION TESTS
# ══════════════════════════════════════════════════════════════

class TestMLATransformation(unittest.TestCase):
    """Verify MLA formatting is applied correctly."""

    @classmethod
    def setUpClass(cls):
        ri = RuleInterpreterAgent()
        cls.spec = ri.get_style_spec("mla")
        cls.docir = _build_simple_docir()
        cls.out_path, cls.changes, cls.doc = _run_transform(cls.docir, cls.spec)

    def test_page_margins_one_inch(self):
        for section in self.doc.sections:
            self.assertAlmostEqual(section.top_margin / 914400, 1.0, places=1)
            self.assertAlmostEqual(section.left_margin / 914400, 1.0, places=1)

    def test_font_is_times_new_roman(self):
        style = self.doc.styles["Normal"]
        self.assertEqual(style.font.name, "Times New Roman")

    def test_font_size_12pt(self):
        style = self.doc.styles["Normal"]
        self.assertEqual(style.font.size, Pt(12))

    def test_double_spacing(self):
        style = self.doc.styles["Normal"]
        pf = style.paragraph_format
        self.assertAlmostEqual(pf.line_spacing, 2.0, places=1)

    def test_no_page_break_before_body(self):
        """MLA has no title page, so no page break before body."""
        body_paras = [p for p in self.doc.paragraphs if "Body paragraph" in p.text]
        for p in body_paras:
            pf = p.paragraph_format
            # Should not have page_break_before set
            self.assertNotEqual(pf.page_break_before, True)

    def test_works_cited_label_present(self):
        found = any("Works Cited" in p.text for p in self.doc.paragraphs)
        self.assertTrue(found, "Works Cited label should be present")

    def test_heading_bold(self):
        heading_paras = [p for p in self.doc.paragraphs
                        if p.text.strip() in ("Introduction", "Conclusion")]
        for p in heading_paras:
            runs_bold = [r.bold for r in p.runs if r.text.strip()]
            self.assertTrue(any(runs_bold), f"Heading '{p.text}' should be bold")

    def test_layout_change_recorded(self):
        cats = {c.category for c in self.changes}
        self.assertIn("page_layout", cats)

    def test_typography_change_recorded(self):
        cats = {c.category for c in self.changes}
        self.assertIn("typography", cats)

    def test_first_line_indent(self):
        style = self.doc.styles["Normal"]
        pf = style.paragraph_format
        fi = pf.first_line_indent
        self.assertIsNotNone(fi)
        # 0.5 inches
        self.assertAlmostEqual(fi / 914400, 0.5, places=1)


# ══════════════════════════════════════════════════════════════
#  CHICAGO TRANSFORMATION TESTS
# ══════════════════════════════════════════════════════════════

class TestChicagoTransformation(unittest.TestCase):
    """Verify Chicago formatting is applied correctly."""

    @classmethod
    def setUpClass(cls):
        ri = RuleInterpreterAgent()
        cls.spec = ri.get_style_spec("chicago")
        cls.docir = _build_simple_docir()
        cls.out_path, cls.changes, cls.doc = _run_transform(cls.docir, cls.spec)

    def test_page_margins_one_inch(self):
        for section in self.doc.sections:
            self.assertAlmostEqual(section.top_margin / 914400, 1.0, places=1)
            self.assertAlmostEqual(section.left_margin / 914400, 1.0, places=1)

    def test_font_is_times_new_roman(self):
        style = self.doc.styles["Normal"]
        self.assertEqual(style.font.name, "Times New Roman")

    def test_font_size_12pt(self):
        style = self.doc.styles["Normal"]
        self.assertEqual(style.font.size, Pt(12))

    def test_double_spacing(self):
        style = self.doc.styles["Normal"]
        pf = style.paragraph_format
        self.assertAlmostEqual(pf.line_spacing, 2.0, places=1)

    def test_title_page_has_page_break(self):
        """Chicago requires title page, so abstract or body should start on new page."""
        # Check that a page break exists somewhere after title
        found_break = False
        for p in self.doc.paragraphs:
            if p.paragraph_format.page_break_before:
                found_break = True
                break
        self.assertTrue(found_break, "Chicago should have page break for title page")

    def test_bibliography_label_present(self):
        found = any("Bibliography" in p.text for p in self.doc.paragraphs)
        self.assertTrue(found, "Bibliography label should be present")

    def test_heading_bold(self):
        heading_paras = [p for p in self.doc.paragraphs
                        if p.text.strip() in ("Introduction", "Conclusion")]
        for p in heading_paras:
            runs_bold = [r.bold for r in p.runs if r.text.strip()]
            self.assertTrue(any(runs_bold), f"Heading '{p.text}' should be bold")

    def test_title_bold(self):
        title_paras = [p for p in self.doc.paragraphs
                      if "Test Paper Title" in p.text]
        self.assertTrue(len(title_paras) > 0, "Title should be present")
        for p in title_paras:
            runs_bold = [r.bold for r in p.runs if r.text.strip()]
            self.assertTrue(any(runs_bold), "Chicago title should be bold")

    def test_first_line_indent(self):
        style = self.doc.styles["Normal"]
        pf = style.paragraph_format
        fi = pf.first_line_indent
        self.assertIsNotNone(fi)
        self.assertAlmostEqual(fi / 914400, 0.5, places=1)

    def test_layout_change_recorded(self):
        cats = {c.category for c in self.changes}
        self.assertIn("page_layout", cats)


# ══════════════════════════════════════════════════════════════
#  CROSS-STYLE COMPARISON TESTS
# ══════════════════════════════════════════════════════════════

class TestCrossStyleComparison(unittest.TestCase):
    """Verify key differences between all 5 styles."""

    @classmethod
    def setUpClass(cls):
        ri = RuleInterpreterAgent()
        cls.apa7 = ri.get_style_spec("apa7")
        cls.ieee = ri.get_style_spec("ieee")
        cls.van = ri.get_style_spec("vancouver")
        cls.mla = ri.get_style_spec("mla")
        cls.chi = ri.get_style_spec("chicago")

    def test_all_use_times_new_roman(self):
        for spec in [self.apa7, self.mla, self.chi, self.van]:
            self.assertEqual(spec.default_typography.font_name, "Times New Roman")

    def test_ieee_uses_times_10pt(self):
        self.assertEqual(self.ieee.default_typography.font_size_pt, 10.0)

    def test_mla_no_abstract(self):
        self.assertEqual(self.mla.abstract.label, "")

    def test_chicago_has_abstract(self):
        self.assertEqual(self.chi.abstract.label, "Abstract")

    def test_reference_labels_differ(self):
        labels = {
            self.apa7.references.section_label,
            self.mla.references.section_label,
            self.chi.references.section_label,
        }
        self.assertEqual(len(labels), 3, "APA7, MLA, Chicago should have different ref labels")

    def test_title_page_required_apa7_chicago(self):
        self.assertTrue(self.apa7.title_page.required)
        self.assertTrue(self.chi.title_page.required)

    def test_title_page_not_required_mla_ieee(self):
        self.assertFalse(self.mla.title_page.required)
        self.assertFalse(self.ieee.title_page.required)

    def test_mla_title_not_bold(self):
        self.assertFalse(self.mla.title_page.title.bold)

    def test_apa7_title_bold(self):
        self.assertTrue(self.apa7.title_page.title.bold)

    def test_chicago_note_citations(self):
        self.assertEqual(self.chi.in_text_citations.style, "note")

    def test_apa7_author_date_citations(self):
        self.assertEqual(self.apa7.in_text_citations.style, "author-date")

    def test_ieee_numeric_citations(self):
        self.assertEqual(self.ieee.in_text_citations.style, "numeric")

    def test_vancouver_numeric_citations(self):
        self.assertEqual(self.van.in_text_citations.style, "numeric")

    def test_all_five_styles_have_unique_ids(self):
        ids = {s.style_id for s in [self.apa7, self.ieee, self.van, self.mla, self.chi]}
        self.assertEqual(len(ids), 5)


# ══════════════════════════════════════════════════════════════
#  VALIDATOR TESTS FOR MLA/CHICAGO
# ══════════════════════════════════════════════════════════════

class TestMLAValidatorAbstract(unittest.TestCase):
    """Verify validator gives full marks for abstract when style has no abstract."""

    def test_mla_abstract_100_percent(self):
        """MLA has no abstract, so validator should give 100%."""
        from backend.agents.validator import ValidatorAgent
        ri = RuleInterpreterAgent()
        spec = ri.get_style_spec("mla")
        docir = _build_simple_docir()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            input_path = tmpdir / "input.docx"
            _create_docx(docir, input_path)
            agent = TransformerAgent()
            out_path, changes = agent.transform(docir, spec, input_path, output_dir=tmpdir)

            validator = ValidatorAgent()
            from backend.schemas.reports import CitationReport
            report = validator.validate(out_path, spec, changes, CitationReport())

            abstract_cat = [c for c in report.categories if c.category == "abstract"]
            self.assertTrue(len(abstract_cat) > 0)
            self.assertEqual(abstract_cat[0].score, 100.0,
                           "MLA abstract should be 100% since MLA has no abstract")


if __name__ == "__main__":
    unittest.main()
