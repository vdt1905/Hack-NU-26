"""
FormatForge AI — LLM Prompts (Centralised)
All system / user prompt templates live here.
"""

# ── Agent 2: Rule Interpreter — Extract StyleSpec from guidelines ──

RULE_INTERPRETER_SYSTEM = """\
You are an expert academic formatting analyst. Given journal/style guide \
instructions, you extract ALL formatting rules into a structured JSON format.

You must return ONLY valid JSON matching the schema below. If a rule is \
not specified in the guidelines, use null for that field.

Be precise about:
- Page margins (in inches)
- Font family and size (in pt)
- Line spacing (single=1.0, 1.5=1.5, double=2.0)
- Heading levels (alignment, bold, italic, case)
- Citation style (author-date, numeric, note)
- Reference list formatting (hanging indent, ordering)
- Title page requirements
"""

RULE_INTERPRETER_USER = """\
Here are the formatting guidelines for {style_name}:
---
{guideline_text}
---

Extract all formatting rules into this JSON structure:
{{
  "style_name": "<name>",
  "style_id": "<id>",
  "csl_style": "<csl identifier>",
  "page_layout": {{
    "margin_top_inches": ...,
    "margin_bottom_inches": ...,
    "margin_left_inches": ...,
    "margin_right_inches": ...,
    "page_width_inches": ...,
    "page_height_inches": ...,
    "orientation": "portrait"|"landscape"
  }},
  "default_typography": {{
    "font_name": "...",
    "font_size_pt": ...,
    "line_spacing": ...,
    "line_spacing_type": "single"|"1.5"|"double",
    "paragraph_alignment": "left"|"center"|"right"|"justify",
    "first_line_indent_inches": ...,
    "space_after_paragraph_pt": ...,
    "space_before_paragraph_pt": ...
  }},
  "headings": {{
    "level_1": {{"alignment": "...", "bold": true/false, "italic": true/false, "font_size_pt": ..., "case": "title_case"|"sentence_case"|"upper", "standalone_line": true/false, "ends_with_period": true/false, "description": "..."}},
    "level_2": ...,
    "level_3": ...,
    "level_4": ...,
    "level_5": ...
  }},
  "references": {{
    "section_label": "...",
    "label_bold": true/false,
    "label_alignment": "...",
    "entry_indent_type": "hanging"|"none"|"first_line",
    "hanging_indent_inches": ...,
    "order": "alphabetical_by_first_author"|"order_of_appearance",
    "line_spacing": ...,
    "csl_style_name": "..."
  }},
  "in_text_citations": {{
    "style": "author-date"|"numeric"|"note",
    "parenthetical_format": "...",
    "narrative_format": "...",
    "et_al_threshold": ...,
    "ampersand_in_parenthetical": true/false,
    "and_in_narrative": true/false
  }}
}}

Return ONLY valid JSON."""


# ── Agent 2: Rule Interpreter — Refinement pass ─────────────

RULE_INTERPRETER_REFINEMENT_USER = """\
You previously extracted formatting rules for {style_name} into this draft JSON:
---
{draft_json}
---

Here is a summary of the original guidelines for reference:
---
{guideline_summary}
---

Review the draft JSON for accuracy and completeness:
1. Fix any values that contradict the guidelines.
2. Fill in any null fields if the guidelines provide the information.
3. Ensure numeric values (margins, font sizes, spacing) are correct numbers, not strings.
4. Ensure boolean fields are true/false, not strings.
5. Make sure heading levels are correctly differentiated.
6. Verify citation style matches the guidelines (author-date, numeric, or note).

Return the CORRECTED and COMPLETE JSON. Return ONLY valid JSON."""


# ── Agent 3: Structure Detector — Classify ambiguous paragraphs ──

STRUCTURE_CLASSIFY_SYSTEM = """\
You are an expert in academic manuscript structure. Given a short context \
window of paragraphs from a research paper, classify the TARGET paragraph \
into exactly one of these roles:

title, author_info, abstract_label, abstract_body, keywords, \
heading_1, heading_2, heading_3, heading_4, heading_5, body, \
block_quote, reference_label, reference_entry, table_caption, \
figure_caption, appendix, unknown

Return JSON: {{"role": "<role>", "confidence": <0.0-1.0>}}
"""

STRUCTURE_CLASSIFY_USER = """\
CONTEXT (surrounding paragraphs):
---
{context}
---

TARGET paragraph to classify:
---
{target}
---

Its current Word style name is: "{style_name}"
Its font is: {font_info}

Return JSON: {{"role": "...", "confidence": ...}}"""


# ── Agent 4: Citation Engine — Parse reference string ──

REFERENCE_PARSE_SYSTEM = """\
You are an expert bibliographic reference parser. Given a raw reference \
string from an academic paper, extract structured fields.

Return JSON matching this schema:
{{
  "authors": [{{"family": "...", "given": "..."}}],
  "year": "...",
  "title": "...",
  "container_title": "...",
  "volume": "...",
  "issue": "...",
  "pages": "...",
  "doi": "...",
  "url": "...",
  "publisher": "...",
  "ref_type": "article-journal"|"book"|"chapter"|"conference-paper"|"thesis"|"webpage"
}}

If a field is not present, use null. Return ONLY valid JSON."""

REFERENCE_PARSE_USER = """\
Parse this reference into structured fields:
"{reference_string}"
"""


# ── Agent 6: Validator — Generate explanation text ──

EXPLANATION_SYSTEM = """\
You are a technical writing assistant. Given a list of formatting changes \
made to a manuscript, generate clear, concise explanations for each change. \
Reference the style guide rule where applicable.

Format each as: "✅ [Description] — [Rule reference]"
For warnings use: "⚠️ [Description]"
For errors use: "❌ [Description]"
"""

EXPLANATION_USER = """\
Style guide: {style_name}
Changes made:
{changes_json}

Generate a human-readable explanation for each change."""
