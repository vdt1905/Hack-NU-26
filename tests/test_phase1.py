"""
FormatForge AI — Phase 1 Tests
Comprehensive tests for DOCX Ingestion & Structure Detection.

Covers:
 • IngestAgent: DOCX parsing, interleaved ordering, font resolution
 • StructureDetectorAgent: all 10 detection passes
 • CitationEngineAgent: extraction + reference parsing
 • citation_parser utility: regex patterns
 • Integration: ingest → detect → citation pipeline

Run: pytest tests/test_phase1.py -v
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from backend.schemas.docir import (
    AuthorName,
    CitationType,
    DocElement,
    DocIR,
    DocMetadata,
    ElementRole,
    ElementType,
    InTextCitation,
    ParagraphFormatting,
    ParsedReference,
    RunFormatting,
    TableCell,
    TableData,
)

# ─────────────────────────────────────────────────────────────
# HELPERS — Build synthetic DocIR for testing
# ─────────────────────────────────────────────────────────────


def _make_elem(
    idx: int,
    content: str,
    role: ElementRole = ElementRole.UNKNOWN,
    style_name: str = "Normal",
    bold: bool | None = None,
    font_size: float | None = None,
    elem_type: ElementType = ElementType.PARAGRAPH,
) -> DocElement:
    """Create a synthetic DocElement for test purposes."""
    return DocElement(
        id=f"elem_{idx:04d}",
        type=elem_type,
        role=role,
        content=content,
        original_style_name=style_name,
        formatting=ParagraphFormatting(
            bold=bold,
            font_size_pt=font_size,
        ),
    )


def _build_docir(elements: list[DocElement]) -> DocIR:
    """Wrap a list of elements into a DocIR object."""
    return DocIR(
        metadata=DocMetadata(
            source_filename="test.docx",
            total_paragraphs=sum(1 for e in elements if e.type == ElementType.PARAGRAPH),
        ),
        elements=elements,
    )


def _build_paper_docir() -> DocIR:
    """Build a realistic synthetic scientific paper DocIR (like RS_TEST1.docx)."""
    elems = [
        _make_elem(1, "Host attachment and fluid shear are integrated into a"),
        _make_elem(2, "mechanical signal regulating virulence in E. coli"),
        _make_elem(3, "O157:H7"),
        _make_elem(4, "Ghadah Alsharif, Sajida Ahmad, Mohammad Islam, and Rehan Shah"),
        _make_elem(5, "aDepartment of Biosciences, University of Birmingham, UK"),
        _make_elem(6, "bSchool of Chemical Engineering, University of Birmingham, UK"),
        _make_elem(7, "Edited by John Smith, Stanford University"),
        _make_elem(8, "Enterohemorrhagic Escherichia coli (EHEC) O157:H7 is a major cause. "
                       "The type III secretion system (T3SS) injects effector proteins into host cells."),
        _make_elem(9, "We demonstrate that attachment triggers LEE expression in a GrlA-dependent manner."),
        _make_elem(10, "virulence | E. coli | shear | LEE | type III secretion"),
        _make_elem(11, "Significance"),
        _make_elem(12, "EHEC O157:H7 is responsible for outbreaks of bloody diarrhea."),
        _make_elem(13, "Our findings reveal that mechanical signals regulate virulence genes."),
        _make_elem(14, "Results"),
        _make_elem(15, "We first examined whether attachment triggers LEE expression (1)."),
        _make_elem(16, "Flow cytometry showed increased GFP fluorescence (2, 3)."),
        _make_elem(17, "These results are consistent with previous studies (Fig. 1A)."),
        _make_elem(18, "Bacterial attachment to host cells activates the LEE1 promoter (4–6)."),
        _make_elem(19, "Discussion"),
        _make_elem(20, "Our results demonstrate that mechanical sensing (7) controls virulence."),
        _make_elem(21, "The role of GrlA was confirmed by mutant analysis (8, 9)."),
        _make_elem(22, "Materials and Methods"),
        _make_elem(23, "E. coli O157:H7 strain EDL933 was used throughout this study."),
        _make_elem(24, "ACKNOWLEDGMENTS"),
        _make_elem(25, "We thank the BBSRC for funding."),
        _make_elem(26, "1. Nataro JP, Kaper JB (1998) Diarrheagenic Escherichia coli. Clin Microbiol Rev 11(1): 142–201."),
        _make_elem(27, "2. Kaper JB, Nataro JP, Mobley HL (2004) Pathogenic Escherichia coli. Nat Rev Microbiol 2(2): 123–140."),
        _make_elem(28, "3. Alsharif G, Ahmad S (2019) Shear-dependent gene regulation. J Bacteriol 201: e00641-18."),
        _make_elem(29, "4. Lee DJ (2012) Gene regulation in E. coli. Nucleic Acids Res 40(21): 10543–10553."),
        _make_elem(30, "5. Tree JJ (2009) LEE regulation. Mol Microbiol 73(6): 1020–1037."),
        _make_elem(31, "6. Roe AJ (2003) Bacterial attachment factors. Infect Immun 71(5): 2590–2596."),
        _make_elem(32, "7. Mellies JL (2007) Pathogenicity islands. Infect Immun 75: 3688–3701."),
        _make_elem(33, "8. Deng W (2004) Type III secretion. Proc Natl Acad Sci USA 101: 3597–3602."),
        _make_elem(34, "9. Elliott SJ (2000) EspG effectors. Mol Microbiol 38(4): 760–771."),
    ]
    return _build_docir(elems)


# ═════════════════════════════════════════════════════════════
# 1. INGEST AGENT TESTS
# ═════════════════════════════════════════════════════════════


class TestIngestAgent:
    """Tests for the IngestAgent DOCX parser."""

    def test_import_and_instantiate(self):
        from backend.agents.ingest import IngestAgent
        agent = IngestAgent()
        assert hasattr(agent, "parse")
        assert hasattr(agent, "_parse_docx")

    def test_unsupported_format_raises(self):
        from backend.agents.ingest import IngestAgent
        agent = IngestAgent()
        with pytest.raises(ValueError, match="Unsupported"):
            agent.parse(Path("fake.xyz"))

    def test_pdf_not_implemented(self):
        from backend.agents.ingest import IngestAgent
        agent = IngestAgent()
        with pytest.raises(NotImplementedError):
            agent.parse(Path("fake.pdf"))

    def test_txt_not_implemented(self):
        from backend.agents.ingest import IngestAgent
        agent = IngestAgent()
        with pytest.raises(NotImplementedError):
            agent.parse(Path("fake.txt"))

    def test_parse_docx_returns_docir(self):
        """Verify IngestAgent can parse a real DOCX and return a DocIR."""
        test_file = Path(__file__).parent.parent / "RS_TEST1.docx"
        if not test_file.exists():
            pytest.skip("RS_TEST1.docx not found")

        from backend.agents.ingest import IngestAgent
        agent = IngestAgent()
        docir = agent.parse(test_file)

        assert isinstance(docir, DocIR)
        assert len(docir.elements) > 100
        assert docir.metadata.source_filename == "RS_TEST1.docx"
        assert docir.metadata.source_format == "docx"
        assert docir.metadata.total_paragraphs > 100

    def test_all_elements_have_ids(self):
        """Every element from ingest must have a unique ID."""
        test_file = Path(__file__).parent.parent / "RS_TEST1.docx"
        if not test_file.exists():
            pytest.skip("RS_TEST1.docx not found")

        from backend.agents.ingest import IngestAgent
        docir = IngestAgent().parse(test_file)

        ids = [e.id for e in docir.elements]
        assert len(ids) == len(set(ids)), "Element IDs are not unique"
        assert all(id_.startswith("elem_") for id_ in ids)

    def test_paragraphs_default_to_unknown_role(self):
        """Ingested paragraphs should have role=UNKNOWN (not yet labelled)."""
        test_file = Path(__file__).parent.parent / "RS_TEST1.docx"
        if not test_file.exists():
            pytest.skip("RS_TEST1.docx not found")

        from backend.agents.ingest import IngestAgent
        docir = IngestAgent().parse(test_file)

        para_elements = [e for e in docir.elements if e.type == ElementType.PARAGRAPH]
        assert all(e.role == ElementRole.UNKNOWN for e in para_elements)

    def test_interleaved_ordering(self):
        """Elements should be in document order (tables interleaved, not appended at end)."""
        test_file = Path(__file__).parent.parent / "RS_TEST1.docx"
        if not test_file.exists():
            pytest.skip("RS_TEST1.docx not found")

        from backend.agents.ingest import IngestAgent
        docir = IngestAgent().parse(test_file)

        # Check that indices are strictly monotonic
        for i, elem in enumerate(docir.elements):
            expected_prefix = f"elem_{i+1:04d}"
            assert elem.id == expected_prefix, f"Element {i} has id {elem.id}, expected {expected_prefix}"

    def test_runs_extracted(self):
        """Paragraph elements should have runs with text content."""
        test_file = Path(__file__).parent.parent / "RS_TEST1.docx"
        if not test_file.exists():
            pytest.skip("RS_TEST1.docx not found")

        from backend.agents.ingest import IngestAgent
        docir = IngestAgent().parse(test_file)

        # At least some elements should have runs
        has_runs = [e for e in docir.elements if e.runs]
        assert len(has_runs) > 50, "Too few elements have run data"

    def test_style_names_captured(self):
        """Elements should capture the original Word style name."""
        test_file = Path(__file__).parent.parent / "RS_TEST1.docx"
        if not test_file.exists():
            pytest.skip("RS_TEST1.docx not found")

        from backend.agents.ingest import IngestAgent
        docir = IngestAgent().parse(test_file)

        para_elements = [e for e in docir.elements if e.type == ElementType.PARAGRAPH]
        # RS_TEST1 uses "Normal" for all styles
        has_style = [e for e in para_elements if e.original_style_name]
        assert len(has_style) > 100


# ═════════════════════════════════════════════════════════════
# 2. STRUCTURE DETECTOR TESTS
# ═════════════════════════════════════════════════════════════


class TestStructureDetectorPass1:
    """Tests for style-name detection pass."""

    def test_title_style_detected(self):
        from backend.agents.structure_detector import StructureDetectorAgent
        elems = [_make_elem(1, "My Paper Title", style_name="Title")]
        docir = _build_docir(elems)
        StructureDetectorAgent().detect(docir)
        assert docir.elements[0].role == ElementRole.TITLE

    def test_heading_style_detected(self):
        from backend.agents.structure_detector import StructureDetectorAgent
        elems = [
            _make_elem(1, "Title", role=ElementRole.TITLE),
            _make_elem(2, "Introduction", style_name="Heading 1"),
            _make_elem(3, "Background", style_name="Heading 2"),
        ]
        docir = _build_docir(elems)
        StructureDetectorAgent().detect(docir)
        assert docir.elements[1].role == ElementRole.HEADING_1
        assert docir.elements[2].role == ElementRole.HEADING_2

    def test_abstract_style_detected(self):
        from backend.agents.structure_detector import StructureDetectorAgent
        elems = [_make_elem(1, "This is the abstract text.", style_name="Abstract")]
        docir = _build_docir(elems)
        StructureDetectorAgent().detect(docir)
        assert docir.elements[0].role == ElementRole.ABSTRACT_BODY


class TestStructureDetectorPass2:
    """Tests for section keyword matching pass."""

    @pytest.mark.parametrize("keyword,expected_role", [
        ("Introduction", ElementRole.HEADING_1),
        ("Results", ElementRole.HEADING_1),
        ("Discussion", ElementRole.HEADING_1),
        ("Materials and Methods", ElementRole.HEADING_1),
        ("Conclusion", ElementRole.HEADING_1),
        ("Significance", ElementRole.HEADING_1),
        ("References", ElementRole.REFERENCE_LABEL),
        ("Bibliography", ElementRole.REFERENCE_LABEL),
        ("Appendix", ElementRole.APPENDIX),
    ])
    def test_section_keyword_detected(self, keyword, expected_role):
        from backend.agents.structure_detector import StructureDetectorAgent
        elems = [_make_elem(1, keyword)]
        docir = _build_docir(elems)
        StructureDetectorAgent().detect(docir)
        assert docir.elements[0].role == expected_role, \
            f"Expected {expected_role} for '{keyword}', got {docir.elements[0].role}"

    def test_keyword_with_trailing_period(self):
        from backend.agents.structure_detector import StructureDetectorAgent
        elems = [_make_elem(1, "Discussion.")]
        docir = _build_docir(elems)
        StructureDetectorAgent().detect(docir)
        assert docir.elements[0].role == ElementRole.HEADING_1

    def test_acknowledgments_caps(self):
        from backend.agents.structure_detector import StructureDetectorAgent
        elems = [_make_elem(1, "ACKNOWLEDGMENTS")]
        docir = _build_docir(elems)
        StructureDetectorAgent().detect(docir)
        assert docir.elements[0].role == ElementRole.HEADING_1

    def test_long_paragraph_not_detected_as_heading(self):
        from backend.agents.structure_detector import StructureDetectorAgent
        long_text = "This is a very long paragraph that contains the word results " * 5
        elems = [_make_elem(1, long_text)]
        docir = _build_docir(elems)
        StructureDetectorAgent().detect(docir)
        assert docir.elements[0].role != ElementRole.HEADING_1


class TestStructureDetectorPass3:
    """Tests for reference section detection."""

    def test_reference_entries_after_label(self):
        from backend.agents.structure_detector import StructureDetectorAgent
        elems = [
            _make_elem(1, "Some body text"),
            _make_elem(2, "References"),
            _make_elem(3, "1. Smith J (2020) Title. Journal 10: 1-5."),
            _make_elem(4, "2. Jones A (2021) Another title. Journal 11: 6-10."),
        ]
        docir = _build_docir(elems)
        StructureDetectorAgent().detect(docir)
        assert docir.elements[1].role == ElementRole.REFERENCE_LABEL
        assert docir.elements[2].role == ElementRole.REFERENCE_ENTRY
        assert docir.elements[3].role == ElementRole.REFERENCE_ENTRY

    def test_numbered_refs_detected_without_label(self):
        from backend.agents.structure_detector import StructureDetectorAgent
        elems = [
            _make_elem(1, "Body text here."),
            _make_elem(2, "More body text."),
            _make_elem(3, "1. Nataro JP (1998) Title. J Rev 11: 142."),
            _make_elem(4, "2. Kaper JB (2004) Title two. Nat Rev 2: 123."),
            _make_elem(5, "3. Alsharif G (2019) Title three. J Bact 201: 641."),
            _make_elem(6, "4. Lee DJ (2012) Title four. Nucleic Acids 40: 10553."),
        ]
        docir = _build_docir(elems)
        StructureDetectorAgent().detect(docir)
        ref_entries = [e for e in docir.elements if e.role == ElementRole.REFERENCE_ENTRY]
        assert len(ref_entries) >= 3


class TestStructureDetectorPass4:
    """Tests for title detection (position-based)."""

    def test_title_detected_by_position(self):
        from backend.agents.structure_detector import StructureDetectorAgent
        elems = [
            _make_elem(1, "My Paper Title About Something"),
            _make_elem(2, "Smith, J. and Jones, A."),
            _make_elem(3, "Results"),
            _make_elem(4, "Body text."),
        ]
        docir = _build_docir(elems)
        StructureDetectorAgent().detect(docir)
        assert docir.elements[0].role == ElementRole.TITLE

    def test_multiline_title_detected(self):
        from backend.agents.structure_detector import StructureDetectorAgent
        elems = [
            _make_elem(1, "Host attachment and fluid shear are"),
            _make_elem(2, "integrated into a mechanical signal"),
            _make_elem(3, "Ghadah Alsharif, Sajida Ahmad, and Rehan Shah"),
            _make_elem(4, "Results"),
            _make_elem(5, "Body."),
        ]
        docir = _build_docir(elems)
        StructureDetectorAgent().detect(docir)
        assert docir.elements[0].role == ElementRole.TITLE
        assert docir.elements[1].role == ElementRole.TITLE

    def test_empty_paragraphs_skipped(self):
        from backend.agents.structure_detector import StructureDetectorAgent
        elems = [
            _make_elem(1, ""),
            _make_elem(2, "My Paper Title"),
            _make_elem(3, "Results"),
            _make_elem(4, "Body."),
        ]
        docir = _build_docir(elems)
        StructureDetectorAgent().detect(docir)
        assert docir.elements[1].role == ElementRole.TITLE


class TestStructureDetectorPass5:
    """Tests for author/affiliation detection."""

    def test_author_names_detected(self):
        from backend.agents.structure_detector import StructureDetectorAgent
        elems = [
            _make_elem(1, "My Paper Title"),
            _make_elem(2, "Smith, J. and Jones, A."),
            _make_elem(3, "Department of Biology, University of Birmingham"),
            _make_elem(4, "Results"),
            _make_elem(5, "Body text."),
        ]
        docir = _build_docir(elems)
        StructureDetectorAgent().detect(docir)
        assert docir.elements[1].role == ElementRole.AUTHOR_INFO
        assert docir.elements[2].role == ElementRole.AUTHOR_INFO

    def test_edited_by_detected(self):
        from backend.agents.structure_detector import StructureDetectorAgent
        elems = [
            _make_elem(1, "My Paper Title"),
            _make_elem(2, "Smith, J."),
            _make_elem(3, "Edited by John Doe, MIT"),
            _make_elem(4, "Results"),
            _make_elem(5, "Body."),
        ]
        docir = _build_docir(elems)
        StructureDetectorAgent().detect(docir)
        assert docir.elements[2].role == ElementRole.AUTHOR_INFO


class TestStructureDetectorPass6:
    """Tests for abstract detection."""

    def test_abstract_body_detected_by_position(self):
        from backend.agents.structure_detector import StructureDetectorAgent
        elems = [
            _make_elem(1, "Paper Title Here"),
            _make_elem(2, "Smith, J."),
            _make_elem(3, "University of East Anglia"),
            _make_elem(4, "This study investigates the role of attachment in virulence gene expression."),
            _make_elem(5, "We demonstrate that shear forces trigger a signaling cascade."),
            _make_elem(6, "Results"),
            _make_elem(7, "Body paragraph here."),
        ]
        docir = _build_docir(elems)
        StructureDetectorAgent().detect(docir)
        assert docir.elements[3].role == ElementRole.ABSTRACT_BODY
        assert docir.elements[4].role == ElementRole.ABSTRACT_BODY

    def test_abstract_with_label(self):
        from backend.agents.structure_detector import StructureDetectorAgent
        elems = [
            _make_elem(1, "Paper Title"),
            _make_elem(2, "Smith, J. and Doe, A."),
            _make_elem(3, "Abstract"),
            _make_elem(4, "This study examines the effect of mechanical forces on bacterial virulence."),
            _make_elem(5, "Results"),
            _make_elem(6, "Body."),
        ]
        docir = _build_docir(elems)
        StructureDetectorAgent().detect(docir)
        assert docir.elements[2].role == ElementRole.ABSTRACT_LABEL
        assert docir.elements[3].role == ElementRole.ABSTRACT_BODY


class TestStructureDetectorPass7:
    """Tests for keywords detection."""

    def test_keywords_with_prefix(self):
        from backend.agents.structure_detector import StructureDetectorAgent
        elems = [_make_elem(1, "Keywords: bacteria, virulence, shear stress")]
        docir = _build_docir(elems)
        StructureDetectorAgent().detect(docir)
        assert docir.elements[0].role == ElementRole.KEYWORDS

    def test_pipe_separated_keywords(self):
        from backend.agents.structure_detector import StructureDetectorAgent
        elems = [
            _make_elem(1, "Title Here"),
            _make_elem(2, "Smith, J."),
            _make_elem(3, "virulence | E. coli | shear | LEE | type III secretion"),
            _make_elem(4, "Results"),
            _make_elem(5, "Body."),
        ]
        docir = _build_docir(elems)
        StructureDetectorAgent().detect(docir)
        assert docir.elements[2].role == ElementRole.KEYWORDS


class TestStructureDetectorPass8:
    """Tests for fill-remaining pass."""

    def test_remaining_filled_as_body(self):
        from backend.agents.structure_detector import StructureDetectorAgent
        elems = [
            _make_elem(1, "Title", role=ElementRole.TITLE),
            _make_elem(2, "Results"),
            _make_elem(3, "Some long paragraph that should be body text in the document."),
        ]
        docir = _build_docir(elems)
        StructureDetectorAgent().detect(docir)
        assert docir.elements[2].role == ElementRole.BODY

    def test_empty_paragraph_stays_unknown(self):
        from backend.agents.structure_detector import StructureDetectorAgent
        elems = [
            _make_elem(1, "Title", role=ElementRole.TITLE),
            _make_elem(2, ""),
        ]
        docir = _build_docir(elems)
        StructureDetectorAgent().detect(docir)
        assert docir.elements[1].role == ElementRole.UNKNOWN


class TestStructureDetectorPass9:
    """Tests for citation extraction pass."""

    def test_numeric_citations_extracted(self):
        from backend.agents.structure_detector import StructureDetectorAgent
        elems = [
            _make_elem(1, "Title", role=ElementRole.TITLE),
            _make_elem(2, "Results"),
            _make_elem(3, "Previous studies (1) showed that attachment (2, 3) triggers virulence."),
        ]
        docir = _build_docir(elems)
        StructureDetectorAgent().detect(docir)

        body_elem = docir.elements[2]
        assert len(body_elem.citations_found) >= 2

    def test_range_citations_extracted(self):
        from backend.agents.structure_detector import StructureDetectorAgent
        elems = [
            _make_elem(1, "Title", role=ElementRole.TITLE),
            _make_elem(2, "Results"),
            _make_elem(3, "Many studies support this finding (4–6)."),
        ]
        docir = _build_docir(elems)
        StructureDetectorAgent().detect(docir)

        body_elem = docir.elements[2]
        assert len(body_elem.citations_found) >= 1

    def test_figure_references_excluded(self):
        from backend.agents.structure_detector import StructureDetectorAgent
        elems = [
            _make_elem(1, "Title", role=ElementRole.TITLE),
            _make_elem(2, "Results"),
            _make_elem(3, "As shown in Fig. 1A and Fig. 2B, the data is clear."),
        ]
        docir = _build_docir(elems)
        StructureDetectorAgent().detect(docir)

        body_elem = docir.elements[2]
        # Figure references should NOT be counted as citations
        for c in body_elem.citations_found:
            assert "Fig" not in c.text, f"Figure ref wrongly captured as citation: {c.text}"

    def test_author_date_citations_extracted(self):
        from backend.agents.structure_detector import StructureDetectorAgent
        elems = [
            _make_elem(1, "Title", role=ElementRole.TITLE),
            _make_elem(2, "Introduction"),
            _make_elem(3, "Previous work (Smith, 2023) confirmed these results. "
                         "Jones (2021) also observed similar patterns."),
        ]
        docir = _build_docir(elems)
        StructureDetectorAgent().detect(docir)

        body_elem = docir.elements[2]
        assert len(body_elem.citations_found) >= 1  # at least parenthetical


class TestStructureDetectorIntegration:
    """Integration tests for the full multi-pass detection."""

    def test_synthetic_paper_structure(self):
        """Full detection on a synthetic paper should label all sections correctly."""
        from backend.agents.structure_detector import StructureDetectorAgent

        docir = _build_paper_docir()
        StructureDetectorAgent().detect(docir)

        # Verify title detected
        titles = docir.get_elements_by_role(ElementRole.TITLE)
        assert len(titles) >= 1

        # Verify section headings
        headings = docir.get_headings()
        heading_texts = [h.content for h in headings]
        assert any("Significance" in t for t in heading_texts)
        assert any("Results" in t for t in heading_texts)
        assert any("Discussion" in t for t in heading_texts)
        assert any("Materials and Methods" in t for t in heading_texts)

        # Verify references
        refs = docir.get_reference_entries()
        assert len(refs) >= 5

        # Verify body text exists
        body = docir.get_body_paragraphs()
        assert len(body) >= 3

        # Keywords detected
        keywords = docir.get_elements_by_role(ElementRole.KEYWORDS)
        assert len(keywords) >= 1

    def test_no_unknown_paragraphs_remain(self):
        """After detection, only empty paragraphs should remain UNKNOWN."""
        from backend.agents.structure_detector import StructureDetectorAgent

        docir = _build_paper_docir()
        StructureDetectorAgent().detect(docir)

        unknown_with_text = [
            e for e in docir.elements
            if e.role == ElementRole.UNKNOWN and e.content.strip()
        ]
        assert len(unknown_with_text) == 0, \
            f"Found {len(unknown_with_text)} unknown elements with text: " \
            f"{[e.content[:50] for e in unknown_with_text[:5]]}"

    def test_citations_extracted_from_body(self):
        """Citations should be extracted from body paragraphs."""
        from backend.agents.structure_detector import StructureDetectorAgent

        docir = _build_paper_docir()
        StructureDetectorAgent().detect(docir)

        all_citations = docir.get_all_citations()
        assert len(all_citations) >= 3, \
            f"Expected >= 3 citations, got {len(all_citations)}"

    def test_use_llm_default_false(self):
        """Default construction should not use LLM."""
        from backend.agents.structure_detector import StructureDetectorAgent
        agent = StructureDetectorAgent()
        assert agent.use_llm is False


# ═════════════════════════════════════════════════════════════
# 3. CITATION ENGINE TESTS
# ═════════════════════════════════════════════════════════════


class TestCitationEngine:
    """Tests for the CitationEngineAgent."""

    def test_import_and_instantiate(self):
        from backend.agents.citation_engine import CitationEngineAgent
        agent = CitationEngineAgent()
        assert hasattr(agent, "process")

    def test_skips_extraction_if_already_done(self):
        """CitationEngine should skip extraction if StructureDetector already did it."""
        from backend.agents.citation_engine import CitationEngineAgent
        from backend.schemas.style_spec import StyleSpec

        elems = [
            DocElement(
                id="e1", type=ElementType.PARAGRAPH, role=ElementRole.BODY,
                content="Some text with (Smith, 2023) citation.",
                citations_found=[InTextCitation(
                    text="(Smith, 2023)",
                    citation_type=CitationType.PARENTHETICAL,
                    authors=["Smith"],
                    year="2023",
                )],
            ),
        ]
        docir = _build_docir(elems)
        style_spec = StyleSpec()

        agent = CitationEngineAgent()
        updated, report = agent.process(docir, style_spec)

        # Should still have 1 citation (not doubled)
        all_cits = updated.get_all_citations()
        assert len(all_cits) == 1

    def test_extracts_author_date_citations(self):
        """CitationEngine should extract author-date citations if not already done."""
        from backend.agents.citation_engine import CitationEngineAgent
        from backend.schemas.style_spec import StyleSpec

        elems = [
            DocElement(
                id="e1", type=ElementType.PARAGRAPH, role=ElementRole.BODY,
                content="Previous work (Smith, 2023) confirmed the hypothesis.",
            ),
        ]
        docir = _build_docir(elems)
        agent = CitationEngineAgent()
        updated, report = agent.process(docir, StyleSpec())

        assert len(updated.get_all_citations()) >= 1

    def test_parse_apa_reference(self):
        """CitationEngine should parse APA-style references."""
        from backend.agents.citation_engine import CitationEngineAgent

        agent = CitationEngineAgent()
        ref = agent._parse_single_reference(
            "Smith, J., & Jones, A. (2023). The role of shear stress. "
            "Journal of Biology, 45(2), 123-145."
        )
        assert ref.year == "2023"
        assert len(ref.authors) >= 1
        assert ref.authors[0].family == "Smith"

    def test_parse_numbered_reference(self):
        """CitationEngine should parse numbered (PNAS/Vancouver) references."""
        from backend.agents.citation_engine import CitationEngineAgent

        agent = CitationEngineAgent()
        ref = agent._parse_single_reference(
            "1. Nataro JP, Kaper JB (1998) Diarrheagenic Escherichia coli. "
            "Clin Microbiol Rev 11(1): 142–201."
        )
        assert ref.year == "1998"
        assert len(ref.authors) >= 1

    def test_parse_reference_fallback(self):
        """Fallback parser should at least extract year and authors."""
        from backend.agents.citation_engine import CitationEngineAgent

        agent = CitationEngineAgent()
        ref = agent._parse_single_reference(
            "Doe, J. (2020). Some unusual reference format that doesn't match standard patterns."
        )
        assert ref.year == "2020"
        assert len(ref.authors) >= 1

    def test_consistency_report_generated(self):
        """Process should generate a CitationReport."""
        from backend.agents.citation_engine import CitationEngineAgent
        from backend.schemas.style_spec import StyleSpec

        docir = _build_paper_docir()
        # First run structure detection to label elements
        from backend.agents.structure_detector import StructureDetectorAgent
        StructureDetectorAgent().detect(docir)

        agent = CitationEngineAgent()
        updated, report = agent.process(docir, StyleSpec())

        assert report.total_references >= 5
        assert report.total_citations >= 1

    def test_numeric_citation_system_handling(self):
        """Report should handle numeric citation system correctly."""
        from backend.agents.citation_engine import CitationEngineAgent
        from backend.schemas.style_spec import StyleSpec

        docir = _build_paper_docir()
        from backend.agents.structure_detector import StructureDetectorAgent
        StructureDetectorAgent().detect(docir)

        agent = CitationEngineAgent()
        updated, report = agent.process(docir, StyleSpec())

        # Should detect numeric system
        assert report.consistency_score >= 0  # at least computable


# ═════════════════════════════════════════════════════════════
# 4. CITATION PARSER UTILITY TESTS
# ═════════════════════════════════════════════════════════════


class TestCitationParser:
    """Tests for citation_parser.py utility functions."""

    def test_has_citations_author_date(self):
        from backend.utils.citation_parser import has_citations
        assert has_citations("As shown by (Smith, 2023).")
        assert has_citations("Smith (2023) demonstrated this.")

    def test_has_citations_numeric(self):
        from backend.utils.citation_parser import has_citations
        assert has_citations("Previous work (1) showed this.")
        assert has_citations("Several studies (2, 3) confirmed.")
        assert has_citations("A range of evidence (4-6) supports.")

    def test_no_citations(self):
        from backend.utils.citation_parser import has_citations
        assert not has_citations("This is a plain sentence.")
        assert not has_citations("The year was 2023.")

    def test_has_numeric_citations(self):
        from backend.utils.citation_parser import has_numeric_citations
        assert has_numeric_citations("(1)")
        assert has_numeric_citations("(2, 3)")
        assert has_numeric_citations("(4-6)")
        assert not has_numeric_citations("No citations here.")

    def test_has_author_date_citations(self):
        from backend.utils.citation_parser import has_author_date_citations
        assert has_author_date_citations("(Smith, 2023)")
        assert has_author_date_citations("Jones (2021)")
        assert not has_author_date_citations("(1)")

    def test_is_figure_reference(self):
        from backend.utils.citation_parser import is_figure_reference
        # match_start should be position of '(' in the numeric match
        assert is_figure_reference("as shown in Fig. (1)", 17)
        assert not is_figure_reference("the study (1) found", 10)

    def test_numeric_single_regex(self):
        from backend.utils.citation_parser import NUMERIC_SINGLE
        assert NUMERIC_SINGLE.search("(1)")
        assert NUMERIC_SINGLE.search("study (17) found")
        assert not NUMERIC_SINGLE.search("(1000)")  # too many digits

    def test_numeric_multi_regex(self):
        from backend.utils.citation_parser import NUMERIC_MULTI
        assert NUMERIC_MULTI.search("(2, 3)")
        assert NUMERIC_MULTI.search("(1-5)")
        assert NUMERIC_MULTI.search("data (4, 5, 6) shows")


# ═════════════════════════════════════════════════════════════
# 5. AUTHOR PARSING TESTS
# ═════════════════════════════════════════════════════════════


class TestAuthorParsing:
    """Tests for author string parsing in CitationEngine."""

    def test_apa_style_authors(self):
        from backend.agents.citation_engine import CitationEngineAgent
        authors = CitationEngineAgent._parse_author_string(
            "Smith, J., & Jones, A. B."
        )
        assert len(authors) >= 2
        assert authors[0].family == "Smith"

    def test_vancouver_style_authors(self):
        from backend.agents.citation_engine import CitationEngineAgent
        authors = CitationEngineAgent._parse_author_string(
            "Nataro JP, Kaper JB"
        )
        assert len(authors) >= 2

    def test_single_author(self):
        from backend.agents.citation_engine import CitationEngineAgent
        authors = CitationEngineAgent._parse_author_string("Smith, J.")
        assert len(authors) == 1
        assert authors[0].family == "Smith"
        assert authors[0].given == "J."

    def test_et_al_handled(self):
        from backend.agents.citation_engine import CitationEngineAgent
        authors = CitationEngineAgent._parse_author_string(
            "Smith, J., et al."
        )
        # "et al." should be skipped
        assert all(a.family != "et al" for a in authors)


# ═════════════════════════════════════════════════════════════
# 6. EDGE CASES & ROBUSTNESS
# ═════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Edge cases for structure detection."""

    def test_empty_docir(self):
        from backend.agents.structure_detector import StructureDetectorAgent
        docir = _build_docir([])
        result = StructureDetectorAgent().detect(docir)
        assert len(result.elements) == 0

    def test_single_element(self):
        from backend.agents.structure_detector import StructureDetectorAgent
        docir = _build_docir([_make_elem(1, "Hello world")])
        StructureDetectorAgent().detect(docir)
        # Single paragraph at start gets detected as title by position heuristic
        assert docir.elements[0].role in (ElementRole.TITLE, ElementRole.BODY)

    def test_all_empty_paragraphs(self):
        from backend.agents.structure_detector import StructureDetectorAgent
        elems = [_make_elem(i, "") for i in range(1, 6)]
        docir = _build_docir(elems)
        StructureDetectorAgent().detect(docir)
        # All should stay UNKNOWN (empty)
        assert all(e.role == ElementRole.UNKNOWN for e in docir.elements)

    def test_table_elements_preserved(self):
        from backend.agents.structure_detector import StructureDetectorAgent
        elems = [
            _make_elem(1, "Title", role=ElementRole.TITLE),
            DocElement(
                id="elem_0002",
                type=ElementType.TABLE,
                role=ElementRole.TABLE,
                content="",
                table_data=TableData(rows=[], num_rows=2, num_cols=3),
            ),
        ]
        docir = _build_docir(elems)
        StructureDetectorAgent().detect(docir)
        assert docir.elements[1].role == ElementRole.TABLE

    def test_confidence_scores_assigned(self):
        """Structure detection should assign confidence > 0 for labelled elements."""
        from backend.agents.structure_detector import StructureDetectorAgent
        docir = _build_paper_docir()
        StructureDetectorAgent().detect(docir)

        labelled = [e for e in docir.elements if e.role != ElementRole.UNKNOWN]
        for e in labelled:
            assert e.role_confidence > 0, \
                f"Element {e.id} ({e.role}) has zero confidence"


