<div align="center">

# FormatForge AI

### Agentic Academic Manuscript Formatter

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![Groq](https://img.shields.io/badge/LLM-Groq_llama--3.3--70b-F55036?style=for-the-badge)](https://groq.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

**Upload a research manuscript. Select a target style. Download publication-ready output.**

*HackaMineD 2026 · Cactus Communications / Paperpal Track*

[Full Technical Documentation](DOCUMENTATION.md)

</div>

---

## What It Does

FormatForge AI takes a raw DOCX manuscript and automatically transforms it to match any of five major academic publication styles — **APA 7, IEEE, Vancouver, MLA, or Chicago** — while simultaneously generating a complete, compilable **LaTeX source file**.

The system combines a **deterministic six-agent pipeline** for reliable DOCX formatting with an **LLM-powered LaTeX generation engine**, plus a conversational **MCP Document Editor Agent** for natural-language post‑processing.

---

## Architecture at a Glance

```mermaid
graph TB
    subgraph FE["React 19 Frontend  Vite + Tailwind"]
        LP[Landing] --> UP[Upload] --> CP[Configure] --> PP[Process] --> LX[LaTeX Editor] --> MA[AI Agent Chat]
    end

    subgraph BE["FastAPI Backend  port 8000"]
        AR["v2 SSE Streaming\n/api/v2/pipeline/stream"]
        ORCH[Orchestrator]
        AR --> ORCH
    end

    subgraph P6["Six-Agent Pipeline"]
        direction LR
        A1["1 Ingest"] --> A2["2 Rule\nInterpreter"] --> A3["3 Structure\nDetector"] --> A4["4 Citation\nEngine"] --> A5["5 Transformer"] --> A6["6 Validator"]
    end

    subgraph LLM["LLM Layer"]
        AGNO[Agno Framework]
        GROQ["Groq llama-3.3-70b"]
        LC[LLM Client]
        AGNO --> GROQ
        LC --> GROQ
    end

    subgraph MCP["MCP Editor  port 8082"]
        MAPI[REST API]
        BOT["DocBot\nAgno Agent"]
        TOOLS["25+ DOCX Tools"]
        MAPI --> BOT --> TOOLS
    end

    PP -->|SSE stream| AR
    ORCH --> P6
    AR -->|Stage 2 LaTeX| AGNO
    A2 --> LC
    A3 --> LC
    MA --> MAPI
```

---

## Two-Stage Processing Pipeline

### Stage 1 — Deterministic DOCX Formatting

```mermaid
sequenceDiagram
    participant File as DOCX File
    participant A1 as Ingest
    participant A2 as Rule Interpreter
    participant A3 as Structure Detector
    participant A4 as Citation Engine
    participant A5 as Transformer
    participant A6 as Validator
    participant Out as Output

    File->>A1: Raw DOCX
    A1->>A2: DocIR with run-level formatting
    A2->>A3: StyleSpec with all formatting rules
    A3->>A4: Labeled DocIR — every paragraph role-tagged
    A4->>A5: CitationReport + updated DocIR
    A5->>A6: Formatted DOCX + change log
    A6->>Out: ComplianceReport 0-100 score
```

### Stage 2 — LLM LaTeX Generation

```mermaid
graph LR
    FMT["Formatted\nManuscript"] -->|split into sections| S1["Section 1"] & S2["Section 2"] & SN["Section N"]
    S1 & S2 & SN -->|Agno + Groq| TEX["LaTeX chunks"]
    TEX --> PRE["Style Preamble\nIEEEtran or article"]
    PRE --> POST["Post-process\nand Sanitize"]
    POST --> FINAL["Complete .tex file"]
```

---

## The Six Agents

| # | Agent | Lines | LLM? | Responsibility |
|---|-------|------:|:-----:|----------------|
| 0 | **Orchestrator** | ~130 | — | Sequences the pipeline; assembles `FormatResult` |
| 1 | **Ingest** | 329 | no | Walks DOCX Open XML; builds `DocIR` with run-level formatting |
| 2 | **Rule Interpreter** | 359 | optional | Loads JSON `StyleSpec`; interprets custom guidelines via LLM |
| 3 | **Structure Detector** | 1,119 | yes | 10-pass hybrid heuristic + LLM paragraph role classifier |
| 4 | **Citation Engine** | 797 | no | Regex parse to citeproc-py format to fuzzy consistency check |
| 5 | **Transformer** | 1,382 | no | Applies every formatting rule; inserts labels; sets columns and headers |
| 6 | **Validator** | 626 | no | Opens output DOCX; scores 8 weighted compliance categories |

> Rule Interpreter only calls the LLM when custom guidelines are provided — hardcoded styles involve zero LLM calls.

---

## Structure Detector — 10-Pass Pipeline

```mermaid
graph TD
    P0["Pass 0 · Unicode Cleanup"]:::det --> P1["Pass 1 · Word Style Names"]:::det
    P1 --> P2["Pass 2 · Section Keywords — 50+ patterns"]:::det
    P2 --> P3["Pass 3 · Reference Detection — backward scan"]:::det
    P3 --> P4["Pass 4 · Title Detection — positional heuristic"]:::det
    P4 --> P5["Pass 5 · Author and Affiliation — regex"]:::det
    P5 --> P6["Pass 6 · Abstract Detection — positional"]:::det
    P6 --> P7a["Pass 7a · Keywords"]:::det
    P7a --> P7b["Pass 7b · Figure and Table Captions"]:::det
    P7b --> P7c["Pass 7c · Front-Matter Correction"]:::det
    P7c --> P7d["Pass 7d · Page Artifact Suppression"]:::det
    P7d --> P8a["Pass 8a · Fill UNKNOWN to BODY"]:::det
    P8a --> P8b["Pass 8b · LLM Batch Correction — 40+30 paragraphs"]:::llm
    P8b --> P9["Pass 9 · In-Text Citation Extraction — 3 regex patterns"]:::det
    P9 --> P10["Pass 10 · LLM Fallback — up to 20 remaining UNKNOWN"]:::llm

    classDef det fill:#dbeafe,stroke:#2563eb,color:#1e3a8a
    classDef llm fill:#fce7f3,stroke:#db2777,color:#831843
```

---

## Data Schemas

```mermaid
classDiagram
    class DocIR {
        +DocMetadata metadata
        +List~DocElement~ elements
        +List~ParsedReference~ references
    }
    class DocElement {
        +ElementRole role
        +str text
        +ParagraphFormatting formatting
        +List~RunFormatting~ runs
        +List~InTextCitation~ citations
        +float confidence
    }
    class StyleSpec {
        +str style_name
        +PageLayout page_layout
        +DefaultTypography default_typography
        +HeadingsSpec headings
        +ReferencesSpec references
    }
    class FormatResult {
        +str output_filename
        +ComplianceReport compliance
        +CitationReport citation_report
        +float processing_time_seconds
    }
    DocIR *-- DocElement
    DocIR *-- ParsedReference
    FormatResult *-- ComplianceReport
    FormatResult *-- CitationReport
```

---

## User Journey

```mermaid
stateDiagram-v2
    direction LR
    [*] --> Landing
    Landing --> Upload : Start Formatting Free
    Upload --> Configure : DOCX uploaded
    Configure --> Process : Select style and engine

    state Process {
        direction TB
        S1 : Stage 1 Static Formatting - 6-agent deterministic pipeline
        S2 : Stage 2 LaTeX Generation - LLM chunk-by-chunk conversion
        S1 --> S2
    }

    Process --> LaTeXEditor : Open LaTeX Editor
    Process --> DownloadDOCX : Download Formatted DOCX

    state LaTeXEditor {
        direction LR
        Edit : Monaco Editor
        Compile : PDF Preview
        Edit --> Compile : Ctrl+Enter
        Compile --> Edit : Revise
    }

    LaTeXEditor --> AgentChat : Open AI Agent

    state AgentChat {
        direction TB
        Chat : Natural Language Instructions
        Preview : Live HTML Document Preview
        Chat --> Preview : DocBot edits DOCX
        Preview --> Chat
    }
```

---

## Five Academic Styles

| Feature | APA 7 | IEEE | Vancouver | MLA | Chicago |
|---------|:-----:|:----:|:---------:|:---:|:-------:|
| Font | TNR 12pt | TNR 10pt | TNR 12pt | TNR 12pt | TNR 12pt |
| Line Spacing | 2.0x | 1.0x | 2.0x | 2.0x | 2.0x |
| Columns | 1 | **2** | 1 | 1 | 1 |
| Citations | Author-date | Numeric `[N]` | Numeric `[N]` | Author-date | Author-date |
| Reference section | References | References | References | Works Cited | Bibliography |
| Running head | Yes 50 chars | No | No | No | No |
| Separate title page | Yes | No | No | No | Yes |
| Abstract max words | 250 | 200 | 300 | — | 300 |

---

## Compliance Validator

The Validator opens the actual output DOCX and scores eight weighted categories:

| Category | Weight | What Is Checked |
|----------|:------:|-----------------|
| `page_layout` | 15% | All four margins, page dimensions |
| `typography` | 15% | Font name, size, line spacing |
| `headings` | 15% | Bold, italic, alignment, case per level |
| `citations` | 15% | Citation-reference consistency score |
| `references` | 15% | Section label, hanging indent, entry spacing |
| `title_page` | 10% | Title presence, size, alignment, bold |
| `abstract` | 10% | Label presence, indent, font size |
| `tables_figures` | 5% | Caption presence and formatting |

Overall score = weighted average (0–100).

---

## MCP Document Editor Agent

After formatting, the **AI Agent** tab opens a 3-panel interface:

| Panel | Content |
|-------|---------|
| Left | Document file browser |
| Centre | Live HTML preview — auto-refreshes after every edit |
| Right | Chat window — **DocBot** powered by Agno + Groq |

DocBot has 25+ DOCX manipulation tools:

| Category | Tools |
|----------|-------|
| Reading | `read_document`, `read_paragraph`, `read_table`, `search_text`, `export_to_text` |
| Editing | `edit_paragraph_text`, `search_and_replace`, `delete_paragraph` |
| Adding | `add_paragraph`, `add_heading`, `add_table`, `add_bullet_list`, `add_numbered_list` |
| Formatting | `format_text`, `format_paragraph`, `set_paragraph_style`, `set_paragraph_alignment` |
| Management | `create_document`, `delete_document`, `duplicate_document` |

---

## Quick Start

```bash
# Clone
git clone https://github.com/vdt1905/Hack-NU-26.git
cd Hack-NU-26

# Python environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# Add your API key
echo GROQ_API_KEY=your_key_here > .env

# Launch everything (Windows)
start_all.bat

# OR start services individually
uvicorn backend.api:app --reload --port 8000   # API backend
cd frontend && npm install && npm run dev        # React frontend  http://localhost:5173
uvicorn mcp_editor.api:app --port 8082          # MCP editor agent
```

---

## Technology Stack

| Layer | Technologies |
|-------|-------------|
| Backend | Python 3.11, FastAPI, Pydantic v2, sse-starlette |
| Document I/O | python-docx, Open XML direct manipulation (lxml) |
| Citations | citeproc-py (CSL 1.0), thefuzz (Levenshtein distance) |
| LLM | Agno framework, Groq llama-3.3-70b, OpenAI fallback, Ollama local |
| MCP | FastMCP stdio transport, SqliteDb conversation persistence |
| Frontend | React 19, Vite, Tailwind CSS, Zustand state management |
| Code editor | Monaco Editor (@monaco-editor/react) |
| Animations | Framer Motion, GSAP, Three.js |
| LaTeX compile | latexonline.cc via browser-side form POST to iframe |

---

## Project Structure

```
Hack-NU-26/
├── backend/
│   ├── agents/               # orchestrator  ingest  rule_interpreter
│   │                         # structure_detector  citation_engine
│   │                         # transformer  validator  paragraph_merger
│   ├── llm/                  # LLM client wrapper + all prompt templates
│   ├── schemas/              # DocIR  StyleSpec  Reports  (Pydantic v2)
│   ├── styles/               # apa7  ieee  vancouver  mla  chicago  (JSON)
│   ├── api.py                # FastAPI v1 REST endpoints
│   └── agno_router.py        # v2 SSE streaming + LaTeX generation
├── frontend/
│   └── src/
│       ├── pages/            # Landing  Upload  Configure  Process  Latex  McpAgent
│       ├── components/       # 14 reusable UI components
│       └── store/            # useAppStore.js (Zustand)
├── mcp_editor/
│   ├── doc_editor_agent/     # DocBot Agno agent + 25+ DOCX tools
│   └── mcp_server/           # FastMCP stdio server
├── tests/                    # test_phase0 through test_phase4  test_mla_chicago
├── app.py                    # Streamlit legacy UI
├── DOCUMENTATION.md          # Full technical documentation (15 sections, 6 diagrams)
└── start_all.bat             # One-click launch (Windows)
```

---

## Full Technical Documentation

All agent internals, schema reference, API specification, LLM prompt templates, LaTeX preamble generation, style JSON structure, and extended Mermaid diagrams are in **[DOCUMENTATION.md](DOCUMENTATION.md)**.

---

<div align="center">

Built at **HackaMineD 2026** &nbsp;·&nbsp; Cactus Communications / Paperpal Track

</div>
