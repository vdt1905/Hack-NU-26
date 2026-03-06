"""
MCP Server — Document Editor (standalone)
==========================================

A standalone MCP Server using FastMCP that exposes all document editing tools
over stdio transport. Can be imported by api.py or run directly.

Usage:
    python -m mcp_server.server       (stdio transport)
    python api.py --mcp               (stdio via unified API)
"""

from __future__ import annotations

import json
import logging
import os
import re
from copy import deepcopy
from pathlib import Path
from typing import Optional

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor
from mcp.server.fastmcp import FastMCP

# ── Logging ──────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("mcp_server")

# ── Load .env ────────────────────────────────────────────────────────────
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
if _ENV_FILE.exists():
    for line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

# ── Paths ────────────────────────────────────────────────────────────────
DOCUMENTS_DIR = Path(__file__).resolve().parent.parent / "documents"
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("DOCUMENTS_DIR", str(DOCUMENTS_DIR))

# ── Helpers ──────────────────────────────────────────────────────────────

ALIGNMENT_MAP = {
    "left": WD_ALIGN_PARAGRAPH.LEFT,
    "center": WD_ALIGN_PARAGRAPH.CENTER,
    "right": WD_ALIGN_PARAGRAPH.RIGHT,
    "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
}

HIGHLIGHT_MAP = {
    "yellow": WD_COLOR_INDEX.YELLOW,
    "green": WD_COLOR_INDEX.BRIGHT_GREEN,
    "pink": WD_COLOR_INDEX.PINK,
    "blue": WD_COLOR_INDEX.BLUE,
    "red": WD_COLOR_INDEX.RED,
    "turquoise": WD_COLOR_INDEX.TURQUOISE,
    "gray": WD_COLOR_INDEX.GRAY_25,
}


def _resolve(filename: str) -> Path:
    return DOCUMENTS_DIR / Path(filename).name


def _load(filename: str) -> Document:
    path = _resolve(filename)
    if not path.exists():
        raise FileNotFoundError(f"Document '{filename}' not found.")
    return Document(str(path))


def _save(doc: Document, filename: str) -> Path:
    path = _resolve(filename)
    doc.save(str(path))
    return path


def _apply_run_format(run, *, bold=None, italic=None, underline=None,
                      strikethrough=None, font_size=None, font_name=None,
                      font_color=None, highlight_color=None):
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if underline is not None:
        run.underline = underline
    if strikethrough is not None:
        run.font.strike = strikethrough
    if font_size is not None:
        run.font.size = Pt(font_size)
    if font_name is not None:
        run.font.name = font_name
    if font_color is not None:
        run.font.color.rgb = RGBColor.from_string(font_color.lstrip("#"))
    if highlight_color is not None:
        hl = HIGHLIGHT_MAP.get(highlight_color.lower())
        if hl:
            run.font.highlight_color = hl


def _set_run_text(r_elem, text: str):
    for t in r_elem.findall(qn("w:t")):
        r_elem.remove(t)
    t_elem = OxmlElement("w:t")
    t_elem.text = text
    if text and (text[0] == " " or text[-1] == " "):
        t_elem.set(qn("xml:space"), "preserve")
    r_elem.append(t_elem)


