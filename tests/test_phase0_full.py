"""
FormatForge AI — Comprehensive Phase 0 Validation
Tests every module, schema, agent stub, API, and utility.
Run: pytest tests/test_phase0_full.py -v
"""

import json
import sys
from pathlib import Path

import pytest

# ─────────────────────────────────────────────────────────────
# 1. CONFIG & PATHS
# ─────────────────────────────────────────────────────────────


def test_config_loads():
    """Config module loads without error and exposes expected constants."""
    from backend.config import (
        APP_NAME, APP_VERSION, PROJECT_ROOT, BACKEND_DIR,
        STYLES_DIR, OUTPUT_DIR, DEFAULT_STYLE, AVAILABLE_STYLES,
        SUPPORTED_INPUT_FORMATS,
    )
    assert APP_NAME == "FormatForge AI"
    assert APP_VERSION == "1.0.0"
    assert PROJECT_ROOT.exists()
    assert BACKEND_DIR.exists()
    assert STYLES_DIR.exists()
    assert DEFAULT_STYLE == "apa7"
    assert "apa7" in AVAILABLE_STYLES
    assert ".docx" in SUPPORTED_INPUT_FORMATS


def test_output_dirs_exist():
    """Output directories were auto-created by config import."""
    from backend.config import OUTPUT_FORMATTED_DIR, OUTPUT_REPORTS_DIR
    assert OUTPUT_FORMATTED_DIR.exists()
    assert OUTPUT_REPORTS_DIR.exists()


# ─────────────────────────────────────────────────────────────
# 2. SCHEMAS — DocIR
# ─────────────────────────────────────────────────────────────


def test_docir_element_types():
    """All ElementType and ElementRole enums are importable."""
    from backend.schemas.docir import ElementType, ElementRole
    assert len(ElementType) >= 4
    assert len(ElementRole) >= 15
    assert ElementType.PARAGRAPH.value == "paragraph"
    assert ElementRole.TITLE.value == "title"
    assert ElementRole.REFERENCE_ENTRY.value == "reference_entry"


def test_docir_run_formatting():
    """RunFormatting model works correctly."""
    from backend.schemas.docir import RunFormatting
    run = RunFormatting(text="Hello", bold=True, font_name="Arial", font_size_pt=14.0)
    assert run.text == "Hello"
    assert run.bold is True
    assert run.font_name == "Arial"
    d = run.model_dump()
    assert "text" in d


def test_docir_paragraph_formatting():
    """ParagraphFormatting model works correctly."""
    from backend.schemas.docir import ParagraphFormatting
    pf = ParagraphFormatting(
        font_name="Times New Roman",
        font_size_pt=12.0,
        alignment="center",
        line_spacing=2.0,
        first_line_indent_inches=0.5,
    )
    assert pf.line_spacing == 2.0


def test_docir_citation_models():
    """InTextCitation and ParsedReference work correctly."""
    from backend.schemas.docir import (
        InTextCitation, CitationType, ParsedReference, AuthorName,
    )
    cite = InTextCitation(
        text="(Smith, 2023)",
        citation_type=CitationType.PARENTHETICAL,
        authors=["Smith"],
        year="2023",
    )
    assert cite.citation_type == CitationType.PARENTHETICAL

    ref = ParsedReference(
        authors=[AuthorName(family="Smith", given="J.")],
        year="2023",
        title="Test Article",
        container_title="Journal of Testing",
    )
    assert ref.authors[0].family == "Smith"


def test_docir_table_data():
    """TableData model works correctly."""
    from backend.schemas.docir import TableData, TableCell
    td = TableData(
        rows=[[TableCell(text="A1", row=0, col=0)]],
        num_rows=1, num_cols=1,
    )
    assert td.num_rows == 1


