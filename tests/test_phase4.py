"""
FormatForge AI — Phase 4 Tests: Style Guide Interpreter Agent
Tests:
  • Hardcoded style loading (apa7, vancouver, ieee)
  • Text cleaning & chunking utilities
  • Deep merge logic
  • LLM-based interpretation (mocked LLM client)
  • Pydantic validation & field-level recovery
  • Fallback to hardcoded on LLM failure
  • URL fetching (mocked)
  • Spec comparison utility
  • Orchestrator integration with guidelines_url
"""

from __future__ import annotations

import json
import logging
import pytest
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch, PropertyMock

# Project imports
from backend.agents.rule_interpreter import (
    RuleInterpreterAgent,
    _clean_text,
    _chunk_text,
    _deep_merge,
    _fetch_url_text,
    _MAX_CHUNK_CHARS,
    _MAX_TOTAL_CHARS,
)
from backend.schemas.style_spec import StyleSpec, PageLayout, DefaultTypography
from backend.config import STYLES_DIR


# ════════════════════════════════════════════════════════════════
# Group 1: Hardcoded StyleSpec loading
# ════════════════════════════════════════════════════════════════


class TestHardcodedLoading:
    """Test loading of all three hardcoded styles."""

    def setup_method(self):
        self.agent = RuleInterpreterAgent()

    def test_load_apa7(self):
        spec = self.agent.get_style_spec("apa7")
        assert spec.style_id == "apa7"
        assert spec.style_name == "APA 7th Edition"
        assert spec.csl_style == "apa"
        assert spec.default_typography.font_name == "Times New Roman"
        assert spec.default_typography.font_size_pt == 12.0
        assert spec.default_typography.line_spacing == 2.0
        assert spec.page_layout.margin_top_inches == 1.0

    def test_load_vancouver(self):
        spec = self.agent.get_style_spec("vancouver")
        assert spec.style_id == "vancouver"
        assert spec.style_name == "Vancouver (ICMJE)"
        assert spec.csl_style == "vancouver"
        assert spec.references.order == "order_of_appearance"
        assert spec.in_text_citations.style == "numeric"
        assert spec.default_typography.paragraph_alignment == "justify"

    def test_load_ieee(self):
        spec = self.agent.get_style_spec("ieee")
        assert spec.style_id == "ieee"
        assert spec.style_name == "IEEE"
        assert spec.csl_style == "ieee"
        assert spec.references.order == "order_of_appearance"
        assert spec.in_text_citations.style == "numeric"
        assert spec.default_typography.font_size_pt == 10.0
        assert spec.page_layout.margin_left_inches == 0.625

    def test_unknown_style_falls_back_to_apa7(self):
        spec = self.agent.get_style_spec("unknown_style_xyz")
        assert spec.style_id == "apa7"
        assert spec.style_name == "APA 7th Edition"

    def test_hardcoded_file_missing_raises(self):
        agent = RuleInterpreterAgent()
        # Temporarily add a bogus entry, then remove it
        agent.STYLE_FILES = dict(agent.STYLE_FILES)  # copy to avoid class mutation
        agent.STYLE_FILES["bogus"] = "nonexistent.json"
        with pytest.raises(FileNotFoundError):
            agent._load_hardcoded("bogus")

    def test_all_hardcoded_files_exist(self):
        for style_id, filename in RuleInterpreterAgent.STYLE_FILES.items():
            path = STYLES_DIR / filename
            assert path.exists(), f"Missing style file: {path}"

    def test_all_hardcoded_files_valid_pydantic(self):
        agent = RuleInterpreterAgent()
        for style_id in agent.STYLE_FILES:
            spec = agent._load_hardcoded(style_id)
            assert isinstance(spec, StyleSpec)


# ════════════════════════════════════════════════════════════════
# Group 2: Utility functions
# ════════════════════════════════════════════════════════════════


class TestCleanText:
    def test_collapses_blank_lines(self):
        text = "Hello\n\n\n\n\nWorld"
        assert _clean_text(text) == "Hello\n\nWorld"

    def test_removes_decorations(self):
        text = "═══════════════\nSection\n─────────"
        result = _clean_text(text)
        assert "═" not in result
        assert "─" not in result
        assert "Section" in result

    def test_strips_whitespace(self):
        text = "   hello   "
        assert _clean_text(text) == "hello"

    def test_empty_string(self):
        assert _clean_text("") == ""
        assert _clean_text("   ") == ""