def _format_matching_text(paragraph, search_text: str, **fmt) -> bool:
    full_text = paragraph.text
    idx = full_text.find(search_text)
    if idx == -1:
        return False
    target_end = idx + len(search_text)
    p_elem = paragraph._p
    runs = list(paragraph.runs)
    boundaries: list[tuple] = []
    pos = 0
    for run in runs:
        rlen = len(run.text)
        boundaries.append((pos, pos + rlen, run))
        pos += rlen
    new_elements: list[tuple] = []
    for run_start, run_end, run in boundaries:
        overlap_start = max(run_start, idx)
        overlap_end = min(run_end, target_end)
        if overlap_start >= overlap_end:
            new_elements.append(("keep", run._r))
            continue
        if run_start < overlap_start:
            before_r = deepcopy(run._r)
            _set_run_text(before_r, run.text[: overlap_start - run_start])
            new_elements.append(("keep", before_r))
        target_r = deepcopy(run._r)
        _set_run_text(target_r, run.text[overlap_start - run_start: overlap_end - run_start])
        new_elements.append(("format", target_r))
        if overlap_end < run_end:
            after_r = deepcopy(run._r)
            _set_run_text(after_r, run.text[overlap_end - run_start:])
            new_elements.append(("keep", after_r))
    for run in runs:
        p_elem.remove(run._r)
    for action, r_elem in new_elements:
        p_elem.append(r_elem)
        if action == "format":
            from docx.text.run import Run
            temp_run = Run(r_elem, paragraph)
            _apply_run_format(temp_run, **fmt)
    return True


# ═════════════════════════════════════════════════════════════════════════
#  MCP SERVER
# ═════════════════════════════════════════════════════════════════════════

mcp = FastMCP(
    "Document Editor",
    instructions=(
        "A local document editing server. Manages .docx files stored in "
        f"'{DOCUMENTS_DIR}'. Supports create, read, edit, format, search, "
        "and export operations."
    ),
)


@mcp.tool()
def list_documents() -> str:
    """List all .docx documents in the document store. Returns JSON array."""
    docs = []
    for f in sorted(DOCUMENTS_DIR.glob("*.docx")):
        stat = f.stat()
        docs.append({"filename": f.name, "size_bytes": stat.st_size, "modified": stat.st_mtime})
    return json.dumps(docs, indent=2)


@mcp.tool()
def create_document(title: str) -> str:
    """Create a new blank .docx document with the given title as filename and first heading."""
    safe_title = re.sub(r'[<>:"/\\|?*]', "_", title)
    filename = f"{safe_title}.docx"
    doc = Document()
    doc.add_heading(title, level=1)
    _save(doc, filename)
    return json.dumps({"filename": filename, "message": f"Document '{title}' created."})


@mcp.tool()
def delete_document(filename: str) -> str:
    """Permanently delete a document from the store."""
    path = _resolve(filename)
    if not path.exists():
        return json.dumps({"error": f"Document '{filename}' not found."})
    path.unlink()
    return json.dumps({"message": f"Document '{filename}' deleted."})


@mcp.tool()
def get_document_info(filename: str) -> str:
    """Get metadata about a document: paragraph count, word count, styles used, table count."""
    doc = _load(filename)
    paras = doc.paragraphs
    word_count = sum(len(p.text.split()) for p in paras)
    styles_used = list({p.style.name for p in paras if p.style})
    return json.dumps({
        "filename": filename,
        "paragraph_count": len(paras),
        "word_count": word_count,
        "table_count": len(doc.tables),
        "styles_used": sorted(styles_used),
    }, indent=2)


@mcp.tool()
def duplicate_document(filename: str, new_filename: str) -> str:
    """Create a copy of a document with a new filename."""
    doc = _load(filename)
    _save(doc, new_filename)
    return json.dumps({"message": f"Document copied to '{new_filename}'."})


@mcp.tool()
def read_document(filename: str) -> str:
    """Read entire document content. Each paragraph prefixed with [P<index>|<style>]."""
    doc = _load(filename)
    lines: list[str] = []
    for i, para in enumerate(doc.paragraphs):
        style = para.style.name if para.style else "Normal"
        lines.append(f"[P{i}|{style}] {para.text}")
    return "\n".join(lines)


@mcp.tool()
def read_paragraph(filename: str, paragraph_index: int) -> str:
    """Read a single paragraph by 0-based index. Returns text, style, alignment."""
    doc = _load(filename)
    paras = doc.paragraphs
    if paragraph_index < 0 or paragraph_index >= len(paras):
        return json.dumps({"error": f"Index {paragraph_index} out of range (0-{len(paras)-1})."})
    p = paras[paragraph_index]
    return json.dumps({
        "index": paragraph_index,
        "style": p.style.name if p.style else "Normal",
        "text": p.text,
        "alignment": str(p.alignment) if p.alignment else "left",
    })


