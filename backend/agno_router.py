"""
FormatForge AI — Unified Pipeline Router
==========================================
Full pipeline:  Static Formatting (Orchestrator) → LLM LaTeX Generation (Agno/Groq)
Exposes SSE streaming endpoint: POST /api/v2/pipeline/stream
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

logger = logging.getLogger(__name__)

agno_router = APIRouter(tags=["Unified Pipeline"])

# ---------------------------------------------------------------------------
# Lazy Agno imports
# ---------------------------------------------------------------------------
_AGNO_READY = False

try:
    from agno.agent import Agent
    from agno.models.groq import Groq as AgnoGroq

    _AGNO_READY = True
except ImportError as exc:
    logger.warning(f"Agno deps missing ({exc}). LaTeX generation will be disabled.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_from_docx(file_path: Path) -> str:
    """Extract full text from a .docx file on disk."""
    import docx

    text = ""
    doc = docx.Document(str(file_path))
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


# ---------------------------------------------------------------------------
# Chunked LaTeX helpers
# ---------------------------------------------------------------------------

# Section headings pattern for splitting
_SECTION_RE = re.compile(
    r"^(Abstract|Introduction|Background|Results|Discussion|"
    r"Materials and Methods|Methods|Significance|Conclusion|Conclusions|"
    r"Acknowledgments|ACKNOWLEDGMENTS|References|Appendix|"
    r"Supplementary|Supporting Information)",
    re.IGNORECASE | re.MULTILINE,
)

_MAX_CHUNK_CHARS = 5000  # ~1200 words, safely under Groq output limits


def _split_into_sections(text: str) -> list[dict]:
    """
    Split a manuscript into logical sections for chunked LLM processing.
    Returns list of {"title": str, "content": str} dicts.
    """
    lines = text.split("\n")
    sections: list[dict] = []
    current_title = "Preamble"
    current_lines: list[str] = []

    for line in lines:
        match = _SECTION_RE.match(line.strip())
        if match and len(current_lines) > 0:
            sections.append({
                "title": current_title,
                "content": "\n".join(current_lines).strip(),
            })
            current_title = line.strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append({
            "title": current_title,
            "content": "\n".join(current_lines).strip(),
        })

    # Filter out empty sections
    sections = [s for s in sections if s["content"].strip()]

    # Further split any section that's too large
    final_sections: list[dict] = []
    for sec in sections:
        if len(sec["content"]) <= _MAX_CHUNK_CHARS:
            final_sections.append(sec)
        else:
            # Split large sections into sub-chunks by paragraph
            paragraphs = sec["content"].split("\n\n")
            chunk_lines: list[str] = []
            chunk_idx = 1
            for para in paragraphs:
                if len("\n\n".join(chunk_lines)) + len(para) + 2 > _MAX_CHUNK_CHARS and chunk_lines:
                    final_sections.append({
                        "title": f"{sec['title']} (Part {chunk_idx})",
                        "content": "\n\n".join(chunk_lines).strip(),
                    })
                    chunk_lines = [para]
                    chunk_idx += 1
                else:
                    chunk_lines.append(para)
            if chunk_lines:
                final_sections.append({
                    "title": f"{sec['title']} (Part {chunk_idx})" if chunk_idx > 1 else sec["title"],
                    "content": "\n\n".join(chunk_lines).strip(),
                })

    return final_sections


def _clean_chunk_latex(raw: str) -> str:
    """Clean LLM output to extract just the LaTeX body content (no preamble/document tags)."""
    text = raw.strip()
    # Remove markdown fences
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        text = text.strip()
    # Remove any \documentclass, \usepackage, \begin{document}, \end{document}
    text = re.sub(r"\\documentclass(\[.*?\])?\{.*?\}", "", text)
    text = re.sub(r"\\usepackage(\[.*?\])?\{.*?\}", "", text)
    text = re.sub(r"\\begin\{document\}", "", text)
    text = re.sub(r"\\end\{document\}", "", text)
    text = re.sub(r"\\maketitle", "", text)
    text = re.sub(r"\\printbibliography", "", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Style-specific LaTeX preamble builder
# ---------------------------------------------------------------------------

_PREAMBLE_MAP: dict[str, str] = {
    "ieee": (
        "\\documentclass[conference]{IEEEtran}\n"
        "\\usepackage{cite}\n"
        "\\usepackage{amsmath,amssymb,amsfonts}\n"
        "\\usepackage{graphicx}\n"
        "\\usepackage{textcomp}\n"
        "\\usepackage{xcolor}\n"
        "\\usepackage{hyperref}\n"
        "\\usepackage{float}\n"
        "\\usepackage[utf8]{inputenc}\n"
        "\\usepackage[T1]{fontenc}\n"
    ),
    "apa7": (
        "\\documentclass[12pt]{article}\n"
        "\\usepackage[margin=1in]{geometry}\n"
        "\\usepackage{times}\n"
        "\\usepackage{setspace}\n"
        "\\doublespacing\n"
        "\\usepackage{amsmath}\n"
        "\\usepackage{graphicx}\n"
        "\\usepackage{hyperref}\n"
        "\\usepackage{float}\n"
        "\\usepackage{natbib}\n"
        "\\usepackage{caption}\n"
        "\\usepackage[utf8]{inputenc}\n"
        "\\usepackage[T1]{fontenc}\n"
        "\\usepackage{indentfirst}\n"
        "\\setlength{\\parindent}{0.5in}\n"
    ),
    "mla": (
        "\\documentclass[12pt]{article}\n"
        "\\usepackage[margin=1in]{geometry}\n"
        "\\usepackage{times}\n"
        "\\usepackage{setspace}\n"
        "\\doublespacing\n"
        "\\usepackage{amsmath}\n"
        "\\usepackage{graphicx}\n"
        "\\usepackage{hyperref}\n"
        "\\usepackage{float}\n"
        "\\usepackage[utf8]{inputenc}\n"
        "\\usepackage[T1]{fontenc}\n"
        "\\usepackage{indentfirst}\n"
        "\\setlength{\\parindent}{0.5in}\n"
    ),
    "chicago": (
        "\\documentclass[12pt]{article}\n"
        "\\usepackage[margin=1in]{geometry}\n"
        "\\usepackage{times}\n"
        "\\usepackage{setspace}\n"
        "\\doublespacing\n"
        "\\usepackage{amsmath}\n"
        "\\usepackage{graphicx}\n"
        "\\usepackage{hyperref}\n"
        "\\usepackage{float}\n"
        "\\usepackage{caption}\n"
        "\\usepackage[utf8]{inputenc}\n"
        "\\usepackage[T1]{fontenc}\n"
        "\\usepackage{indentfirst}\n"
        "\\setlength{\\parindent}{0.5in}\n"
    ),
    "vancouver": (
        "\\documentclass[12pt]{article}\n"
        "\\usepackage[margin=1in]{geometry}\n"
        "\\usepackage{times}\n"
        "\\usepackage{setspace}\n"
        "\\doublespacing\n"
        "\\usepackage{amsmath}\n"
        "\\usepackage{graphicx}\n"
        "\\usepackage{hyperref}\n"
        "\\usepackage{float}\n"
        "\\usepackage{caption}\n"
        "\\usepackage[utf8]{inputenc}\n"
        "\\usepackage[T1]{fontenc}\n"
    ),
}

_DEFAULT_PREAMBLE = (
    "\\documentclass[12pt]{article}\n"
    "\\usepackage[margin=1in]{geometry}\n"
    "\\usepackage{amsmath}\n"
    "\\usepackage{amssymb}\n"
    "\\usepackage{graphicx}\n"
    "\\usepackage{hyperref}\n"
    "\\usepackage{float}\n"
    "\\usepackage{caption}\n"
    "\\usepackage{natbib}\n"
    "\\usepackage{times}\n"
    "\\usepackage[utf8]{inputenc}\n"
    "\\usepackage[T1]{fontenc}\n"
)


def _build_preamble(style: str) -> str:
    """Return a style-specific LaTeX preamble (everything before \\begin{document})."""
    return _PREAMBLE_MAP.get(style.lower(), _DEFAULT_PREAMBLE)


# ---------------------------------------------------------------------------
# LaTeX post-processor — fixes common LLM mistakes
# ---------------------------------------------------------------------------

def _postprocess_latex(body: str, style: str) -> str:
    """Clean up the merged LaTeX body before wrapping in preamble + document env."""

    # 1. Remove empty abstract environments  (LLM sometimes emits empty ones)
    body = re.sub(r"\\begin\{abstract\}\s*\\end\{abstract\}", "", body)

    # 2. Convert \section{Abstract} → proper \begin{abstract}...\end{abstract}
    def _replace_abstract_section(m: re.Match) -> str:
        content = m.group(1).strip()
        if not content:
            return ""
        return f"\\begin{{abstract}}\n{content}\n\\end{{abstract}}"

    body = re.sub(
        r"\\section\*?\{Abstract\}\s*\n(.*?)(?=\\section(?:\*?\{)|\\begin\{thebibliography\}|$)",
        _replace_abstract_section,
        body,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # 3. Remove duplicate \maketitle
    count = body.count("\\maketitle")
    if count > 1:
        first = True
        def _keep_first(m: re.Match) -> str:
            nonlocal first
            if first:
                first = False
                return m.group(0)
            return ""
        body = re.sub(r"\\maketitle", _keep_first, body)

    # 4. Fix leftover markdown artefacts the LLM may emit
    body = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", body)
    body = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\\textit{\1}", body)

    # 5. Remove stray inner \begin{document} / \end{document}
    body = body.replace("\\begin{document}", "").replace("\\end{document}", "")

    # 6. Remove duplicate \title{} (keep first)
    titles = list(re.finditer(r"\\title\{", body))
    if len(titles) > 1:
        # keep first, remove rest
        for m in reversed(titles[1:]):
            # find closing brace
            depth = 0
            start = m.start()
            for i in range(start, len(body)):
                if body[i] == "{":
                    depth += 1
                elif body[i] == "}":
                    depth -= 1
                    if depth == 0:
                        body = body[:start] + body[i + 1:]
                        break

    # 7. Normalize multiple consecutive blank lines → max 2
    body = re.sub(r"\n{4,}", "\n\n\n", body)

    # 8. IEEE-specific: ensure \IEEEkeywords for Index Terms
    if style.lower() == "ieee":
        # Convert plain "Index Terms—..." paragraph into proper environment
        body = re.sub(
            r"(?m)^\\textit\{Index Terms\}[—–-]+\s*(.+)$",
            r"\\begin{IEEEkeywords}\n\1\n\\end{IEEEkeywords}",
            body,
        )

    # 9. Fix unescaped special chars in text (common LLM mistake)
    # Only fix & that isn't already in a tabular/align env context
    # This is tricky — skip for now to avoid false positives

    # 10. Remove any trailing \bibliography{} or \bibliographystyle{} (we use thebibliography)
    body = re.sub(r"\\bibliography\{[^}]*\}", "", body)
    body = re.sub(r"\\bibliographystyle\{[^}]*\}", "", body)

    return body.strip()


# ---------------------------------------------------------------------------
# Unified pipeline endpoint
# ---------------------------------------------------------------------------

@agno_router.post(
    "/api/v2/pipeline/stream",
    summary="Full pipeline: Static Format → LLM LaTeX (SSE)",
)
async def pipeline_stream(
    file: UploadFile = File(...),
    style: str = Form("apa7"),
    model: str = Form("llama-3.3-70b-versatile"),
):
    """
    Full FormatForge pipeline via Server-Sent Events:
      Stage 1 — Static formatting engine (6-agent Orchestrator)
      Stage 2 — LLM-based LaTeX generation (Agno + Groq)
    """
    api_key = os.environ.get("GROQ_API_KEY")
    filename = (file.filename or "upload.docx").lower()

    if not (filename.endswith(".docx") or filename.endswith(".pdf")):
        raise HTTPException(status_code=400, detail="Unsupported format. Upload .docx or .pdf.")

    file_bytes = await file.read()

    suffix = Path(filename).suffix
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(file_bytes)
    tmp.close()
    tmp_path = Path(tmp.name)

    async def sse_generator():
        formatted_path: Path | None = None
        try:
            # ══════════════════════════════════════════════════════
            # STAGE 1 — Static Formatting Engine (Orchestrator)
            # ══════════════════════════════════════════════════════
            yield _sse({"stage": 1, "log": "🔧 Starting static formatting engine..."})
            yield _sse({"stage": 1, "log": f"Style: {style} | File: {file.filename}"})
            await asyncio.sleep(0.05)

            from backend.agents.orchestrator import Orchestrator

            yield _sse({"stage": 1, "log": "Step 1/6 — Ingesting document..."})
            orchestrator = Orchestrator()

            result = await orchestrator.run(input_path=tmp_path, style_id=style)

            if not result.success:
                yield _sse({"error": f"Static formatting failed: {result.error_message}"})
                return

            formatted_path = Path(result.output_filename)

            yield _sse({"stage": 1, "log": "Step 2/6 — Style spec loaded"})
            yield _sse({"stage": 1, "log": "Step 3/6 — Document structure detected"})

            if result.structure_summary:
                summary_str = ", ".join(f"{k}: {v}" for k, v in result.structure_summary.items())
                yield _sse({"stage": 1, "log": f"Structure: {summary_str}"})

            yield _sse({"stage": 1, "log": "Step 4/6 — Citations processed"})
            yield _sse({"stage": 1, "log": "Step 5/6 — Formatting applied"})
            yield _sse({"stage": 1, "log": "Step 6/6 — Compliance validated"})

            if result.compliance_report:
                cr = result.compliance_report
                yield _sse({
                    "stage": 1,
                    "log": f"✅ Static formatting complete — Score: {cr.overall_score}% | "
                           f"Time: {result.processing_time_seconds}s",
                    "compliance_score": cr.overall_score,
                    "processing_time": result.processing_time_seconds,
                })

            yield _sse({
                "stage": 1,
                "log": "📄 Formatted document saved.",
                "formatted_file": formatted_path.name if formatted_path else None,
                "stage_complete": 1,
            })

            # Copy formatted file to MCP documents directory for agent editing
            try:
                from backend.config import PROJECT_ROOT
                mcp_docs_dir = PROJECT_ROOT / "documents"
                mcp_docs_dir.mkdir(parents=True, exist_ok=True)
                dest = mcp_docs_dir / formatted_path.name
                shutil.copy2(str(formatted_path), str(dest))
                yield _sse({"stage": 1, "log": f"📂 Copied to agent documents: {formatted_path.name}"})
            except Exception as copy_err:
                logger.warning(f"Could not copy to MCP documents: {copy_err}")

            # ══════════════════════════════════════════════════════
            # STAGE 2 — LLM LaTeX Generation (Chunked)
            # ══════════════════════════════════════════════════════

            if not _AGNO_READY or not api_key:
                yield _sse({
                    "stage": 2,
                    "log": "⚠️ LLM LaTeX generation skipped (Agno/Groq not available).",
                    "is_final": True,
                    "latex": "",
                    "formatted_file": formatted_path.name if formatted_path else None,
                })
                return

            yield _sse({"stage": 2, "log": "🧠 Starting LLM-based LaTeX generation..."})
            await asyncio.sleep(0.05)

            yield _sse({"stage": 2, "log": "Extracting text from formatted document..."})
            try:
                formatted_text = _extract_from_docx(formatted_path)
            except Exception as e:
                yield _sse({"error": f"Failed to read formatted document: {e}"})
                return

            if not formatted_text.strip():
                yield _sse({"error": "Formatted document is empty — cannot generate LaTeX."})
                return

            word_count = len(formatted_text.split())
            yield _sse({"stage": 2, "log": f"Extracted {word_count} words from formatted document."})

            # ── Split into sections for chunked generation ──
            sections = _split_into_sections(formatted_text)
            yield _sse({"stage": 2, "log": f"Split document into {len(sections)} sections for chunked LaTeX generation."})

            latex_agent = Agent(
                name="LaTeXConverterAgent",
                model=AgnoGroq(id=model, api_key=api_key),
                instructions=(
                    f"You are an expert LaTeX code generator for {style.upper()} academic manuscripts.\n"
                    f"You will receive ONE SECTION of a manuscript at a time.\n"
                    f"Convert it into LaTeX body content ONLY.\n\n"
                    f"RULES:\n"
                    f"1. Output ONLY LaTeX body content — NO \\documentclass, NO \\usepackage, NO \\begin{{document}}, NO \\end{{document}}.\n"
                    f"2. Use \\section{{}}, \\subsection{{}}, \\subsubsection{{}} for headings.\n"
                    f"3. Convert citations to \\cite{{author_year}} format.\n"
                    f"4. Preserve EVERY paragraph, EVERY sentence, EVERY detail. Do NOT summarize.\n"
                    f"5. For figure/table descriptions, use \\begin{{figure}}[H]...\\end{{figure}} or \\begin{{table}}[H]...\\end{{table}}.\n"
                    f"6. Use proper LaTeX for math: $...$ for inline, $$...$$ for display.\n"
                    f"7. Use \\textit{{}} for species names, \\textbf{{}} for emphasis.\n"
                    f"8. Return ONLY raw LaTeX code. NO markdown fences. NO explanations.\n"
                    f"9. Do NOT skip or truncate ANY content. Every word matters.\n"
                ),
                markdown=False,
            )

            # ── Generate LaTeX for each section ──
            body_parts: list[str] = []
            preamble_section = None

            for idx, section in enumerate(sections):
                sec_title = section["title"]
                sec_content = section["content"]
                sec_words = len(sec_content.split())

                yield _sse({"stage": 2, "log": f"Chunk {idx+1}/{len(sections)}: {sec_title} ({sec_words} words)..."})

                # For the first section (Preamble), generate title/author/abstract
                if idx == 0 and sec_title == "Preamble":
                    chunk_prompt = (
                        f"Convert this manuscript header section into LaTeX code.\n"
                        f"Include: \\title{{}}, \\author{{}}, \\maketitle, and \\begin{{abstract}}...\\end{{abstract}} if abstract is present.\n"
                        f"Do NOT output \\documentclass or \\usepackage or \\begin{{document}}.\n"
                        f"Preserve ALL text exactly.\n\n"
                        f"--- SECTION ---\n{sec_content}\n--- END ---\n"
                    )
                elif "reference" in sec_title.lower():
                    chunk_prompt = (
                        f"Convert this references section into LaTeX \\begin{{thebibliography}} format.\n"
                        f"Use \\bibitem{{key}} for each reference. Preserve ALL references.\n"
                        f"Do NOT output \\documentclass or \\usepackage.\n\n"
                        f"--- REFERENCES ---\n{sec_content}\n--- END ---\n"
                    )
                else:
                    chunk_prompt = (
                        f"Convert this section into LaTeX body content.\n"
                        f"Section heading: {sec_title}\n"
                        f"Use \\section{{{sec_title}}} at the start (unless already a subsection).\n"
                        f"Do NOT output \\documentclass, \\usepackage, \\begin{{document}}, or \\end{{document}}.\n"
                        f"Preserve EVERY paragraph exactly. Do NOT summarize or skip.\n\n"
                        f"--- SECTION ---\n{sec_content}\n--- END ---\n"
                    )

                try:
                    chunk_result = await asyncio.to_thread(latex_agent.run, chunk_prompt)
                    chunk_latex = _clean_chunk_latex(chunk_result.content)
                    body_parts.append(chunk_latex)
                    yield _sse({"stage": 2, "log": f"  ✓ Chunk {idx+1} complete ({len(chunk_latex)} chars)"})
                except Exception as e:
                    logger.warning(f"Chunk {idx+1} ({sec_title}) failed: {e}")
                    yield _sse({"stage": 2, "log": f"  ⚠ Chunk {idx+1} failed: {str(e)[:80]}, using raw text fallback"})
                    # Fallback: wrap raw text in LaTeX
                    escaped = sec_content.replace("&", "\\&").replace("%", "\\%").replace("#", "\\#").replace("_", "\\_")
                    body_parts.append(f"\\section{{{sec_title}}}\n\n{escaped}")

                await asyncio.sleep(0.1)  # Rate limit between Groq calls

            # ── Assemble final LaTeX document ──
            yield _sse({"stage": 2, "log": "Assembling final LaTeX document from all chunks..."})

            merged_body = "\n\n".join(body_parts)

            # Post-process: fix LLM mistakes (empty abstracts, markdown, duplicates)
            yield _sse({"stage": 2, "log": "Post-processing LaTeX (fixing LLM artifacts)..."})
            merged_body = _postprocess_latex(merged_body, style)

            # Style-specific preamble
            preamble = _build_preamble(style)

            merged_latex = (
                f"{preamble}\n"
                "\\begin{document}\n\n"
                f"{merged_body}\n\n"
                "\\end{document}\n"
            )

            yield _sse({"stage": 2, "log": f"✅ LaTeX generation complete! ({len(merged_latex)} chars, {len(merged_latex.split(chr(10)))} lines)"})

            yield _sse({
                "is_final": True,
                "latex": merged_latex,
                "formatted_file": formatted_path.name if formatted_path else None,
            })

        except Exception as e:
            logger.exception("Pipeline error: %s", e)
            yield _sse({"error": str(e)})

        finally:
            tmp_path.unlink(missing_ok=True)

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# Download formatted file
# ---------------------------------------------------------------------------

@agno_router.get("/api/v2/download/{filename}")
async def download_formatted(filename: str):
    """Download the statically formatted .docx file."""
    from backend.config import OUTPUT_FORMATTED_DIR

    file_path = OUTPUT_FORMATTED_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        str(file_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
    )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@agno_router.get("/api/v2/health")
async def agno_health():
    return {
        "agno_available": _AGNO_READY,
        "groq_key_set": bool(os.environ.get("GROQ_API_KEY")),
    }