class TestChunkText:
    def test_short_text_single_chunk(self):
        text = "Short text."
        chunks = _chunk_text(text)
        assert len(chunks) == 1
        assert chunks[0] == "Short text."

    def test_long_text_multiple_chunks(self):
        # Generate text longer than _MAX_CHUNK_CHARS
        para = "This is a paragraph of text. " * 50  # ~1450 chars each
        text = "\n\n".join([para] * 10)  # ~14500 chars
        chunks = _chunk_text(text, max_chars=3000)
        assert len(chunks) > 1
        for c in chunks:
            assert len(c) <= 3000 + 200  # small tolerance for paragraph boundaries

    def test_respects_max_total(self):
        huge = "x" * (_MAX_TOTAL_CHARS + 5000)
        chunks = _chunk_text(huge)
        total = sum(len(c) for c in chunks)
        assert total <= _MAX_TOTAL_CHARS + 100

    def test_empty_text(self):
        chunks = _chunk_text("")
        assert chunks == [""] or chunks == []


class TestDeepMerge:
    def test_flat_merge(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self):
        base = {"a": {"x": 1, "y": 2}, "b": 10}
        override = {"a": {"y": 99, "z": 3}}
        result = _deep_merge(base, override)
        assert result == {"a": {"x": 1, "y": 99, "z": 3}, "b": 10}

    def test_none_values_not_overwritten(self):
        base = {"a": 1, "b": 2}
        override = {"a": None, "b": 3}
        result = _deep_merge(base, override)
        assert result["a"] == 1  # None doesn't override
        assert result["b"] == 3

    def test_empty_override(self):
        base = {"a": 1}
        result = _deep_merge(base, {})
        assert result == {"a": 1}

    def test_deep_three_levels(self):
        base = {"a": {"b": {"c": 1, "d": 2}}}
        override = {"a": {"b": {"d": 99}}}
        result = _deep_merge(base, override)
        assert result["a"]["b"]["c"] == 1
        assert result["a"]["b"]["d"] == 99


# ════════════════════════════════════════════════════════════════
# Group 3: LLM-based interpretation (mocked)
# ════════════════════════════════════════════════════════════════

# Sample APA 7 guideline text for testing
APA7_GUIDELINE_TEXT = """
APA 7th Edition Formatting Guidelines

Page Setup:
- Use 1-inch margins on all sides
- Standard letter size paper (8.5 x 11 inches)
- Portrait orientation

Typography:
- Use 12-point Times New Roman font throughout
- Double-space all text
- Left-align body text (do not justify)
- Indent the first line of each paragraph 0.5 inches

Title Page:
- Title in bold, centered, 3-4 lines below the top margin
- Author name centered below title (not bold)
- Institutional affiliation centered below author name

Headings (5 levels):
- Level 1: Centered, Bold, Title Case
- Level 2: Flush Left, Bold, Title Case
- Level 3: Flush Left, Bold Italic, Title Case
- Level 4: Indented 0.5 in., Bold, Title Case, Ending With a Period. Text begins on same line.
- Level 5: Indented 0.5 in., Bold Italic, Title Case, Ending With a Period. Text on same line.

Abstract:
- Label "Abstract" centered, bold at top of page
- Single paragraph, no indent, max 250 words
- Keywords line: indented, "Keywords:" in italic, followed by keywords

References:
- "References" label centered and bold
- Double-spaced entries with 0.5 inch hanging indent
- Alphabetical order by first author's last name
- Use APA citation style

In-Text Citations:
- Author-date format: (Smith, 2023) or Smith (2023)
- Use & in parenthetical citations
- Use "and" in narrative citations
- et al. for 3+ authors
"""