@mcp.tool()
def read_table(filename: str, table_index: int = 0) -> str:
    """Read a table by 0-based index. Returns a JSON 2D array of cell texts."""
    doc = _load(filename)
    tables = doc.tables
    if table_index < 0 or table_index >= len(tables):
        return json.dumps({"error": f"Table index {table_index} out of range (0-{len(tables)-1})."})
    table = tables[table_index]
    data = [[cell.text for cell in row.cells] for row in table.rows]
    return json.dumps({"table_index": table_index, "rows": len(table.rows),
                        "cols": len(table.columns), "data": data}, indent=2)


@mcp.tool()
def search_text(filename: str, query: str, case_sensitive: bool = False) -> str:
    """Search for text in a document. Returns matching paragraphs with indices."""
    doc = _load(filename)
    results = []
    for i, p in enumerate(doc.paragraphs):
        text = p.text
        q = query if case_sensitive else query.lower()
        t = text if case_sensitive else text.lower()
        if q in t:
            results.append({"paragraph_index": i, "style": p.style.name, "text": text})
    return json.dumps({"query": query, "matches": len(results), "results": results}, indent=2)


@mcp.tool()
def search_and_replace(filename: str, find_text: str, replace_with: str,
                       case_sensitive: bool = False) -> str:
    """Find and replace all occurrences of text in the document."""
    doc = _load(filename)
    count = 0
    for para in doc.paragraphs:
        for run in para.runs:
            if case_sensitive:
                if find_text in run.text:
                    run.text = run.text.replace(find_text, replace_with)
                    count += 1
            else:
                if find_text.lower() in run.text.lower():
                    pattern = re.compile(re.escape(find_text), re.IGNORECASE)
                    count += len(pattern.findall(run.text))
                    run.text = pattern.sub(replace_with, run.text)
    _save(doc, filename)
    return json.dumps({"find": find_text, "replace_with": replace_with, "replacements": count})


@mcp.tool()
def add_paragraph(filename: str, text: str, style: str = "Normal") -> str:
    """Append a new paragraph at the end. Styles: Normal, Heading 1-4, List Bullet, etc."""
    doc = _load(filename)
    doc.add_paragraph(text, style=style)
    _save(doc, filename)
    idx = len(doc.paragraphs) - 1
    return json.dumps({"message": f"Paragraph added at index {idx}.", "index": idx, "style": style})


@mcp.tool()
def insert_paragraph_after(filename: str, text: str, after_index: int,
                           style: str = "Normal") -> str:
    """Insert a new paragraph after the paragraph at the given 0-based index."""
    doc = _load(filename)
    paras = doc.paragraphs
    if after_index < 0 or after_index >= len(paras):
        return json.dumps({"error": f"Index {after_index} out of range."})
    ref_para = paras[after_index]
    new_p = OxmlElement("w:p")
    ref_para._p.addnext(new_p)
    from docx.text.paragraph import Paragraph
    new_para = Paragraph(new_p, doc)
    new_para.style = style
    new_para.add_run(text)
    _save(doc, filename)
    return json.dumps({"message": f"Paragraph inserted after index {after_index}.",
                        "new_index": after_index + 1})


@mcp.tool()
def delete_paragraph(filename: str, paragraph_index: int) -> str:
    """Delete the paragraph at the given 0-based index."""
    doc = _load(filename)
    paras = doc.paragraphs
    if paragraph_index < 0 or paragraph_index >= len(paras):
        return json.dumps({"error": f"Index {paragraph_index} out of range."})
    p_elem = paras[paragraph_index]._p
    p_elem.getparent().remove(p_elem)
    _save(doc, filename)
    return json.dumps({"message": f"Paragraph {paragraph_index} deleted."})


