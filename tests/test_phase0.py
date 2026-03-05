"""
Basic tests for the FormatForge AI pipeline.
Run with: pytest tests/ -v
"""

import json
from pathlib import Path

import pytest


def test_docir_schema():
    """Test that DocIR schema can be instantiated and serialised."""
    from backend.schemas.docir import DocIR, DocElement, ElementRole, ElementType

    elem = DocElement(
        id="elem_001",
        type=ElementType.PARAGRAPH,
        role=ElementRole.TITLE,
        content="Test Title",
    )
    docir = DocIR(elements=[elem])
    data = docir.model_dump(mode="json")

    assert data["elements"][0]["role"] == "title"
    assert data["elements"][0]["content"] == "Test Title"


def test_stylespec_load():
    """Test that APA 7 StyleSpec JSON loads and validates."""
    from backend.schemas.style_spec import StyleSpec
    from backend.config import STYLES_DIR

    path = STYLES_DIR / "apa7.json"
    assert path.exists(), f"APA 7 style file not found at {path}"

    with open(path) as f:
        data = json.load(f)

    spec = StyleSpec.model_validate(data)
    assert spec.style_id == "apa7"
    assert spec.default_typography.font_name == "Times New Roman"
    assert spec.default_typography.line_spacing == 2.0
    assert spec.page_layout.margin_top_inches == 1.0
    assert spec.headings.level_1.bold is True
    assert spec.headings.level_1.alignment == "center"


def test_compliance_report_schema():
    """Test that ComplianceReport can be created and scored."""
    from backend.schemas.reports import ComplianceReport, CategoryScore

    report = ComplianceReport(style_name="APA 7th Edition")
    report.categories = [
        CategoryScore(category="page_layout", score=100, weight=0.15),
        CategoryScore(category="typography", score=90, weight=0.15),
        CategoryScore(category="headings", score=80, weight=0.15),
    ]
    report.compute_overall_score()
    assert report.overall_score == pytest.approx(90.0, abs=0.1)


def test_rule_interpreter_hardcoded():
    """Test that RuleInterpreter loads hardcoded APA 7 spec."""
    from backend.agents.rule_interpreter import RuleInterpreterAgent

    agent = RuleInterpreterAgent()
    spec = agent.get_style_spec("apa7")
    assert spec.style_name == "APA 7th Edition"
    assert spec.references.csl_style_name == "apa"


def test_text_utils():
    """Test title case and text utilities."""
    from backend.utils.text_utils import apa_title_case, word_count, clean_text

    assert apa_title_case("the effects of social media on learning") == "The Effects of Social Media on Learning"
    assert word_count("one two three") == 3
    assert clean_text("  hello   world  ") == "hello world"


def test_citation_parser():
    """Test citation regex patterns."""
    from backend.utils.citation_parser import has_citations

    assert has_citations("According to Smith (2023), the results were significant.")
    assert has_citations("The findings were confirmed (Jones, 2021).")
    assert not has_citations("There are no citations here.")
