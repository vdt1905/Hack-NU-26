# FormatForge AI — MASTER HACKATHON PLAN
## "Fix My Format, Agent Paperpal" | HackaMined 2026

---

# TABLE OF CONTENTS
1. [Problem Statement Deep Analysis](#1-problem-statement-deep-analysis)
2. [Why This Problem Is Hard (And What Judges Want)](#2-why-this-problem-is-hard)
3. [Our Winning Strategy — The Core Insight](#3-our-winning-strategy)
4. [System Architecture — Multi-Agent Pipeline](#4-system-architecture)
5. [Tech Stack — Every Single Tool & Why](#5-tech-stack)
6. [Internal Data Schemas (DocIR + StyleSpec)](#6-internal-data-schemas)
7. [Phase-by-Phase Implementation Plan (40 Hours)](#7-phase-by-phase-plan)
8. [APA 7th Edition — Complete Rule Specification](#8-apa-7th-edition-rules)
9. [Citation Consistency Engine — Deep Dive](#9-citation-engine)
10. [Compliance Scoring & Explainability](#10-compliance-scoring)
11. [Frontend / Demo UI](#11-frontend-ui)
12. [API Design](#12-api-design)
13. [Folder Structure](#13-folder-structure)
14. [Risk Mitigation & Failure Modes](#14-risk-mitigation)
15. [Presentation & Mentor Strategy](#15-presentation-strategy)
16. [Scoring Rubric Map — What Wins Points](#16-scoring-rubric-map)

---

# 1. PROBLEM STATEMENT DEEP ANALYSIS

## What They Actually Want (Plain English)

The challenge is: **Build an AI system that takes a messy research manuscript (DOCX/PDF) and automatically reformats it to perfectly match a specific journal's style guide (starting with APA 7th edition).**

### The Input
- A raw research manuscript (DOCX, PDF, or plain text)
- A style guide / journal formatting rules (start with APA 7th edition, bonus: support more)

### The Output
- A **publication-ready .docx file** that opens natively in Microsoft Word
- A **compliance report** showing what was changed and why
- The original **content must be 100% preserved** — only formatting changes

### What "Formatting" Actually Means (The Full Scope)
| Category | What Must Be Formatted | APA 7 Example |
|----------|----------------------|---------------|
| **Page Layout** | Margins, page size, orientation | 1" margins all sides, Letter size |
| **Typography** | Font family, size, line spacing | Times New Roman 12pt, double-spaced |
| **Title Page** | Title, author, affiliation, course, date | Centered, bold title, double-spaced author info |
| **Abstract** | Label, format, word limit | "Abstract" centered bold, single paragraph, 150-250 words |
| **Headings** | 5 levels of heading hierarchy | Level 1: Centered Bold; Level 2: Flush Left Bold; etc. |
| **Body Text** | Paragraph indentation, alignment | 0.5" first-line indent, left-aligned, double-spaced |
| **In-Text Citations** | Parenthetical & narrative format | (Author, Year) or Author (Year) |
| **Reference List** | Ordering, hanging indent, format | Alphabetical, 0.5" hanging indent, specific punctuation |
| **Tables** | Numbering, title, notes, lines | Table 1 (bold), title in italics, horizontal rules only |
| **Figures** | Numbering, title, notes | Figure 1 (bold italics), title in italics below number |
| **Running Head** | Page header with shortened title | Shortened title flush left, page number flush right |
| **Page Numbers** | Position and starting page | Top right, starting from title page |

### What They're Really Evaluating (Reading Between The Lines)

From the rubric:
- **How accurately style guide is followed and document is formatted (30%)** — This is KING. Must get APA 7 right.
- **Working demo (30%)** — Must have a functional end-to-end system. Upload → Process → Download.
- **Presentation and Engagement with Mentors (20%)** — Story, integration ideas, using their products.
- **Tech Scalability (20%)** — Architecture that can extend to other journals/styles.

**CRITICAL QUOTE from the problem statement:**
> "Even if final product is not great, intermediate steps identification and partial automation is also evaluated with equal weightage to running end product."

This means: **Show your work.** Even if the final DOCX isn't perfect, if you can show:
1. "We detected the structure correctly" ✓
2. "We extracted these rules from the guidelines" ✓  
3. "We applied headings formatting" ✓
4. "Citations were partially matched" ✓

...you still win major points. The system's **interpretability and partial results** are valued equally.

---

# 2. WHY THIS PROBLEM IS HARD (And What Judges Want)

## The 6 Hard Problems (From Their Slides)

| # | Hard Problem | Our Solution |
|---|-------------|-------------|
| 1 | **No Rule Database** — Journal guidelines live in PDFs and prose | LLM extracts rules into structured JSON (StyleSpec) |
| 2 | **Global Consistency** — Change one citation, all refs must update | Citation Consistency Engine with bidirectional validation |
| 3 | **Multimodal Documents** — Text + figures + tables + equations | python-docx preserves embedded objects; we format around them |
| 4 | **No Training Ground Truth** — Can't fine-tune on pairs | Rule interpreter approach, not ML-based formatting |
| 5 | **Privacy Wall** — Researchers won't upload to public LLMs | Architecture allows local LLM swap; deterministic core |
| 6 | **Output Must Be Publication-Ready** — Not suggestions, actual .docx | python-docx generates real, Word-compatible output |

## Key Insight The Judges Want

The slides say: *"Think: agentic rule interpreter, not a template applier."*

This means:
- **DON'T** just hardcode APA rules as if/else statements (too rigid, not scalable)
- **DO** build a system that READS rules from a guideline document/URL and INTERPRETS them
- **DON'T** have the LLM rewrite the entire document (will destroy content)
- **DO** use LLM for understanding/classification, deterministic code for formatting

---

# 3. OUR WINNING STRATEGY — THE CORE INSIGHT

## The Hybrid Architecture: LLM Brain + Deterministic Hands

```
┌─────────────────────────────────────────────────────┐
│                   LLM DOES:                         │
│  • Classify document structure (what is this para?) │
│  • Extract rules from guideline text → JSON         │
│  • Resolve ambiguous headings                       │
│  • Generate explanations for changes                │
│  (Small, focused calls — never sees whole doc)      │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│              DETERMINISTIC CODE DOES:               │
│  • Parse DOCX structure (python-docx)               │
│  • Apply formatting rules (fonts, margins, spacing) │
│  • Reformat citations (citeproc-py + CSL)           │
│  • Validate citation↔reference consistency          │
│  • Generate compliance scores                       │
│  • Produce final .docx output                       │
│  (100% predictable, no hallucination risk)          │
└─────────────────────────────────────────────────────┘
```

**Why this wins:**
1. LLM handles the "intelligent" parts (understanding natural language guidelines, disambiguating structure)
2. Deterministic code handles the "precise" parts (formatting, citation rendering, validation)
3. LLM never touches actual manuscript text → no content corruption
4. Architecture is modular → easy to add new style guides
5. Privacy-friendly → can swap to local LLM; formatting engine runs entirely locally
6. CSL gives us 10,000+ journal citation styles for FREE

---

# 4. SYSTEM ARCHITECTURE — MULTI-AGENT PIPELINE

## High-Level Flow

```
INPUT                    PIPELINE                              OUTPUT
─────                    ────────                              ──────

manuscript.docx  ───►  [Agent 1: Ingest & Parse]  ───►  DocIR JSON
                              │
style_guide.txt  ───►  [Agent 2: Rule Interpreter] ───►  StyleSpec JSON
                              │
                   ┌──────────┴──────────┐
                   │                     │
            [Agent 3: Structure     [Agent 4: Citation
             Detector]               Engine]
                   │                     │
                   ▼                     ▼
            Labeled DocIR          Formatted References
                   │                     │
                   └──────┬──────────────┘
                          │
                   [Agent 5: Transformer]
                          │
                          ▼
                   Formatted DOCX + Change Log
                          │
                   [Agent 6: Validator & Scorer]
                          │
                          ▼
                   output.docx + compliance_report.json
```

## Agent Details

### Agent 0: Orchestrator
- **Role:** Routes tasks to agents, maintains shared state
- **Implementation:** FastAPI endpoint that sequences the pipeline
- **Maintains:** DocIR JSON (internal document representation) + StyleSpec JSON (rules)

### Agent 1: Ingest & Parse
- **Input:** DOCX file (primary), PDF file (secondary via GROBID), plain text
- **Process:** 
  - Use `python-docx` to read every paragraph, run, table, image
  - Extract: text content, existing style names, font properties, bold/italic flags
  - Preserve: embedded images, tables, charts as-is (don't touch them)
- **Output:** DocIR JSON — our internal document representation

### Agent 2: Style Guide Interpreter (THE AGENTIC WOW FACTOR)
- **Input:** Style guide text (URL, pasted text, or uploaded PDF)
- **Process:**
  - Feed guideline text to LLM in chunks
  - LLM outputs structured StyleSpec JSON following our schema
  - Validate JSON against schema (reject hallucinated fields)
  - For APA 7: we also have a hardcoded fallback StyleSpec as ground truth
- **Output:** StyleSpec JSON
- **Why this impresses judges:** "We built a rule interpreter, not a template"

### Agent 3: Structure Detector
- **Input:** DocIR JSON
- **Process:**
  - **Pass 1 (Heuristic):** Use paragraph style names ("Heading 1", "Title", etc.), font size changes, bold patterns, known keywords ("Abstract", "References", "Introduction")
  - **Pass 2 (LLM Fallback):** For ambiguous paragraphs, send small context windows to LLM: "Is this a heading, body text, or caption?"
  - Labels every block as: `title | author_info | abstract | heading_1 | heading_2 | heading_3 | heading_4 | heading_5 | body | citation_block | reference_entry | table_caption | figure_caption | table | figure | appendix | keywords`
- **Output:** Labeled DocIR JSON (same structure, now with role annotations)

### Agent 4: Citation & Reference Engine
- **Input:** Labeled DocIR JSON (specifically reference entries + in-text citations)
- **Process:**
  1. Extract raw reference strings from the "References" section
  2. Parse each reference into structured CSL-JSON using regex + LLM fallback
  3. Extract in-text citations using regex patterns: `(Author, Year)`, `Author (Year)`, `(Author et al., Year)`
  4. Format references using `citeproc-py` with the appropriate CSL file (APA, Vancouver, IEEE, etc.)
  5. Validate: every in-text citation matches exactly one reference entry, and vice versa
  6. Flag: orphan citations (in-text with no reference), orphan references (reference with no in-text mention)
- **Output:** Formatted reference list + citation validation report

### Agent 5: Transformation Engine (DETERMINISTIC)
- **Input:** Labeled DocIR + StyleSpec JSON + Formatted References
- **Process:**
  - Set page layout: margins, size, orientation
  - Set default paragraph format: font, size, spacing, indentation
  - Apply heading styles per level (font, size, bold, italic, alignment, spacing)
  - Format title page elements
  - Format abstract (label + paragraph)
  - Replace reference section with citeproc-formatted references
  - Add running head + page numbers
  - Apply table/figure caption formatting
  - Track every single change in a diff log: `{element, old_format, new_format, rule_reference}`
- **Output:** Formatted Document object + Change Log

### Agent 6: Compliance Validator & Scorer
- **Input:** Formatted Document + StyleSpec + Change Log
- **Process:**
  - Re-scan the formatted document against StyleSpec rules
  - Score each category: page layout, typography, headings, citations, references, title page
  - Generate human-readable explanations: "Heading 'Introduction' changed from 14pt Arial to 12pt TNR Bold Centered per APA Level 1 heading rules (§ 2.27)"
  - Produce overall compliance percentage
- **Output:** `compliance_report.json` + explanation strings

---

# 5. TECH STACK — EVERY SINGLE TOOL & WHY

## Backend (Python — FastAPI)

| Tool | Version | Purpose | Why This One |
|------|---------|---------|-------------|
| **FastAPI** | latest | REST API framework | Fastest Python API framework, auto-docs with Swagger, async support |
| **python-docx** | 1.2.0 | Read/write DOCX files | Industry standard, full access to paragraph styles, runs, tables, images, sections |
| **citeproc-py** | 0.9.0 | CSL citation processor | Pure Python CSL 1.0.1 processor, formats citations/bibliographies |
| **citeproc-py-styles** | 0.1.5 | CSL style files (10K+ styles) | Pre-packaged CSL files for APA, Vancouver, IEEE, Chicago, etc. |
| **python-pptx** | (optional) | If we need to handle presentation inputs | |
| **PyMuPDF (fitz)** | latest | PDF text extraction (fallback) | Fast, lightweight PDF reader, no Java dependency |
| **regex** | latest | Advanced citation pattern matching | Better Unicode support than `re`, needed for citation parsing |
| **pydantic** | v2 | Data validation for DocIR/StyleSpec schemas | Type safety, JSON schema generation, validation |
| **openai** / **groq** / **anthropic** | latest | LLM API client | For rule interpretation + structure classification |
| **Jinja2** | latest | Template engine for explainable output | Clean HTML report generation |

## LLM Strategy

| Scenario | Model | Cost | Why |
|----------|-------|------|-----|
| **Primary (Hackathon)** | GPT-4o / Claude Sonnet via API | ~$0.05/doc | Best quality for rule extraction & structure classification |
| **Fallback (Free)** | Groq (Llama 3.1 70B) | Free tier | Fast inference, good for hackathon budget |
| **Privacy Demo** | Ollama + Qwen2.5-7B-Instruct | Free, local | Show judges we thought about privacy |

**KEY PRINCIPLE:** LLM is ONLY used for:
1. Converting guideline prose → StyleSpec JSON (~1 call)
2. Classifying ambiguous paragraphs (~5-10 small calls per doc)
3. Parsing messy references into structured fields (~1 call per 10 refs)
4. Generating explanation text (~1 call)

LLM **NEVER** rewrites or modifies manuscript content.

## Frontend (Streamlit — Fast, Python-only)

| Tool | Purpose |
|------|---------|
| **Streamlit** | Web UI framework — file upload, preview, download |
| **streamlit-diff-viewer** or custom | Side-by-side before/after comparison |
| **plotly** | Compliance score visualization (gauge charts, bar charts) |

**Why Streamlit over React/Next.js:**
- Pure Python — no context-switching, no separate deploy
- File upload + download built-in
- Can build in 2-3 hours vs 8-10 hours for React
- Looks polished enough for a hackathon demo
- Judges see it and understand immediately

## Optional: GROBID (for PDF support — bonus feature)

| Tool | Purpose |
|------|---------|
| **GROBID** (Docker) | PDF → TEI XML structure extraction |
| **grobid-client-python** | Python wrapper for GROBID API calls |

GROBID is the gold standard for extracting structure from scientific PDFs (used by Semantic Scholar, ResearchGate, etc.). However, it requires Docker + Java, so it's a **Day 2 bonus** if time permits. For the hackathon, DOCX input is primary focus.

---

# 6. INTERNAL DATA SCHEMAS

## DocIR JSON (Document Internal Representation)

This is our universal document format — every document gets converted to this first.

```json
{
  "metadata": {
    "source_filename": "manuscript.docx",
    "source_format": "docx",
    "total_paragraphs": 87,
    "total_tables": 3,
    "total_figures": 2,
    "parsed_at": "2026-03-05T10:30:00Z"
  },
  "elements": [
    {
      "id": "elem_001",
      "type": "paragraph",
      "role": "title",
      "content": "Effects of Social Media on Academic Performance",
      "original_style": "Title",
      "formatting": {
        "font_name": "Calibri",
        "font_size": 26,
        "bold": true,
        "italic": false,
        "alignment": "center",
        "line_spacing": 1.15,
        "space_before": 0,
        "space_after": 0,
        "first_line_indent": 0
      },
      "runs": [
        {
          "text": "Effects of Social Media on Academic Performance",
          "bold": true,
          "italic": false,
          "font_name": "Calibri",
          "font_size": 26
        }
      ]
    },
    {
      "id": "elem_002",
      "type": "paragraph",
      "role": "author_info",
      "content": "John Smith\nUniversity of Technology\nCS 101: Research Methods\nDr. Jane Doe\nMarch 5, 2026",
      "formatting": { "..." : "..." }
    },
    {
      "id": "elem_015",
      "type": "paragraph",
      "role": "heading_1",
      "content": "Introduction",
      "formatting": { "..." : "..." }
    },
    {
      "id": "elem_016",
      "type": "paragraph",
      "role": "body",
      "content": "Social media has become an integral part of daily life...",
      "citations_found": [
        {"text": "(Smith, 2023)", "type": "parenthetical", "author": "Smith", "year": "2023"},
        {"text": "Jones (2022)", "type": "narrative", "author": "Jones", "year": "2022"}
      ],
      "formatting": { "..." : "..." }
    },
    {
      "id": "elem_080",
      "type": "paragraph",
      "role": "reference_entry",
      "content": "Smith, J. (2023). Digital habits and student outcomes. Journal of Education, 45(2), 112-128.",
      "parsed_reference": {
        "authors": [{"family": "Smith", "given": "J."}],
        "year": "2023",
        "title": "Digital habits and student outcomes",
        "container_title": "Journal of Education",
        "volume": "45",
        "issue": "2",
        "pages": "112-128",
        "type": "article-journal"
      }
    },
    {
      "id": "elem_050",
      "type": "table",
      "role": "table",
      "caption": "Descriptive Statistics for Study Variables",
      "table_number": 1
    },
    {
      "id": "elem_060",
      "type": "image",
      "role": "figure",
      "caption": "Distribution of Social Media Usage",
      "figure_number": 1
    }
  ]
}
```

## StyleSpec JSON (Formatting Rules)

This is what the LLM extracts from guideline text, or what we hardcode for APA 7.

```json
{
  "style_name": "APA 7th Edition",
  "style_id": "apa7",
  "csl_style": "apa",
  
  "page_layout": {
    "margin_top_inches": 1.0,
    "margin_bottom_inches": 1.0,
    "margin_left_inches": 1.0,
    "margin_right_inches": 1.0,
    "page_width_inches": 8.5,
    "page_height_inches": 11.0,
    "orientation": "portrait"
  },
  
  "default_typography": {
    "font_name": "Times New Roman",
    "font_size_pt": 12,
    "line_spacing": 2.0,
    "line_spacing_type": "double",
    "paragraph_alignment": "left",
    "first_line_indent_inches": 0.5,
    "space_after_paragraph_pt": 0,
    "space_before_paragraph_pt": 0
  },
  
  "title_page": {
    "required": true,
    "title": {
      "font_size_pt": 12,
      "bold": true,
      "alignment": "center",
      "position": "3-4 lines below top margin"
    },
    "author_name": {
      "font_size_pt": 12,
      "bold": false,
      "alignment": "center",
      "position": "one double-spaced line below title"
    },
    "affiliation": {
      "font_size_pt": 12,
      "bold": false,
      "alignment": "center"
    },
    "course_info": {
      "font_size_pt": 12,
      "alignment": "center"
    },
    "instructor": {
      "font_size_pt": 12,
      "alignment": "center"
    },
    "date": {
      "font_size_pt": 12,
      "alignment": "center"
    }
  },
  
  "abstract": {
    "label": "Abstract",
    "label_bold": true,
    "label_alignment": "center",
    "paragraph_indent": false,
    "max_words": 250,
    "keywords_label": "Keywords:",
    "keywords_italic": true,
    "keywords_indent": true
  },
  
  "headings": {
    "level_1": {
      "alignment": "center",
      "bold": true,
      "italic": false,
      "font_size_pt": 12,
      "case": "title_case",
      "standalone_line": true,
      "space_before": "double_space",
      "description": "Centered, Bold, Title Case"
    },
    "level_2": {
      "alignment": "left",
      "bold": true,
      "italic": false,
      "font_size_pt": 12,
      "case": "title_case",
      "standalone_line": true,
      "description": "Flush Left, Bold, Title Case"
    },
    "level_3": {
      "alignment": "left",
      "bold": true,
      "italic": true,
      "font_size_pt": 12,
      "case": "title_case",
      "standalone_line": true,
      "description": "Flush Left, Bold Italic, Title Case"
    },
    "level_4": {
      "alignment": "indented",
      "bold": true,
      "italic": false,
      "font_size_pt": 12,
      "case": "title_case",
      "standalone_line": false,
      "ends_with_period": true,
      "description": "Indented, Bold, Title Case, Ending With Period. (Paragraph starts on same line)"
    },
    "level_5": {
      "alignment": "indented",
      "bold": true,
      "italic": true,
      "font_size_pt": 12,
      "case": "title_case",
      "standalone_line": false,
      "ends_with_period": true,
      "description": "Indented, Bold Italic, Title Case, Ending With Period. (Paragraph starts on same line)"
    }
  },
  
  "running_head": {
    "enabled": true,
    "content": "SHORTENED TITLE",
    "alignment": "left",
    "page_number_alignment": "right",
    "font_size_pt": 12,
    "all_caps": true,
    "max_characters": 50
  },
  
  "references": {
    "section_label": "References",
    "label_bold": true,
    "label_alignment": "center",
    "entry_indent_type": "hanging",
    "hanging_indent_inches": 0.5,
    "order": "alphabetical_by_first_author",
    "line_spacing": 2.0,
    "csl_style_name": "apa"
  },
  
  "tables": {
    "number_label": "Table",
    "number_bold": true,
    "number_italic": false,
    "title_italic": true,
    "title_below_number": true,
    "note_prefix": "Note.",
    "note_italic_prefix": true,
    "horizontal_lines_only": true
  },
  
  "figures": {
    "number_label": "Figure",
    "number_bold": true,
    "number_italic": true,
    "title_italic": true,
    "title_below_number": true,
    "note_prefix": "Note.",
    "note_italic_prefix": true
  },
  
  "in_text_citations": {
    "style": "author-date",
    "parenthetical_format": "(Author, Year)",
    "narrative_format": "Author (Year)",
    "et_al_threshold": 3,
    "ampersand_in_parenthetical": true,
    "and_in_narrative": true
  }
}
```

---

# 7. PHASE-BY-PHASE IMPLEMENTATION PLAN (40 Hours)

## PHASE 0: Setup & Foundation (Hours 0-2)
**Goal:** Project scaffold, dependencies installed, ready to code.

| Task | Time | Details |
|------|------|---------|
| Create project structure | 15 min | See folder structure below |
| Set up Python virtual environment | 10 min | `python -m venv venv` |
| Install core dependencies | 15 min | `pip install fastapi uvicorn python-docx citeproc-py citeproc-py-styles pydantic openai streamlit regex` |
| Create Pydantic models for DocIR + StyleSpec | 45 min | Based on schemas above |
| Hardcode APA 7 StyleSpec JSON | 30 min | From the rules in Section 8 |
| Set up LLM client (OpenAI/Groq) | 15 min | API key config, wrapper function |

**Deliverable:** Running project skeleton with schemas defined.

---

## PHASE 1: DOCX Ingestion & Structure Detection (Hours 2-10)
**Goal:** Upload a DOCX → get a labeled DocIR JSON with all structure elements identified.

### Hour 2-5: DOCX Parser
| Task | Time | Details |
|------|------|---------|
| Build DOCX → DocIR converter | 2h | Read every paragraph + run with python-docx, capture all formatting properties |
| Handle tables extraction | 30 min | Iterate `doc.tables`, store structure, detect captions above/below |
| Handle images/figures | 30 min | Detect inline shapes, relationship IDs, captions |

**Key Code Concepts:**
```python
from docx import Document
from docx.shared import Pt, Inches, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH

doc = Document("manuscript.docx")
for para in doc.paragraphs:
    element = {
        "content": para.text,
        "style_name": para.style.name,  # e.g., "Heading 1", "Normal"
        "alignment": para.alignment,
        "runs": [{
            "text": run.text,
            "bold": run.bold,
            "italic": run.italic,
            "font_name": run.font.name,
            "font_size": run.font.size,
        } for run in para.runs]
    }
```

### Hour 5-10: Structure Detector
| Task | Time | Details |
|------|------|---------|
| Rule-based classifier v1 | 2h | Use style names + keyword patterns + font analysis |
| LLM fallback for ambiguous | 1.5h | Send context window of 3-5 paragraphs to LLM |
| Title/abstract detection | 30 min | First big/bold element = title; "Abstract" keyword = abstract section |
| Heading level inference | 1h | Combine style name, font size, bold/italic, relative position |
| Reference section boundary | 30 min | Detect "References" heading → all subsequent paras are reference entries |
| Citation extraction (regex) | 1h | Pattern matching for (Author, Year), Author (Year), et al. |

**Heuristic Rules for Structure Detection:**
```
IF para.style.name contains "Title" → role = title
IF para.style.name contains "Heading" → role = heading_N (extract level from style)
IF para.text.strip() == "Abstract" AND para is bold/centered → role = abstract_label
IF para follows abstract_label and no heading before next heading → role = abstract_body
IF para.text.strip() == "References" AND is heading-like → role = references_label
IF para follows references_label → role = reference_entry  
IF para.text matches citation_regex → extract citations from body paragraphs
IF font_size > default AND bold → likely a heading (infer level from size)
```

**Citation Regex Patterns:**
```python
# Parenthetical: (Smith, 2023) or (Smith & Jones, 2023) or (Smith et al., 2023)
PARENTHETICAL = r'\(([A-Z][a-z]+(?:\s(?:&|and)\s[A-Z][a-z]+)?(?:\set\sal\.)?,\s*\d{4}[a-z]?(?:;\s*[A-Z][a-z]+(?:\s(?:&|and)\s[A-Z][a-z]+)?(?:\set\sal\.)?,\s*\d{4}[a-z]?)*)\)'

# Narrative: Smith (2023) or Smith and Jones (2023) or Smith et al. (2023)
NARRATIVE = r'([A-Z][a-z]+(?:\s(?:and|&)\s[A-Z][a-z]+)?(?:\set\sal\.)?)\s*\((\d{4}[a-z]?)\)'
```

**Deliverable:** Upload manuscript.docx → see detected structure tree with confidence scores.

---

## PHASE 2: Transformation Engine — Core Formatting (Hours 10-22)
**Goal:** Take labeled DocIR + StyleSpec → produce formatted DOCX.

### Hour 10-13: Page Layout & Typography
| Task | Time | Details |
|------|------|---------|
| Set page margins | 30 min | `section.top_margin = Inches(1.0)` etc. |
| Set default font | 30 min | Modify `doc.styles['Normal'].font` |
| Set line spacing to double | 30 min | `paragraph_format.line_spacing = 2.0` |
| Set first-line indent | 30 min | `paragraph_format.first_line_indent = Inches(0.5)` for body text |
| Add running head + page numbers | 1h | Header/footer manipulation with python-docx |

### Hour 13-16: Heading Formatting
| Task | Time | Details |
|------|------|---------|
| Create/modify heading styles for 5 levels | 2h | Match APA 7 specifications exactly |
| Apply heading styles to detected headings | 1h | Iterate labeled DocIR, set paragraph properties |

**APA 7 Heading Implementation:**
```python
def apply_apa_heading(paragraph, level):
    pf = paragraph.paragraph_format
    for run in paragraph.runs:
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)
    
    if level == 1:  # Centered, Bold
        pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in paragraph.runs:
            run.bold = True
            run.italic = False
    elif level == 2:  # Flush Left, Bold
        pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
        for run in paragraph.runs:
            run.bold = True
            run.italic = False
    elif level == 3:  # Flush Left, Bold Italic
        pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
        for run in paragraph.runs:
            run.bold = True
            run.italic = True
    # ... etc. for levels 4-5
```

### Hour 16-18: Title Page Formatting
| Task | Time | Details |
|------|------|---------|
| Detect/create title page elements | 1h | Title, author, affiliation, etc. |
| Apply APA 7 title page formatting | 1h | Centered, proper spacing, bold title |

### Hour 18-20: Abstract Formatting
| Task | Time | Details |
|------|------|---------|
| Format abstract label | 30 min | "Abstract" centered, bold |
| Format abstract body | 30 min | No indent, single paragraph, check word count |
| Format keywords line | 30 min | "Keywords:" italic, indented, keywords in plain text |

### Hour 20-22: Body Text & General Cleanup
| Task | Time | Details |
|------|------|---------|
| Apply body paragraph formatting | 1h | Font, size, spacing, indent for all body text |
| Preserve tables/figures | 30 min | Don't reformat content, only add proper captions |
| Table/figure caption formatting | 30 min | "Table 1" bold, title italic below |

**Deliverable:** Upload manuscript.docx → download formatted_manuscript.docx that looks like proper APA 7.

---

## PHASE 3: Citation & Reference Engine (Hours 22-30)
**Goal:** Parse, validate, and reformat all citations and references.

### Hour 22-25: Reference Parsing
| Task | Time | Details |
|------|------|---------|
| Extract reference strings | 1h | Split reference section into individual entries |
| Parse references into structured data | 2h | Regex + LLM to extract: authors, year, title, journal, volume, pages, DOI |

**Reference Parsing Strategy (Regex + LLM hybrid):**
```python
# Step 1: Try regex patterns for common formats
JOURNAL_PATTERN = r'^(.+?)\s*\((\d{4})\)\.\s*(.+?)\.\s*(.+?),\s*(\d+)(?:\((\d+)\))?,\s*(.+?)\.(?:\s*https?://doi\.org/(.+))?$'

# Step 2: If regex fails, use LLM
prompt = """Parse this reference into structured fields:
"{ref_string}"
Return JSON: {authors: [{family, given}], year, title, container_title, volume, issue, pages, doi, type}"""
```

### Hour 25-28: Citation Formatting with citeproc-py
| Task | Time | Details |
|------|------|---------|
| Set up citeproc-py with APA style | 1h | Load CSL file, create bibliography engine |
| Convert parsed refs to CSL-JSON | 1h | Map our parsed fields to CSL-JSON format |
| Render formatted bibliography | 1h | Use citeproc-py to generate properly formatted reference list |

**citeproc-py Integration:**
```python
from citeproc import CitationStylesStyle, CitationStylesBibliography, formatter
from citeproc.source.json import CiteProcJSON
from citeproc_styles import get_style_filepath

# Load APA style
style_path = get_style_filepath('apa')
style = CitationStylesStyle(style_path)

# Create source from parsed references
csl_data = [ref.to_csl_json() for ref in parsed_references]
source = CiteProcJSON(csl_data)

# Generate bibliography
bib = CitationStylesBibliography(style, source, formatter.plain)
# Register citations...
formatted_refs = bib.bibliography()  # Perfectly formatted APA references!
```

### Hour 28-30: Citation Consistency Validation
| Task | Time | Details |
|------|------|---------|
| Build citation↔reference matcher | 1h | Fuzzy match in-text citations to reference entries |
| Identify orphan citations | 30 min | In-text citations with no matching reference |
| Identify orphan references | 30 min | References never cited in text |

**Matching Logic:**
```python
def match_citation_to_reference(citation, references):
    """
    citation: {"author": "Smith", "year": "2023"}
    references: [{"authors": [{"family": "Smith"}], "year": "2023"}, ...]
    
    Match by: first author family name + year
    Handle: et al. (match first author), multiple authors, year suffixes
    """
    matches = []
    for ref in references:
        first_author = ref["authors"][0]["family"]
        if first_author.lower() == citation["author"].lower() and ref["year"] == citation["year"]:
            matches.append(ref)
    return matches  # Should be exactly 1; 0 = orphan citation; 2+ = ambiguous
```

**Deliverable:** All references formatted by citeproc-py + validation report showing consistency.

---

## PHASE 4: Style Guide Interpreter Agent (Hours 30-34)
**Goal:** The "agentic" part — LLM reads a style guide URL/text and produces StyleSpec JSON.

### Hour 30-34: LLM Rule Extraction
| Task | Time | Details |
|------|------|---------|
| Build guideline text extractor | 1h | Fetch URL content, extract relevant text, chunk it |
| Design LLM extraction prompt | 1h | System + user prompt that produces StyleSpec JSON |
| Implement validation + fallback | 1h | Validate LLM output against Pydantic schema; fallback to hardcoded if invalid |
| Test with APA 7 (Purdue OWL) | 1h | Verify LLM-extracted rules match our hardcoded ones |

**LLM Extraction Prompt:**
```
SYSTEM: You are an expert academic formatting analyst. Given journal/style guide 
instructions, extract ALL formatting rules into a structured JSON format.

USER: Here are the formatting guidelines for {style_name}:
---
{guideline_text}
---

Extract all rules into this exact JSON schema:
{StyleSpec JSON schema}

Be precise about:
- Page margins (in inches)
- Font family and size
- Line spacing (single=1.0, 1.5=1.5, double=2.0)
- Heading levels (alignment, bold, italic, case)
- Citation style (author-date, numbered, etc.)
- Reference list formatting (hanging indent, ordering)
- Title page requirements

Return ONLY valid JSON. If a rule is not specified, use null.
```

**Deliverable:** Paste any style guide text → get StyleSpec JSON. Show this working for APA 7 + at least one other style (Vancouver or IEEE).

---

## PHASE 5: Frontend, Compliance Dashboard, Polish (Hours 34-40)
**Goal:** Streamlit UI + compliance scoring + final integration.

### Hour 34-37: Streamlit UI
| Task | Time | Details |
|------|------|---------|
| File upload component | 30 min | `st.file_uploader("Upload Manuscript", type=["docx"])` |
| Style guide selector | 30 min | Dropdown: APA 7, Vancouver, IEEE + "Custom (paste text)" |
| Processing pipeline integration | 1h | Call backend, show progress bar |
| Results display | 1h | Three panels: detected structure, compliance score, download |

**Streamlit Layout:**
```
┌─────────────────────────────────────────────────────────────────┐
│  FormatForge AI — Agent Paperpal                  [Upload] [Go] │
├───────────────────┬─────────────────────┬───────────────────────┤
│  STRUCTURE VIEW   │  COMPLIANCE SCORE   │  CHANGES LOG          │
│                   │                     │                       │
│  📄 Title         │  Overall: 87%       │  ✅ Margins → 1"      │
│  👤 Authors       │  ████████░░         │  ✅ Font → TNR 12pt   │
│  📝 Abstract      │                     │  ✅ Heading 1 styled  │
│  📋 Introduction  │  Page Layout: 100%  │  ⚠️ 2 orphan refs    │
│  📋 Methods       │  Typography: 95%    │  ✅ Spacing → double  │
│  📋 Results       │  Headings: 90%      │  ✅ Abstract label    │
│  📋 Discussion    │  Citations: 75%     │  ❌ Figure 2 no cap   │
│  📚 References    │  References: 80%    │                       │
│                   │  Title Page: 85%    │                       │
├───────────────────┴─────────────────────┴───────────────────────┤
│  [📥 Download Formatted DOCX]  [📊 Download Report JSON]        │
└─────────────────────────────────────────────────────────────────┘
```

### Hour 37-38: Compliance Scorer
| Task | Time | Details |
|------|------|---------|
| Implement category-level scoring | 30 min | Check each rule, compute percentage |
| Generate explanations | 30 min | "Changed X to Y per APA rule Z" |

### Hour 38-39: Integration Testing & Bug Fixes
| Task | Time | Details |
|------|------|---------|
| Test with 2-3 sample manuscripts | 30 min | Verify end-to-end flow |
| Fix critical bugs | 30 min | Prioritize: output must open in Word without corruption |

### Hour 39-40: Demo Prep
| Task | Time | Details |
|------|------|---------|
| Prepare demo script | 30 min | Upload → detect → format → download → open in Word |
| Polish slides | 30 min | Architecture diagram, key results, integration ideas |

**Deliverable:** Fully functional demo: upload → process → download + compliance dashboard.

---

# 8. APA 7TH EDITION — COMPLETE RULE SPECIFICATION

## Page Layout
- **Margins:** 1 inch on all sides (top, bottom, left, right)
- **Paper size:** 8.5 × 11 inches (US Letter)
- **Orientation:** Portrait

## Typography
- **Font:** Times New Roman 12pt (or: Calibri 11pt, Arial 11pt, Georgia 11pt, Lucida Unicode 10pt — TNR 12 is the most common)
- **Line spacing:** Double-spaced throughout (2.0)
- **Paragraph indent:** 0.5 inch first-line indent for body paragraphs
- **Alignment:** Left-aligned (ragged right edge, NOT justified)
- **No extra spacing** between paragraphs (space before/after = 0 pt)

## Title Page (Student Paper — APA 7)
- **Title:** Bold, centered, Title Case, 3-4 lines down from top margin
- **Author name(s):** One double-spaced line below title, centered
- **Affiliation:** Department and University, centered, one line below author
- **Course number and name:** Centered, below affiliation
- **Instructor name:** Centered
- **Assignment due date:** Centered

**Note:** APA 7 student papers do NOT have a running head by default (unlike professional papers).

## Headings (5 Levels)

| Level | Format |
|-------|--------|
| 1 | Centered, **Bold**, Title Case |
| 2 | Flush Left, **Bold**, Title Case |
| 3 | Flush Left, ***Bold Italic***, Title Case |
| 4 | Indented 0.5", **Bold**, Title Case, Period. Text continues on same line. |
| 5 | Indented 0.5", ***Bold Italic***, Title Case, Period. Text continues on same line. |

All headings: Same font as body (TNR 12pt), double-spaced, NO extra space before/after beyond double spacing.

## Abstract
- **Label:** "Abstract" — centered, bold, NOT italic
- **Body:** Single paragraph, no indentation, 150-250 words
- **Keywords:** New line below abstract, indented 0.5", "Keywords:" in italic, followed by keywords in plain text, separated by commas

## In-Text Citations
- **Parenthetical:** (Author, Year) — use ampersand (&) for multiple authors in parentheses
- **Narrative:** Author (Year) — use "and" for multiple authors in running text
- **3+ authors:** Use "et al." from first citation onward
- **Multiple works:** (Smith, 2020; Jones, 2021) — semicolon separated, alphabetical
- **Direct quote:** (Author, Year, p. X) or (Author, Year, para. X)

## Reference List
- **Label:** "References" — centered, bold (same format as Level 1 heading)
- **Entries:** Alphabetical by first author's last name
- **Indent:** Hanging indent — first line flush left, subsequent lines indented 0.5"
- **Spacing:** Double-spaced, no extra space between entries
- **DOI format:** https://doi.org/xxxxx (as clickable hyperlink when possible)
- **Journal articles:** Author, A. A. (Year). Title of article. *Title of Journal, Volume*(Issue), Pages. https://doi.org/xxxxx
- **Books:** Author, A. A. (Year). *Title of book* (Edition). Publisher.

## Tables
- **Number:** "Table 1" — bold, flush left, plain text
- **Title:** One double-spaced line below number — italic, flush left, Title Case
- **Borders:** Top and bottom horizontal lines for the table; header row has bottom border; NO vertical lines
- **Note:** Below table: "Note." in italic, followed by text in plain

## Figures
- **Number:** "Figure 1" — bold, italic, flush left
- **Title:** One double-spaced line below number — italic, flush left, Title Case
- **Note:** Below figure: "Note." in italic, followed by text in plain

## Running Head (Professional Papers Only)
- **Header left:** Shortened title in ALL CAPS (max 50 characters)
- **Header right:** Page number
- **Font:** Same as body (TNR 12pt)

## Page Numbers
- **Position:** Top right of every page (including title page)
- **Starting:** Page 1 on title page

---

# 9. CITATION CONSISTENCY ENGINE — DEEP DIVE

This is one of the most impactful features for judging. The slides specifically highlight:
> "Every in-text cite resolves to exactly one reference entry — and vice versa — across the full document"

## The Three Validation Checks

### Check 1: Every in-text citation has a matching reference
```
For each citation (Author, Year) found in body text:
    Search references for matching author + year
    IF matches == 0: FLAG as "Orphan Citation" (Error)
    IF matches == 1: LINK citation → reference (Success)
    IF matches > 1: FLAG as "Ambiguous Citation" (Warning)
```

### Check 2: Every reference is cited at least once
```
For each reference in the reference list:
    Search all body text for matching citation
    IF found: LINK reference → citation(s) (Success)
    IF not found: FLAG as "Uncited Reference" (Warning)
```

### Check 3: Citation format matches style
```
For each citation:
    CHECK ampersand (&) vs "and" usage
    CHECK et al. threshold (3+ authors in APA 7)
    CHECK year present
    CHECK parentheses formatting
```

## Output: Citation Consistency Report
```json
{
  "total_citations": 24,
  "total_references": 18,
  "matched": 16,
  "orphan_citations": [
    {"text": "(Brown, 2019)", "location": "paragraph 12", "issue": "No matching reference found"}
  ],
  "uncited_references": [
    {"reference": "Davis, M. (2020). ...", "issue": "Not cited anywhere in text"}
  ],
  "format_issues": [
    {"text": "Smith and Jones (2023)", "issue": "Should use '&' in parenthetical citations", "location": "paragraph 8"}
  ],
  "consistency_score": 88.9
}
```

---

# 10. COMPLIANCE SCORING & EXPLAINABILITY

## Scoring Categories

| Category | Weight | What's Checked |
|----------|--------|---------------|
| Page Layout | 15% | Margins (1"), page size, orientation |
| Typography | 15% | Font (TNR 12pt), line spacing (double), indent (0.5") |
| Headings | 15% | Correct level formatting, title case, alignment |
| Title Page | 10% | All required elements, proper formatting |
| Abstract | 10% | Label, no indent, word count, keywords format |
| Citations (in-text) | 15% | Correct format, & vs and, et al. usage |
| References | 15% | Hanging indent, alphabetical, CSL-formatted |
| Tables/Figures | 5% | Numbering, captions, formatting |

## Explainable Corrections Format

Every change generates an explanation string:
```
✅ Page margins changed from 0.75" to 1.0" (all sides) — APA 7 §2.22
✅ Font changed from Calibri 11pt to Times New Roman 12pt — APA 7 §2.19
✅ Line spacing changed from 1.15 to 2.0 (double) — APA 7 §2.21
✅ Heading "Introduction" changed from 14pt Bold to 12pt Bold Centered — APA 7 Level 1 heading §2.27
✅ First-line indent set to 0.5" for body paragraphs — APA 7 §2.24
⚠️ Abstract is 312 words (max recommended: 250) — APA 7 §2.9
✅ Reference list formatted with 0.5" hanging indent — APA 7 §2.12
❌ Citation "(Brown, 2019)" has no matching reference — needs manual review
✅ Running head added: "EFFECTS OF SOCIAL MEDIA" — APA 7 §2.8
```

---

# 11. FRONTEND / DEMO UI

## Streamlit App Structure

```python
# app.py
import streamlit as st

st.set_page_config(page_title="FormatForge AI", layout="wide")
st.title("🎓 FormatForge AI — Agent Paperpal")
st.subheader("Agentic Manuscript Formatting System")

# Sidebar
with st.sidebar:
    uploaded_file = st.file_uploader("Upload Manuscript", type=["docx", "pdf", "txt"])
    style_choice = st.selectbox("Select Style Guide", ["APA 7th Edition", "Vancouver", "IEEE", "Chicago"])
    custom_guidelines = st.text_area("Or paste custom guidelines...")
    process_btn = st.button("🚀 Format Document", type="primary")

# Main area - 3 columns
if process_btn and uploaded_file:
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        st.subheader("📄 Detected Structure")
        # Show tree view of detected elements
    
    with col2:
        st.subheader("📊 Compliance Score")
        # Show gauge/bar charts
    
    with col3:
        st.subheader("📝 Changes Made")
        # Show list of explainable corrections
    
    # Download buttons
    st.download_button("📥 Download Formatted DOCX", data=output_docx)
    st.download_button("📊 Download Compliance Report", data=report_json)
```

---

# 12. API DESIGN

## FastAPI Endpoints

```
POST /api/v1/format
  Body: {file: UploadFile, style: str, guidelines_text?: str}
  Response: {formatted_doc_url, compliance_report, change_log}

POST /api/v1/parse
  Body: {file: UploadFile}
  Response: {docir: DocIR}  # Just structure detection

POST /api/v1/interpret-rules
  Body: {guidelines_text: str, guidelines_url?: str}
  Response: {style_spec: StyleSpec}

POST /api/v1/validate-citations
  Body: {file: UploadFile}
  Response: {citation_report: CitationReport}

GET /api/v1/styles
  Response: {available_styles: ["apa7", "vancouver", "ieee", "chicago"]}

GET /api/v1/health
  Response: {status: "ok", version: "1.0.0"}
```

---

# 13. FOLDER STRUCTURE

```
FormatForge/
├── app.py                          # Streamlit frontend (entry point)
├── requirements.txt                # All Python dependencies
├── README.md                       # Project documentation
├── .env                            # API keys (OPENAI_API_KEY, etc.)
│
├── backend/
│   ├── __init__.py
│   ├── api.py                      # FastAPI app & endpoints
│   ├── config.py                   # Configuration / settings
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── docir.py                # DocIR Pydantic models
│   │   ├── style_spec.py           # StyleSpec Pydantic models
│   │   └── reports.py              # ComplianceReport, CitationReport models
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── orchestrator.py         # Main pipeline controller
│   │   ├── ingest.py               # Agent 1: DOCX/PDF → DocIR
│   │   ├── structure_detector.py   # Agent 3: Label paragraphs with roles
│   │   ├── rule_interpreter.py     # Agent 2: Guidelines → StyleSpec
│   │   ├── citation_engine.py      # Agent 4: Parse, format, validate citations
│   │   ├── transformer.py          # Agent 5: Apply formatting to DOCX
│   │   └── validator.py            # Agent 6: Compliance scoring & explanations
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py               # LLM API wrapper (OpenAI/Groq/Ollama)
│   │   └── prompts.py              # All LLM prompts centralized
│   │
│   ├── styles/
│   │   ├── __init__.py
│   │   ├── apa7.json               # Hardcoded APA 7 StyleSpec
│   │   ├── vancouver.json          # Hardcoded Vancouver StyleSpec
│   │   └── ieee.json               # Hardcoded IEEE StyleSpec
│   │
│   └── utils/
│       ├── __init__.py
│       ├── citation_parser.py      # Regex patterns for citation extraction
│       ├── reference_parser.py     # Reference string → structured data
│       └── text_utils.py           # Title case, text cleaning, etc.
│
├── tests/
│   ├── test_ingest.py
│   ├── test_structure.py
│   ├── test_transformer.py
│   └── sample_manuscripts/         # Test DOCX files
│       ├── messy_apa_paper.docx
│       └── sample_research.docx
│
└── output/                          # Generated files go here
    ├── formatted/
    └── reports/
```

---

# 14. RISK MITIGATION & FAILURE MODES

## Top Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **DOCX figures/tables break on save** | High | Medium | DON'T move them. Only reformat captions + surrounding text. Preserve all OLE objects. |
| **LLM hallucinates formatting rules** | Medium | Medium | Always validate LLM output against Pydantic schema. Have hardcoded fallback StyleSpec for APA. |
| **Citation parsing fails on unusual formats** | Medium | High | Start with regex, fall back to LLM. Accept partial results — any correct matches boost score. |
| **LLM changes manuscript content** | Critical | Low | LLM NEVER receives manuscript body text for modification. Only structure classification + rule extraction. |
| **python-docx loses formatting on complex docs** | Medium | Medium | Test with progressively complex docs. Worst case: format what we can, leave rest untouched. |
| **GROBID Docker setup fails** | Low | Medium | GROBID is a Day 2 BONUS. Primary path is DOCX-only, which requires no Docker at all. |
| **API key rate limits / costs** | Medium | Low | Use Groq free tier for fallback. Cache LLM responses. Minimize API calls. |
| **Streamlit performance on large docs** | Low | Low | Process server-side, only display summary + download in Streamlit. |

## Emergency Fallback Plan (If Behind Schedule)

If by hour 30 the system isn't end-to-end, prioritize:
1. ✅ DOCX uploads and structure detection works → show this alone (counts for "intermediate steps")
2. ✅ Page layout + heading formatting works → show before/after comparison
3. ✅ Compliance report is generated → show the scoring dashboard
4. ❌ Skip citation engine (hard) → just show detected citations as-is
5. ❌ Skip multi-style support → APA-only is perfectly fine

---

# 15. PRESENTATION & MENTOR STRATEGY

## Key Talking Points (30-second version)

> "We built FormatForge AI — an agentic manuscript formatting system. Rather than templating, we built a rule interpreter. Our LLM reads journal guidelines and extracts machine-readable rules. Our deterministic engine then formats the document precisely — no hallucination risk. We use CSL's 10,000+ citation styles for reference formatting. Everything is modular: swap in new style guides without rebuilding the pipeline."

## Mentor-Specific Talking Points

- **Riddhi Shah (Product Manager):** Talk about the product integration. "This could be a Paperpal Preflight feature — upload your manuscript, select target journal, get instant compliance check + auto-format."
- **Sachinkumar Patel (Software Architect):** Talk about the agent architecture, modularity, API design, how each agent is independently testable and scalable.
- **Kunal Sawhney (Sr. Engineering):** Talk about tech scalability — CSL gives 10K+ styles, modular design, API-first approach.
- **Fenil Ramoliya (ML Engineer, MiNED '24 winner):** Talk about the LLM-deterministic hybrid, why we DON'T let LLM format text directly, privacy considerations.
- **Bhargav Modha (ML Engineer, MiNED '23 winner):** Talk about NLP challenges in structure detection, citation parsing, handling ambiguity.

## The Brownie Points (Do Before Demo!)

1. **Register and use Paperpal** (paperpal.com) — test Manuscript Check and Preflight
2. **Install RDiscovery Chrome extension** — try "Ask RDiscovery" feature
3. In your presentation, suggest 3 concrete integration ideas:
   - "FormatForge could power Paperpal's Preflight formatting check"
   - "RDiscovery could surface target journal requirements when a paper is uploaded"
   - "The Citation Consistency Engine could be a standalone Paperpal feature"

## Demo Script (5 minutes)

1. **[30s]** Show the Streamlit UI — clean, professional
2. **[30s]** Upload a messy manuscript.docx — show the original (bad formatting)
3. **[30s]** Select "APA 7th Edition" — click "Format"
4. **[60s]** Show the three result panels:
   - Structure detection tree (Title, Abstract, Headings, etc.)
   - Compliance score dashboard (85%+ overall)
   - Change log with explanations ("Changed X to Y per APA rule Z")
5. **[30s]** Download the formatted DOCX — open in Word — show it looks correct
6. **[30s]** Switch to "Vancouver" style — show it works with another style too (bonus!)
7. **[60s]** Show the architecture slide — explain the 6 agents + hybrid approach
8. **[30s]** Show the API endpoints in FastAPI Swagger docs — prove it's API-first
9. **[30s]** Close with: "This is scalable to any journal with CSL's 10,000+ styles. Privacy-ready with local LLM option."

---

# 16. SCORING RUBRIC MAP — EXACTLY HOW WE WIN POINTS

| Criteria | Weight | What We Show | Expected Score |
|----------|--------|-------------|----------------|
| **Formatting Accuracy** | 30% | APA 7 headings, margins, font, spacing, citations — all correct. Side-by-side before/after. | 25-28/30 |
| **Working Demo** | 30% | Upload DOCX → format → download. Streamlit UI with structure view, compliance score, change log. | 27-30/30 |
| **Presentation & Engagement** | 20% | Clear explanation of architecture, Paperpal integration ideas, using their products (Paperpal, RDiscovery). | 16-18/20 |
| **Tech Scalability** | 20% | CSL (10K styles), modular agents, API-first, StyleSpec schema supports any journal, privacy-ready. | 17-19/20 |
| **TOTAL** | 100% | | **85-95/100** |

---

# SUMMARY: WHAT MAKES US WIN

1. **Hybrid Architecture** — LLM for understanding, deterministic code for precision. No other team will have this clarity.
2. **CSL Integration** — 10,000+ citation styles for free. Instant scalability.
3. **Explainable Corrections** — Every change comes with a "why" and a rule reference. Builds trust.
4. **Compliance Dashboard** — Visual, quantitative scoring. Judges love metrics.
5. **Working Demo** — Upload → Process → Download → Open in Word. End-to-end.
6. **Clean Architecture** — 6 modular agents. Any engineer can understand and extend it.
7. **Privacy-Ready** — Can swap to local LLM. Deterministic core runs entirely offline.
8. **Mentor Engagement** — We used their products. We have integration ideas. We speak their language.

---

*Document created: March 5, 2026*  
*Team: HackaMined 2026*  
*Target: 1st Place — INR 15K + AI Engineering Internship*