def test_docir_full_roundtrip():
    """Build a full DocIR, serialize, deserialize, and verify."""
    from backend.schemas.docir import (
        DocIR, DocElement, DocMetadata, ElementType, ElementRole,
        ParagraphFormatting, RunFormatting,
    )
    meta = DocMetadata(source_filename="test.docx", total_paragraphs=3)
    elems = [
        DocElement(id="e1", type=ElementType.PARAGRAPH, role=ElementRole.TITLE,
                   content="Title", formatting=ParagraphFormatting(bold=True)),
        DocElement(id="e2", type=ElementType.PARAGRAPH, role=ElementRole.ABSTRACT_BODY,
                   content="Abstract text here"),
        DocElement(id="e3", type=ElementType.PARAGRAPH, role=ElementRole.BODY,
                   content="Body paragraph"),
    ]
    docir = DocIR(metadata=meta, elements=elems)
    data = docir.model_dump(mode="json")
    restored = DocIR.model_validate(data)
    assert len(restored.elements) == 3
    assert restored.get_title().content == "Title"
    assert restored.get_abstract().content == "Abstract text here"
    assert len(restored.get_body_paragraphs()) == 1
    assert len(restored.get_headings()) == 0


# ─────────────────────────────────────────────────────────────
# 3. SCHEMAS — StyleSpec
# ─────────────────────────────────────────────────────────────


def test_stylespec_defaults():
    """StyleSpec default construction produces valid APA 7 defaults."""
    from backend.schemas.style_spec import StyleSpec
    spec = StyleSpec()
    assert spec.style_name == "APA 7th Edition"
    assert spec.default_typography.font_name == "Times New Roman"
    assert spec.default_typography.font_size_pt == 12.0
    assert spec.default_typography.line_spacing == 2.0
    assert spec.page_layout.margin_top_inches == 1.0
    assert spec.headings.level_1.bold is True
    assert spec.headings.level_1.alignment == "center"
    assert spec.headings.get_level(2).bold is True


def test_stylespec_json_roundtrip():
    """StyleSpec can serialize to JSON and back."""
    from backend.schemas.style_spec import StyleSpec
    spec = StyleSpec()
    data = spec.model_dump(mode="json")
    assert isinstance(data, dict)
    restored = StyleSpec.model_validate(data)
    assert restored.style_id == spec.style_id


def test_apa7_json_file_valid():
    """Validate the apa7.json file loads and produces correct StyleSpec."""
    from backend.schemas.style_spec import StyleSpec
    from backend.config import STYLES_DIR
    path = STYLES_DIR / "apa7.json"
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    spec = StyleSpec.model_validate(data)
    assert spec.style_id == "apa7"
    assert spec.csl_style == "apa"
    assert spec.title_page.required is True
    assert spec.title_page.title.bold is True
    assert spec.abstract.label == "Abstract"
    assert spec.abstract.max_words == 250
    assert spec.references.entry_indent_type == "hanging"
    assert spec.references.hanging_indent_inches == 0.5
    assert spec.in_text_citations.style == "author-date"
    assert spec.in_text_citations.et_al_threshold == 3


# ─────────────────────────────────────────────────────────────
# 4. SCHEMAS — Reports
# ─────────────────────────────────────────────────────────────


def test_change_record():
    """ChangeRecord model works."""
    from backend.schemas.reports import ChangeRecord, ChangeStatus, Severity
    cr = ChangeRecord(
        element_id="e1", category="typography",
        description="Font changed from Calibri to TNR",
        old_value="Calibri 11pt", new_value="TNR 12pt",
        status=ChangeStatus.APPLIED, severity=Severity.INFO,
    )
    assert cr.status == ChangeStatus.APPLIED


def test_compliance_report_scoring():
    """ComplianceReport weighted scoring computation."""
    from backend.schemas.reports import ComplianceReport, CategoryScore
    report = ComplianceReport(style_name="APA 7")
    report.categories = [
        CategoryScore(category="page_layout", score=100, weight=0.5),
        CategoryScore(category="typography", score=50, weight=0.5),
    ]
    report.compute_overall_score()
    assert report.overall_score == pytest.approx(75.0, abs=0.1)


def test_citation_report_scoring():
    """CitationReport consistency scoring."""
    from backend.schemas.reports import CitationReport, OrphanReference
    cr = CitationReport(total_citations=10, total_references=10, matched=9)
    cr.orphan_citations = []
    cr.uncited_references = [OrphanReference(reference_text="Unused ref")]
    cr.format_issues = []
    cr.compute_score()
    assert cr.consistency_score > 90