VANCOUVER_GUIDELINE_TEXT = """
Vancouver Citation Style Guidelines (ICMJE)

General Formatting:
- Use 12-point Times New Roman or Arial
- Double-space throughout the manuscript
- Justify text on both margins
- No first-line paragraph indent

References:
- Number references in order of first appearance in text
- Use arabic numerals in parentheses (1) or superscript
- List all authors; if more than 6, list first 6 followed by et al.
- References label flush left, bold
- No hanging indent

In-Text Citations:
- Use numeric citations (superscript or in parentheses)
- Numbers correspond to reference list entries

Headings:
- Level 1: Flush left, bold, uppercase
- Level 2: Flush left, bold, title case
- Level 3: Flush left, italic, sentence case

Abstract:
- Label flush left, bold
- Structured abstract preferred (Background, Methods, Results, Conclusion)
- Max 250 words
"""

IEEE_GUIDELINE_TEXT = """
IEEE Conference Paper Formatting

Page Setup:
- US Letter paper (8.5 x 11 inches)
- Top margin: 0.75 inches
- Bottom margin: 1 inch
- Left and right margins: 0.625 inches

Typography:
- 10-point Times New Roman
- Single-spaced body text
- Justified alignment
- 0.25 inch first-line indent

Title:
- 24-point, centered, not bold
- Author name 11-point, centered

Headings:
- Level 1 (Primary): Centered, small caps, uppercase, Roman numeral prefix
- Level 2: Flush left, italic, title case, letter prefix
- Level 3: Indented, italic, numbered, period, text follows on same line

References:
- Numbered in order of appearance using [1], [2] style
- Label centered, not bold
- No hanging indent
- Single-spaced

In-Text Citations:
- Square bracket numbers: [1], [2], [1]-[3]
- Do not use author names unless necessary

Abstract:
- Label centered, bold
- Max 200 words
- Index Terms (italic) after abstract
"""


def _make_mock_llm_response(style_data: dict) -> dict:
    """Create a mock LLM JSON response for a given style."""
    return style_data