@mcp.tool()
def edit_paragraph_text(filename: str, paragraph_index: int, new_text: str) -> str:
    """Replace the entire text of a paragraph while keeping its style."""
    doc = _load(filename)
    paras = doc.paragraphs
    if paragraph_index < 0 or paragraph_index >= len(paras):
        return json.dumps({"error": f"Index {paragraph_index} out of range."})
    para = paras[paragraph_index]
    for run in para.runs:
        run.text = ""
    if para.runs:
        para.runs[0].text = new_text
    else:
        para.add_run(new_text)
    _save(doc, filename)
    return json.dumps({"message": f"Paragraph {paragraph_index} text updated."})


@mcp.tool()
def add_heading(filename: str, text: str, level: int = 1) -> str:
    """Add a heading (level 1-4) at the end of the document."""
    if level < 1 or level > 4:
        return json.dumps({"error": "Heading level must be 1-4."})
    doc = _load(filename)
    doc.add_heading(text, level=level)
    _save(doc, filename)
    idx = len(doc.paragraphs) - 1
    return json.dumps({"message": f"Heading {level} added at index {idx}.", "index": idx})


@mcp.tool()
def add_page_break(filename: str) -> str:
    """Add a page break at the end of the document."""
    doc = _load(filename)
    doc.add_page_break()
    _save(doc, filename)
    return json.dumps({"message": "Page break added."})


@mcp.tool()
def add_table(filename: str, rows: int, cols: int, data: str | None = None) -> str:
    """Add a table at the end. Optional data is a JSON 2D array e.g. '[["A","B"],["1","2"]]'."""
    doc = _load(filename)
    table = doc.add_table(rows=rows, cols=cols, style="Table Grid")
    if data:
        try:
            cell_data = json.loads(data)
            for r, row_data in enumerate(cell_data):
                for c, val in enumerate(row_data):
                    if r < rows and c < cols:
                        table.cell(r, c).text = str(val)
        except (json.JSONDecodeError, IndexError):
            pass
    _save(doc, filename)
    return json.dumps({"message": f"Table ({rows}x{cols}) added.",
                        "table_index": len(doc.tables) - 1})


@mcp.tool()
def add_bullet_list(filename: str, items: str) -> str:
    """Add a bullet list. items is a JSON array e.g. '["First", "Second"]'."""
    doc = _load(filename)
    try:
        item_list = json.loads(items)
    except json.JSONDecodeError:
        return json.dumps({"error": "items must be a JSON array of strings."})
    for item in item_list:
        doc.add_paragraph(str(item), style="List Bullet")
    _save(doc, filename)
    return json.dumps({"message": f"Bullet list with {len(item_list)} items added."})


@mcp.tool()
def add_numbered_list(filename: str, items: str) -> str:
    """Add a numbered list. items is a JSON array e.g. '["First", "Second"]'."""
    doc = _load(filename)
    try:
        item_list = json.loads(items)
    except json.JSONDecodeError:
        return json.dumps({"error": "items must be a JSON array of strings."})
    for item in item_list:
        doc.add_paragraph(str(item), style="List Number")
    _save(doc, filename)
    return json.dumps({"message": f"Numbered list with {len(item_list)} items added."})


@mcp.tool()
def format_text(
    filename: str, search_text: str,
    bold: bool | None = None, italic: bool | None = None,
    underline: bool | None = None, strikethrough: bool | None = None,
    font_size: float | None = None, font_name: str | None = None,
    font_color: str | None = None, highlight_color: str | None = None,
) -> str:
    """Apply formatting to ALL occurrences of search_text. Colors hex without '#'."""
    doc = _load(filename)
    fmt = {k: v for k, v in dict(
        bold=bold, italic=italic, underline=underline, strikethrough=strikethrough,
        font_size=font_size, font_name=font_name, font_color=font_color,
        highlight_color=highlight_color,
    ).items() if v is not None}
    count = 0
    for para in doc.paragraphs:
        if search_text in para.text:
            if _format_matching_text(para, search_text, **fmt):
                count += 1
    _save(doc, filename)
    return json.dumps({"search_text": search_text, "paragraphs_formatted": count,
                        "formatting_applied": list(fmt.keys())})