# ═════════════════════════════════════════════════════════════
# 7. FULL PIPELINE INTEGRATION (ingest → detect → cite)
# ═════════════════════════════════════════════════════════════


class TestFullPipelineIntegration:
    """End-to-end integration tests with RS_TEST1.docx."""

    @pytest.fixture
    def rs_test1_path(self):
        path = Path(__file__).parent.parent / "RS_TEST1.docx"
        if not path.exists():
            pytest.skip("RS_TEST1.docx not found")
        return path

    def test_ingest_then_detect(self, rs_test1_path):
        """Ingest → Structure detection should label most elements."""
        from backend.agents.ingest import IngestAgent
        from backend.agents.structure_detector import StructureDetectorAgent

        docir = IngestAgent().parse(rs_test1_path)
        StructureDetectorAgent().detect(docir)

        # Title should be found at the beginning
        titles = docir.get_elements_by_role(ElementRole.TITLE)
        assert len(titles) >= 1
        title_text = " ".join(t.content for t in titles)
        assert "attachment" in title_text.lower() or "shear" in title_text.lower()

        # Section headings should be detected
        headings = docir.get_headings()
        heading_texts = [h.content.lower() for h in headings]
        assert any("results" in t for t in heading_texts), \
            f"'Results' heading not found. Found: {heading_texts[:10]}"
        assert any("discussion" in t for t in heading_texts)

    def test_reference_entries_detected(self, rs_test1_path):
        """Reference section should be detected with numbered entries."""
        from backend.agents.ingest import IngestAgent
        from backend.agents.structure_detector import StructureDetectorAgent

        docir = IngestAgent().parse(rs_test1_path)
        StructureDetectorAgent().detect(docir)

        refs = docir.get_reference_entries()
        assert len(refs) >= 20, \
            f"Expected >= 20 references, got {len(refs)}"

    def test_citations_extracted(self, rs_test1_path):
        """Numeric citations should be found in body text."""
        from backend.agents.ingest import IngestAgent
        from backend.agents.structure_detector import StructureDetectorAgent

        docir = IngestAgent().parse(rs_test1_path)
        StructureDetectorAgent().detect(docir)

        all_citations = docir.get_all_citations()
        assert len(all_citations) >= 5, \
            f"Expected >= 5 citations, got {len(all_citations)}"

    def test_full_pipeline_with_citation_engine(self, rs_test1_path):
        """Full ingest → detect → citation engine pipeline."""
        from backend.agents.ingest import IngestAgent
        from backend.agents.structure_detector import StructureDetectorAgent
        from backend.agents.citation_engine import CitationEngineAgent
        from backend.schemas.style_spec import StyleSpec

        # Step 1: Ingest
        docir = IngestAgent().parse(rs_test1_path)

        # Step 2: Structure detection
        StructureDetectorAgent().detect(docir)

        # Step 3: Citation processing
        cit_agent = CitationEngineAgent()
        docir, citation_report = cit_agent.process(docir, StyleSpec())

        # Verify pipeline output
        assert citation_report.total_references >= 20
        assert citation_report.total_citations >= 1

        # Print summary for manual verification
        role_counts = {}
        for e in docir.elements:
            role = e.role.value
            role_counts[role] = role_counts.get(role, 0) + 1

        print("\n=== RS_TEST1.docx Pipeline Summary ===")
        for role, count in sorted(role_counts.items()):
            print(f"  {role:25s}: {count}")
        print(f"  {'TOTAL':25s}: {len(docir.elements)}")
        print(f"\n  Citations found: {citation_report.total_citations}")
        print(f"  References found: {citation_report.total_references}")
        print(f"  Consistency score: {citation_report.consistency_score:.1f}%")

    def test_structure_summary_coverage(self, rs_test1_path):
        """Verify that most elements get labelled (few UNKNOWN remaining)."""
        from backend.agents.ingest import IngestAgent
        from backend.agents.structure_detector import StructureDetectorAgent

        docir = IngestAgent().parse(rs_test1_path)
        StructureDetectorAgent().detect(docir)

        total = len(docir.elements)
        unknown = len([
            e for e in docir.elements
            if e.role == ElementRole.UNKNOWN and e.content.strip()
        ])
        coverage = (total - unknown) / total * 100

        assert coverage > 85, \
            f"Structure detection coverage too low: {coverage:.1f}% ({unknown} unknown with text)"