def test_format_result():
    """FormatResult wraps all reports."""
    from backend.schemas.reports import FormatResult
    fr = FormatResult(success=True)
    assert fr.success is True
    assert fr.compliance_report is not None
    assert fr.citation_report is not None


# ─────────────────────────────────────────────────────────────
# 5. LLM CLIENT
# ─────────────────────────────────────────────────────────────


def test_llm_client_class_importable():
    """LLMClient class is importable and constructible (may fail without key)."""
    from backend.llm.client import LLMClient
    # Test that the class exists with expected methods
    assert hasattr(LLMClient, "chat")
    assert hasattr(LLMClient, "chat_json")
    assert hasattr(LLMClient, "is_available")


def test_get_llm_client_singleton():
    """get_llm_client returns a singleton."""
    from backend.llm.client import get_llm_client
    c1 = get_llm_client()
    c2 = get_llm_client()
    assert c1 is c2


def test_llm_prompts_defined():
    """All prompt templates are non-empty strings."""
    from backend.llm.prompts import (
        RULE_INTERPRETER_SYSTEM, RULE_INTERPRETER_USER,
        STRUCTURE_CLASSIFY_SYSTEM, STRUCTURE_CLASSIFY_USER,
        REFERENCE_PARSE_SYSTEM, REFERENCE_PARSE_USER,
        EXPLANATION_SYSTEM, EXPLANATION_USER,
    )
    for name, prompt in [
        ("RULE_INTERPRETER_SYSTEM", RULE_INTERPRETER_SYSTEM),
        ("RULE_INTERPRETER_USER", RULE_INTERPRETER_USER),
        ("STRUCTURE_CLASSIFY_SYSTEM", STRUCTURE_CLASSIFY_SYSTEM),
        ("STRUCTURE_CLASSIFY_USER", STRUCTURE_CLASSIFY_USER),
        ("REFERENCE_PARSE_SYSTEM", REFERENCE_PARSE_SYSTEM),
        ("REFERENCE_PARSE_USER", REFERENCE_PARSE_USER),
        ("EXPLANATION_SYSTEM", EXPLANATION_SYSTEM),
        ("EXPLANATION_USER", EXPLANATION_USER),
    ]:
        assert isinstance(prompt, str) and len(prompt) > 10, f"{name} is empty or too short"


# ─────────────────────────────────────────────────────────────
# 6. AGENTS — Import & Instantiation
# ─────────────────────────────────────────────────────────────


def test_ingest_agent():
    """IngestAgent is importable and has parse method."""
    from backend.agents.ingest import IngestAgent
    agent = IngestAgent()
    assert hasattr(agent, "parse")
    assert hasattr(agent, "_parse_docx")


def test_structure_detector_agent():
    """StructureDetectorAgent is importable and has detect method."""
    from backend.agents.structure_detector import StructureDetectorAgent
    agent = StructureDetectorAgent()
    assert hasattr(agent, "detect")


def test_rule_interpreter_agent():
    """RuleInterpreterAgent loads hardcoded APA 7 correctly."""
    from backend.agents.rule_interpreter import RuleInterpreterAgent
    agent = RuleInterpreterAgent()
    spec = agent.get_style_spec("apa7")
    assert spec.style_name == "APA 7th Edition"
    assert spec.default_typography.font_name == "Times New Roman"
    # Test fallback for unknown style
    spec2 = agent.get_style_spec("unknown_style")
    assert spec2.style_id == "apa7"  # falls back to APA 7


def test_citation_engine_agent():
    """CitationEngineAgent is importable and has process method."""
    from backend.agents.citation_engine import CitationEngineAgent
    agent = CitationEngineAgent()
    assert hasattr(agent, "process")
    assert hasattr(agent, "_extract_citations")
    assert hasattr(agent, "_parse_references")


def test_transformer_agent():
    """TransformerAgent is importable and has transform method."""
    from backend.agents.transformer import TransformerAgent
    agent = TransformerAgent()
    assert hasattr(agent, "transform")