@mcp.tool()
def format_paragraph(
    filename: str, paragraph_index: int,
    bold: bool | None = None, italic: bool | None = None,
    underline: bool | None = None, strikethrough: bool | None = None,
    font_size: float | None = None, font_name: str | None = None,
    font_color: str | None = None, alignment: str | None = None,
    style: str | None = None,
) -> str:
    """Apply formatting to an entire paragraph. alignment: left/center/right/justify."""
    doc = _load(filename)
    paras = doc.paragraphs
    if paragraph_index < 0 or paragraph_index >= len(paras):
        return json.dumps({"error": f"Index {paragraph_index} out of range."})
    para = paras[paragraph_index]
    if alignment and alignment.lower() in ALIGNMENT_MAP:
        para.alignment = ALIGNMENT_MAP[alignment.lower()]
    if style:
        try:
            para.style = style
        except KeyError:
            return json.dumps({"error": f"Unknown style '{style}'."})
    fmt = {k: v for k, v in dict(
        bold=bold, italic=italic, underline=underline, strikethrough=strikethrough,
        font_size=font_size, font_name=font_name, font_color=font_color,
    ).items() if v is not None}
    if fmt:
        for run in para.runs:
            _apply_run_format(run, **fmt)
        if not para.runs and para.text:
            run = para.add_run(para.text)
            _apply_run_format(run, **fmt)
    _save(doc, filename)
    applied = list(fmt.keys())
    if alignment:
        applied.append("alignment")
    if style:
        applied.append("style")
    return json.dumps({"message": f"Paragraph {paragraph_index} formatted.",
                        "formatting_applied": applied})


@mcp.tool()
def set_paragraph_style(filename: str, paragraph_index: int, style: str) -> str:
    """Change paragraph style. Common: Normal, Heading 1-4, List Bullet, Quote, Title."""
    doc = _load(filename)
    paras = doc.paragraphs
    if paragraph_index < 0 or paragraph_index >= len(paras):
        return json.dumps({"error": f"Index {paragraph_index} out of range."})
    try:
        paras[paragraph_index].style = style
    except KeyError:
        return json.dumps({"error": f"Unknown style '{style}'."})
    _save(doc, filename)
    return json.dumps({"message": f"Paragraph {paragraph_index} style set to '{style}'."})


@mcp.tool()
def set_paragraph_alignment(filename: str, paragraph_index: int, alignment: str) -> str:
    """Set paragraph alignment: left, center, right, or justify."""
    doc = _load(filename)
    paras = doc.paragraphs
    if paragraph_index < 0 or paragraph_index >= len(paras):
        return json.dumps({"error": f"Index {paragraph_index} out of range."})
    a = ALIGNMENT_MAP.get(alignment.lower())
    if a is None:
        return json.dumps({"error": f"Unknown alignment '{alignment}'. Use left/center/right/justify."})
    paras[paragraph_index].alignment = a
    _save(doc, filename)
    return json.dumps({"message": f"Paragraph {paragraph_index} alignment set to '{alignment}'."})


@mcp.tool()
def export_to_text(filename: str) -> str:
    """Export the document as plain text (no formatting)."""
    doc = _load(filename)
    return "\n".join(p.text for p in doc.paragraphs)


# ═════════════════════════════════════════════════════════════════════════
#  ENTRY POINT — run MCP on stdio when invoked directly
# ═════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    log.info("Starting MCP Server — Document Editor (stdio transport)…")
    mcp.run(transport="stdio")