class TestLLMInterpretation:
    """Test LLM-based rule extraction with a mocked LLM client."""

    def setup_method(self):
        self.agent = RuleInterpreterAgent()

    def _mock_client(self, return_data: dict):
        """Create a mock LLM client that returns the given data."""
        mock = MagicMock()
        mock.chat_json.return_value = return_data
        return mock

    @patch("backend.llm.client.get_llm_client")
    def test_llm_extracts_apa7_from_text(self, mock_get_client):
        """LLM returns valid APA 7 data → should produce correct StyleSpec."""
        apa7_data = {
            "style_name": "APA 7th Edition",
            "style_id": "apa7",
            "csl_style": "apa",
            "page_layout": {"margin_top_inches": 1.0, "margin_left_inches": 1.0},
            "default_typography": {
                "font_name": "Times New Roman",
                "font_size_pt": 12.0,
                "line_spacing": 2.0,
                "paragraph_alignment": "left",
            },
            "references": {
                "order": "alphabetical_by_first_author",
                "entry_indent_type": "hanging",
                "hanging_indent_inches": 0.5,
            },
            "in_text_citations": {
                "style": "author-date",
                "et_al_threshold": 3,
            },
        }
        mock_get_client.return_value = self._mock_client(apa7_data)

        spec = self.agent.get_style_spec(
            style_id="apa7",
            guidelines_text=APA7_GUIDELINE_TEXT,
        )

        assert isinstance(spec, StyleSpec)
        assert spec.style_name == "APA 7th Edition"
        assert spec.default_typography.font_name == "Times New Roman"
        assert spec.default_typography.font_size_pt == 12.0
        assert spec.references.order == "alphabetical_by_first_author"
        assert spec.in_text_citations.style == "author-date"

    @patch("backend.llm.client.get_llm_client")
    def test_llm_extracts_vancouver_from_text(self, mock_get_client):
        """LLM returns valid Vancouver data → should produce correct StyleSpec."""
        vancouver_data = {
            "style_name": "Vancouver",
            "style_id": "vancouver",
            "csl_style": "vancouver",
            "default_typography": {
                "font_name": "Times New Roman",
                "font_size_pt": 12.0,
                "line_spacing": 2.0,
                "paragraph_alignment": "justify",
                "first_line_indent_inches": 0.0,
            },
            "references": {
                "order": "order_of_appearance",
                "entry_indent_type": "none",
                "label_alignment": "left",
            },
            "in_text_citations": {
                "style": "numeric",
                "parenthetical_format": "(1)",
            },
        }
        mock_get_client.return_value = self._mock_client(vancouver_data)

        spec = self.agent.get_style_spec(
            style_id="vancouver",
            guidelines_text=VANCOUVER_GUIDELINE_TEXT,
        )

        assert spec.style_name == "Vancouver"
        assert spec.references.order == "order_of_appearance"
        assert spec.in_text_citations.style == "numeric"
        assert spec.default_typography.paragraph_alignment == "justify"

    @patch("backend.llm.client.get_llm_client")
    def test_llm_extracts_ieee_from_text(self, mock_get_client):
        """LLM returns valid IEEE data → should produce correct StyleSpec."""
        ieee_data = {
            "style_name": "IEEE",
            "style_id": "ieee",
            "csl_style": "ieee",
            "page_layout": {
                "margin_top_inches": 0.75,
                "margin_left_inches": 0.625,
                "margin_right_inches": 0.625,
            },
            "default_typography": {
                "font_name": "Times New Roman",
                "font_size_pt": 10.0,
                "line_spacing": 1.0,
                "paragraph_alignment": "justify",
            },
            "references": {
                "order": "order_of_appearance",
                "entry_indent_type": "none",
            },
            "in_text_citations": {
                "style": "numeric",
                "parenthetical_format": "[1]",
            },
        }
        mock_get_client.return_value = self._mock_client(ieee_data)

        spec = self.agent.get_style_spec(
            style_id="ieee",
            guidelines_text=IEEE_GUIDELINE_TEXT,
        )

        assert spec.style_name == "IEEE"
        assert spec.default_typography.font_size_pt == 10.0
        assert spec.page_layout.margin_top_inches == 0.75
        assert spec.in_text_citations.parenthetical_format == "[1]"

    @patch("backend.llm.client.get_llm_client")
    def test_llm_failure_falls_back_to_hardcoded(self, mock_get_client):
        """If LLM raises an exception, should fallback to hardcoded."""
        mock_client = MagicMock()
        mock_client.chat_json.side_effect = RuntimeError("API key invalid")
        mock_get_client.return_value = mock_client

        spec = self.agent.get_style_spec(
            style_id="apa7",
            guidelines_text="Some guideline text",
        )

        # Should fallback to hardcoded APA 7
        assert isinstance(spec, StyleSpec)
        assert spec.style_id == "apa7"

    @patch("backend.llm.client.get_llm_client")
    def test_llm_returns_partial_data_merged_with_defaults(self, mock_get_client):
        """LLM returns only some fields → rest should come from defaults."""
        partial_data = {
            "style_name": "Custom Journal",
            "default_typography": {
                "font_name": "Arial",
                "font_size_pt": 11.0,
            },
        }
        mock_get_client.return_value = self._mock_client(partial_data)

        spec = self.agent.get_style_spec(
            style_id="apa7",
            guidelines_text="Some guidelines mentioning Arial 11pt",
        )

        assert spec.style_name == "Custom Journal"
        assert spec.default_typography.font_name == "Arial"
        assert spec.default_typography.font_size_pt == 11.0
        # Defaults should fill in the rest
        assert spec.page_layout.margin_top_inches == 1.0  # default
        assert spec.headings.level_1.bold is True  # default

    @patch("backend.llm.client.get_llm_client")
    def test_llm_returns_invalid_json_falls_back(self, mock_get_client):
        """If LLM returns non-dict, should fallback."""
        mock_client = MagicMock()
        mock_client.chat_json.side_effect = ValueError("Invalid JSON")
        mock_get_client.return_value = mock_client

        spec = self.agent.get_style_spec(
            style_id="vancouver",
            guidelines_text="Bad guidelines",
        )

        # Falls back to hardcoded
        assert isinstance(spec, StyleSpec)

    @patch("backend.llm.client.get_llm_client")
    def test_multi_chunk_processing(self, mock_get_client):
        """Long text should be split into chunks, each processed separately."""
        # Key: the mock is called twice (once per chunk) + once for refinement
        call_count = {"n": 0}

        def side_effect(**kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return {"style_name": "Chunked Style", "page_layout": {"margin_top_inches": 1.5}}
            elif call_count["n"] == 2:
                return {"default_typography": {"font_name": "Courier New"}}
            else:
                return {}  # refinement pass

        mock_client = MagicMock()
        mock_client.chat_json.side_effect = side_effect
        mock_get_client.return_value = mock_client

        # Create text long enough to require 2+ chunks
        long_text = ("Guidelines paragraph " * 200 + "\n\n") * 5
        spec = self.agent.get_style_spec(
            style_id="apa7",
            guidelines_text=long_text,
        )

        assert isinstance(spec, StyleSpec)
        assert mock_client.chat_json.call_count >= 2  # at least 2 chunks

    @patch("backend.llm.client.get_llm_client")
    def test_refinement_pass_runs(self, mock_get_client):
        """After initial extraction, a refinement pass should run."""
        call_count = {"n": 0}

        def side_effect(**kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return {"style_name": "Initial"}
            elif call_count["n"] == 2:
                # Refinement pass corrects the name
                return {"style_name": "Refined Style Name"}
            return {}

        mock_client = MagicMock()
        mock_client.chat_json.side_effect = side_effect
        mock_get_client.return_value = mock_client

        spec = self.agent.get_style_spec(
            style_id="apa7",
            guidelines_text="Short guidelines text.",
        )

        assert spec.style_name == "Refined Style Name"
        assert mock_client.chat_json.call_count == 2

    @patch("backend.llm.client.get_llm_client")
    def test_refinement_failure_uses_first_pass(self, mock_get_client):
        """If refinement fails, first-pass result should still work."""
        call_count = {"n": 0}

        def side_effect(**kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return {"style_name": "First Pass Only"}
            raise RuntimeError("Refinement API error")

        mock_client = MagicMock()
        mock_client.chat_json.side_effect = side_effect
        mock_get_client.return_value = mock_client

        spec = self.agent.get_style_spec(
            style_id="apa7",
            guidelines_text="Short guidelines.",
        )

        assert spec.style_name == "First Pass Only"


# ════════════════════════════════════════════════════════════════
# Group 4: Validation & Recovery
# ════════════════════════════════════════════════════════════════


class TestValidationAndRecovery:

    def setup_method(self):
        self.agent = RuleInterpreterAgent()

    def test_validate_and_merge_good_data(self):
        data = {
            "style_name": "Test Style",
            "style_id": "test",
            "default_typography": {"font_name": "Verdana"},
        }
        spec = self.agent._validate_and_merge(data, "apa7")
        assert spec.style_name == "Test Style"
        assert spec.default_typography.font_name == "Verdana"
        # defaults filled
        assert spec.page_layout.margin_top_inches == 1.0

    def test_validate_and_merge_completely_empty(self):
        """Empty dict → all defaults."""
        spec = self.agent._validate_and_merge({}, "apa7")
        assert spec.style_name == "APA 7th Edition"  # default
        assert isinstance(spec, StyleSpec)

    def test_recover_spec_with_one_bad_section(self):
        defaults = json.loads(StyleSpec().model_dump_json())
        bad_data = dict(defaults)
        bad_data["page_layout"] = "not a dict"  # invalid
        bad_data["style_name"] = "Recovered"

        spec = self.agent._recover_spec(bad_data, defaults, "apa7")
        assert spec.style_name == "Recovered"
        # page_layout should be default since it was invalid
        assert spec.page_layout.margin_top_inches == 1.0

    def test_recover_spec_all_bad_sections(self):
        """If every section is bad, should still return a valid spec."""
        defaults = json.loads(StyleSpec().model_dump_json())
        bad_data = {k: "invalid" for k in defaults}
        spec = self.agent._recover_spec(bad_data, defaults, "apa7")
        assert isinstance(spec, StyleSpec)


# ════════════════════════════════════════════════════════════════
# Group 5: URL Fetching (mocked)
# ════════════════════════════════════════════════════════════════


class TestURLFetching:

    def setup_method(self):
        self.agent = RuleInterpreterAgent()

    @patch("backend.agents.rule_interpreter._fetch_url_text")
    @patch("backend.llm.client.get_llm_client")
    def test_guidelines_url_triggers_fetch_and_llm(self, mock_get_client, mock_fetch):
        mock_fetch.return_value = APA7_GUIDELINE_TEXT

        mock_client = MagicMock()
        mock_client.chat_json.return_value = {"style_name": "From URL"}
        mock_get_client.return_value = mock_client

        spec = self.agent.get_style_spec(
            style_id="apa7",
            guidelines_url="https://example.com/apa7-guide",
        )

        mock_fetch.assert_called_once_with("https://example.com/apa7-guide")
        assert spec.style_name == "From URL"

    @patch("backend.agents.rule_interpreter._fetch_url_text")
    def test_url_fetch_failure_falls_back_to_hardcoded(self, mock_fetch):
        mock_fetch.side_effect = ConnectionError("Network error")

        spec = self.agent.get_style_spec(
            style_id="apa7",
            guidelines_url="https://unreachable.example.com",
        )

        assert spec.style_id == "apa7"  # fallback

    @patch("backend.agents.rule_interpreter._fetch_url_text")
    def test_url_fetch_empty_content_falls_back(self, mock_fetch):
        mock_fetch.return_value = "short"  # < 50 chars

        spec = self.agent.get_style_spec(
            style_id="ieee",
            guidelines_url="https://example.com/empty",
        )

        assert spec.style_id == "ieee"  # fallback

    def test_guidelines_text_takes_priority_over_url(self):
        """When both text and url are given, text should be used."""
        with patch.object(self.agent, "_interpret_with_llm") as mock_llm:
            mock_llm.return_value = StyleSpec(style_name="From Text")
            spec = self.agent.get_style_spec(
                style_id="apa7",
                guidelines_text="Some text",
                guidelines_url="https://example.com",
            )
            mock_llm.assert_called_once()
            assert spec.style_name == "From Text"

    def test_no_text_no_url_loads_hardcoded(self):
        spec = self.agent.get_style_spec(style_id="apa7")
        assert spec.style_id == "apa7"
        assert spec.style_name == "APA 7th Edition"

    def test_empty_text_loads_hardcoded(self):
        spec = self.agent.get_style_spec(style_id="apa7", guidelines_text="   ")
        assert spec.style_id == "apa7"

    def test_empty_url_loads_hardcoded(self):
        spec = self.agent.get_style_spec(style_id="ieee", guidelines_url="")
        assert spec.style_id == "ieee"


# ════════════════════════════════════════════════════════════════
# Group 6: Spec Comparison
# ════════════════════════════════════════════════════════════════


class TestSpecComparison:

    def setup_method(self):
        self.agent = RuleInterpreterAgent()

    def test_identical_specs_no_diffs(self):
        spec = self.agent.get_style_spec("apa7")
        diffs = self.agent.compare_specs(spec, spec)
        assert diffs == {}

    def test_different_specs_show_diffs(self):
        apa = self.agent.get_style_spec("apa7")
        ieee = self.agent.get_style_spec("ieee")
        diffs = self.agent.compare_specs(apa, ieee)
        assert len(diffs) > 0
        assert "style_name" in diffs
        assert "style_id" in diffs

    def test_apa_vs_vancouver_key_differences(self):
        apa = self.agent.get_style_spec("apa7")
        van = self.agent.get_style_spec("vancouver")
        diffs = self.agent.compare_specs(apa, van)

        # These should definitely differ
        assert "references.order" in diffs
        assert diffs["references.order"]["a"] == "alphabetical_by_first_author"
        assert diffs["references.order"]["b"] == "order_of_appearance"

        assert "in_text_citations.style" in diffs
        assert diffs["in_text_citations.style"]["a"] == "author-date"
        assert diffs["in_text_citations.style"]["b"] == "numeric"

    def test_comparison_includes_nested_fields(self):
        apa = self.agent.get_style_spec("apa7")
        ieee = self.agent.get_style_spec("ieee")
        diffs = self.agent.compare_specs(apa, ieee)

        # Font size should differ
        assert "default_typography.font_size_pt" in diffs
        assert diffs["default_typography.font_size_pt"]["a"] == 12.0
        assert diffs["default_typography.font_size_pt"]["b"] == 10.0


# ════════════════════════════════════════════════════════════════
# Group 7: Vancouver & IEEE hardcoded spec correctness
# ════════════════════════════════════════════════════════════════


class TestStyleSpecCorrectness:
    """Verify that hardcoded style files contain correct & expected values."""

    def setup_method(self):
        self.agent = RuleInterpreterAgent()

    # Vancouver checks
    def test_vancouver_numeric_citations(self):
        spec = self.agent.get_style_spec("vancouver")
        assert spec.in_text_citations.style == "numeric"

    def test_vancouver_order_of_appearance(self):
        spec = self.agent.get_style_spec("vancouver")
        assert spec.references.order == "order_of_appearance"

    def test_vancouver_no_hanging_indent(self):
        spec = self.agent.get_style_spec("vancouver")
        assert spec.references.entry_indent_type == "none"

    def test_vancouver_justified_text(self):
        spec = self.agent.get_style_spec("vancouver")
        assert spec.default_typography.paragraph_alignment == "justify"

    def test_vancouver_abstract_label_left(self):
        spec = self.agent.get_style_spec("vancouver")
        assert spec.abstract.label_alignment == "left"

    # IEEE checks
    def test_ieee_10pt_font(self):
        spec = self.agent.get_style_spec("ieee")
        assert spec.default_typography.font_size_pt == 10.0

    def test_ieee_single_spacing(self):
        spec = self.agent.get_style_spec("ieee")
        assert spec.default_typography.line_spacing == 1.0

    def test_ieee_narrow_margins(self):
        spec = self.agent.get_style_spec("ieee")
        assert spec.page_layout.margin_left_inches == 0.625
        assert spec.page_layout.margin_right_inches == 0.625
        assert spec.page_layout.margin_top_inches == 0.75

    def test_ieee_no_title_page_required(self):
        spec = self.agent.get_style_spec("ieee")
        assert spec.title_page.required is False

    def test_ieee_bracket_citations(self):
        spec = self.agent.get_style_spec("ieee")
        assert spec.in_text_citations.parenthetical_format == "[1]"

    def test_ieee_index_terms(self):
        spec = self.agent.get_style_spec("ieee")
        assert "Index" in spec.abstract.keywords_label

    def test_ieee_reference_single_spacing(self):
        spec = self.agent.get_style_spec("ieee")
        assert spec.references.line_spacing == 1.0

    # APA 7 vs defaults sanity
    def test_apa7_first_line_indent(self):
        spec = self.agent.get_style_spec("apa7")
        assert spec.default_typography.first_line_indent_inches == 0.5

    def test_apa7_hanging_indent(self):
        spec = self.agent.get_style_spec("apa7")
        assert spec.references.hanging_indent_inches == 0.5
        assert spec.references.entry_indent_type == "hanging"

    def test_apa7_heading_levels_correct(self):
        spec = self.agent.get_style_spec("apa7")
        h = spec.headings
        assert h.level_1.alignment == "center"
        assert h.level_1.bold is True
        assert h.level_2.alignment == "left"
        assert h.level_3.italic is True
        assert h.level_4.standalone_line is False
        assert h.level_5.ends_with_period is True


# ════════════════════════════════════════════════════════════════
# Group 8: Orchestrator integration
# ════════════════════════════════════════════════════════════════


class TestOrchestratorIntegration:
    """Verify that the orchestrator passes guidelines_url to rule_interpreter."""

    def test_orchestrator_accepts_guidelines_url_param(self):
        """The run() method should accept guidelines_url."""
        import inspect
        from backend.agents.orchestrator import Orchestrator

        sig = inspect.signature(Orchestrator.run)
        assert "guidelines_url" in sig.parameters

    def test_orchestrator_run_signature_has_all_params(self):
        """Verify all expected parameters exist."""
        import inspect
        from backend.agents.orchestrator import Orchestrator

        sig = inspect.signature(Orchestrator.run)
        params = list(sig.parameters.keys())
        assert "input_path" in params
        assert "style_id" in params
        assert "guidelines_text" in params
        assert "guidelines_url" in params
        assert "output_dir" in params


# ════════════════════════════════════════════════════════════════
# Group 9: Edge cases & regression
# ════════════════════════════════════════════════════════════════


class TestEdgeCases:

    def setup_method(self):
        self.agent = RuleInterpreterAgent()

    @patch("backend.llm.client.get_llm_client")
    def test_llm_client_init_failure_falls_back(self, mock_get_client):
        """If get_llm_client raises, should fallback to hardcoded."""
        mock_get_client.side_effect = RuntimeError("No API key")

        spec = self.agent.get_style_spec(
            style_id="apa7",
            guidelines_text="Some text",
        )
        assert spec.style_id == "apa7"

    @patch("backend.llm.client.get_llm_client")
    def test_guidelines_with_unicode(self, mock_get_client):
        """Guidelines with unicode characters should not crash."""
        mock_client = MagicMock()
        mock_client.chat_json.return_value = {"style_name": "Unicode Style 日本語"}
        mock_get_client.return_value = mock_client

        spec = self.agent.get_style_spec(
            style_id="apa7",
            guidelines_text="Guidelines with émojis 🎉 and ñ characters",
        )
        assert spec.style_name == "Unicode Style 日本語"

    @patch("backend.llm.client.get_llm_client")
    def test_very_short_guidelines(self, mock_get_client):
        """Single-sentence guidelines should still be processed."""
        mock_client = MagicMock()
        mock_client.chat_json.return_value = {"style_name": "Brief"}
        mock_get_client.return_value = mock_client

        spec = self.agent.get_style_spec(
            style_id="apa7",
            guidelines_text="Use 12pt Times New Roman, double-spaced.",
        )
        assert spec.style_name == "Brief"

    def test_style_spec_default_construction(self):
        """StyleSpec() with no args should produce valid APA 7 defaults."""
        spec = StyleSpec()
        assert spec.style_name == "APA 7th Edition"
        assert spec.default_typography.font_name == "Times New Roman"
        assert spec.headings.level_1.bold is True

    def test_all_three_styles_produce_distinct_specs(self):
        """apa7, vancouver, ieee should all be meaningfully different."""
        apa = self.agent.get_style_spec("apa7")
        van = self.agent.get_style_spec("vancouver")
        ieee = self.agent.get_style_spec("ieee")

        # All different names
        names = {apa.style_name, van.style_name, ieee.style_name}
        assert len(names) == 3

        # All different citation styles
        cite_combos = {
            (apa.in_text_citations.style, apa.references.order),
            (van.in_text_citations.style, van.references.order),
            (ieee.in_text_citations.style, ieee.references.order),
        }
        # APA is author-date/alphabetical, Vancouver and IEEE are numeric/order_of_appearance
        # So at least 2 distinct combos
        assert len(cite_combos) >= 2


# ════════════════════════════════════════════════════════════════
# Group 10: Prompt template checks
# ════════════════════════════════════════════════════════════════


class TestPromptTemplates:
    """Verify prompt templates have required placeholders."""

    def test_interpreter_user_prompt_has_placeholders(self):
        from backend.llm.prompts import RULE_INTERPRETER_USER
        assert "{style_name}" in RULE_INTERPRETER_USER
        assert "{guideline_text}" in RULE_INTERPRETER_USER

    def test_interpreter_system_prompt_not_empty(self):
        from backend.llm.prompts import RULE_INTERPRETER_SYSTEM
        assert len(RULE_INTERPRETER_SYSTEM) > 100

    def test_refinement_prompt_has_placeholders(self):
        from backend.llm.prompts import RULE_INTERPRETER_REFINEMENT_USER
        assert "{style_name}" in RULE_INTERPRETER_REFINEMENT_USER
        assert "{draft_json}" in RULE_INTERPRETER_REFINEMENT_USER
        assert "{guideline_summary}" in RULE_INTERPRETER_REFINEMENT_USER

    def test_user_prompt_formats_correctly(self):
        from backend.llm.prompts import RULE_INTERPRETER_USER
        formatted = RULE_INTERPRETER_USER.format(
            style_name="APA 7",
            guideline_text="Use 1 inch margins.",
        )
        assert "APA 7" in formatted
        assert "1 inch margins" in formatted

    def test_refinement_prompt_formats_correctly(self):
        from backend.llm.prompts import RULE_INTERPRETER_REFINEMENT_USER
        formatted = RULE_INTERPRETER_REFINEMENT_USER.format(
            style_name="Test",
            draft_json='{"style_name": "Test"}',
            guideline_summary="Use double spacing.",
        )
        assert "Test" in formatted
        assert "double spacing" in formatted