def test_validator_agent():
    """ValidatorAgent is importable and has validate method."""
    from backend.agents.validator import ValidatorAgent
    agent = ValidatorAgent()
    assert hasattr(agent, "validate")
    assert hasattr(agent, "CATEGORY_WEIGHTS")
    weights = agent.CATEGORY_WEIGHTS
    total_weight = sum(weights.values())
    assert abs(total_weight - 1.0) < 0.01, f"Weights should sum to 1.0, got {total_weight}"


def test_orchestrator_agent():
    """Orchestrator instantiates all sub-agents."""
    from backend.agents.orchestrator import Orchestrator
    orch = Orchestrator()
    assert orch.ingest is not None
    assert orch.structure_detector is not None
    assert orch.rule_interpreter is not None
    assert orch.citation_engine is not None
    assert orch.transformer is not None
    assert orch.validator is not None


# ─────────────────────────────────────────────────────────────
# 7. UTILITIES
# ─────────────────────────────────────────────────────────────


def test_apa_title_case():
    """APA title case function handles minor words correctly."""
    from backend.utils.text_utils import apa_title_case
    assert apa_title_case("the effects of social media on learning") == "The Effects of Social Media on Learning"
    assert apa_title_case("a new approach to data analysis") == "A New Approach to Data Analysis"
    # First word always capitalized even if minor
    assert apa_title_case("in the beginning") == "In the Beginning"


def test_clean_text():
    """clean_text removes control chars and extra whitespace."""
    from backend.utils.text_utils import clean_text
    assert clean_text("  hello   world  ") == "hello world"
    assert clean_text("line\x00break") == "linebreak"


def test_word_count():
    from backend.utils.text_utils import word_count
    assert word_count("one two three") == 3
    assert word_count("") == 1 or word_count("") == 0  # handle edge case


def test_unit_conversions():
    """Test EMU/inches/pt conversions."""
    from backend.utils.text_utils import inches_to_emu, emu_to_inches, pt_to_emu, emu_to_pt
    assert inches_to_emu(1.0) == 914400
    assert emu_to_inches(914400) == 1.0
    assert pt_to_emu(12.0) == 152400
    assert emu_to_pt(152400) == 12.0


def test_truncate():
    from backend.utils.text_utils import truncate
    assert truncate("short", 50) == "short"
    assert len(truncate("a" * 100, 50)) == 50


def test_citation_parser_patterns():
    """Test citation detection patterns."""
    from backend.utils.citation_parser import (
        has_citations, PARENTHETICAL_SINGLE, NARRATIVE, HAS_CITATION,
    )
    assert has_citations("(Smith, 2023)")
    assert has_citations("Jones (2021)")
    assert not has_citations("No citations here")

    m = PARENTHETICAL_SINGLE.search("results (Smith, 2023) were")
    assert m is not None
    assert m.group(1) == "Smith"
    assert m.group(2) == "2023"

    m = NARRATIVE.search("Smith (2023) found")
    assert m is not None
    assert m.group(1) == "Smith"
    assert m.group(2) == "2023"


def test_reference_parser():
    """Test reference string parsing."""
    from backend.utils.reference_parser import parse_reference, reference_to_csl_json
    ref = parse_reference("Smith, J. (2023). A test article. Journal of Testing, 10(2), 1-10.")
    assert ref.year == "2023"
    assert len(ref.authors) >= 1
    assert ref.authors[0].family == "Smith"

    csl = reference_to_csl_json(ref, cite_id="ref1")
    assert csl["id"] == "ref1"
    assert "author" in csl


# ─────────────────────────────────────────────────────────────
# 8. FASTAPI APP
# ─────────────────────────────────────────────────────────────


def test_fastapi_app_creates():
    """FastAPI app object is created and has expected routes."""
    from backend.api import app
    routes = [r.path for r in app.routes]
    assert "/api/v1/health" in routes
    assert "/api/v1/styles" in routes
    assert "/api/v1/format" in routes


def test_fastapi_health_endpoint():
    """Health endpoint returns ok."""
    from fastapi.testclient import TestClient
    from backend.api import app
    client = TestClient(app)
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_fastapi_styles_endpoint():
    """Styles endpoint returns available styles."""
    from fastapi.testclient import TestClient
    from backend.api import app
    client = TestClient(app)
    resp = client.get("/api/v1/styles")
    assert resp.status_code == 200
    data = resp.json()
    assert "apa7" in data["available_styles"]


# ─────────────────────────────────────────────────────────────
# 9. STREAMLIT APP — Syntax check (no runtime, just import)
# ─────────────────────────────────────────────────────────────


def test_streamlit_app_syntax():
    """Verify app.py has valid Python syntax by compiling it."""
    app_path = Path(__file__).parent.parent / "app.py"
    assert app_path.exists()
    source = app_path.read_text(encoding="utf-8")
    compile(source, str(app_path), "exec")  # SyntaxError raised if invalid


# ─────────────────────────────────────────────────────────────
# 10. INTEGRATION: Structure Detector on dummy DocIR
# ─────────────────────────────────────────────────────────────


def test_structure_detector_on_dummy_docir():
    """Structure Detector labels elements with heuristic rules."""
    from backend.schemas.docir import (
        DocIR, DocElement, DocMetadata, ElementType, ElementRole,
        ParagraphFormatting,
    )
    from backend.agents.structure_detector import StructureDetectorAgent

    elems = [
        DocElement(id="e1", content="Impact of Social Media", 
                   original_style_name="Title",
                   formatting=ParagraphFormatting(bold=True, alignment="center")),
        DocElement(id="e2", content="Abstract",
                   formatting=ParagraphFormatting(bold=True, alignment="center")),
        DocElement(id="e3", content="This study examines the effects..."),
        DocElement(id="e4", content="Introduction",
                   original_style_name="Heading 1",
                   formatting=ParagraphFormatting(bold=True)),
        DocElement(id="e5", content="Social media has become ubiquitous..."),
        DocElement(id="e6", content="References",
                   formatting=ParagraphFormatting(bold=True, alignment="center")),
        DocElement(id="e7", content="Smith, J. (2023). Article title. Journal, 1(1), 1-10."),
    ]
    docir = DocIR(
        metadata=DocMetadata(source_filename="test.docx", total_paragraphs=7),
        elements=elems,
    )
    agent = StructureDetectorAgent()
    result = agent.detect(docir)

    # Check that at least some roles were assigned
    roles = [e.role for e in result.elements]
    assert ElementRole.TITLE in roles, f"Title not detected. Roles: {roles}"
    assert ElementRole.ABSTRACT_LABEL in roles, f"Abstract label not detected. Roles: {roles}"


# ─────────────────────────────────────────────────────────────
# 11. INTEGRATION: Citation Engine on dummy DocIR
# ─────────────────────────────────────────────────────────────


def test_citation_extraction_on_dummy():
    """Citation engine extracts parenthetical and narrative citations."""
    from backend.schemas.docir import DocIR, DocElement, DocMetadata, ElementRole
    from backend.schemas.style_spec import StyleSpec
    from backend.agents.citation_engine import CitationEngineAgent

    elems = [
        DocElement(id="e1", role=ElementRole.BODY,
                   content="According to Smith (2023), the results were significant."),
        DocElement(id="e2", role=ElementRole.BODY,
                   content="The findings were confirmed (Jones, 2021)."),
        DocElement(id="e3", role=ElementRole.REFERENCE_ENTRY,
                   content="Smith, J. (2023). A test article. Journal of Testing, 10(1), 1-10."),
        DocElement(id="e4", role=ElementRole.REFERENCE_ENTRY,
                   content="Jones, A. (2021). Another article. Testing Review, 5(2), 20-30."),
    ]
    docir = DocIR(
        metadata=DocMetadata(source_filename="test.docx"),
        elements=elems,
    )
    agent = CitationEngineAgent()
    style = StyleSpec()
    result_docir, report = agent.process(docir, style)

    # Check citations were extracted
    all_cites = result_docir.get_all_citations()
    assert len(all_cites) >= 2, f"Expected ≥2 citations, got {len(all_cites)}"

    # Check report
    assert report.total_citations >= 2
    assert report.total_references >= 2


# ─────────────────────────────────────────────────────────────
# DONE — Phase 0 comprehensive validation complete
# ─────────────────────────────────────────────────────────────
