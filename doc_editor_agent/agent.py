"""
agent.py — Agno Agent definition (importable module)
=====================================================

Provides `create_agent()` factory and a `get_agent()` singleton helper.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

log = logging.getLogger("doc_editor_agent")

# Load .env
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
if _ENV_FILE.exists():
    for line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


AGENT_INSTRUCTION = """\
You are **DocBot**, an intelligent Document Editor Agent for .docx files.

## RULES
1. **Read-only** tools — call immediately, no confirmation needed.
2. **Write/edit/delete** — describe what you will do, then execute. Report: Done.
3. `read_document` is **paginated**: returns 30 paragraphs at a time. Use `start` param to page.
4. Paragraph indices are **0-based** (P0, P1 …).
5. Color hex **without** '#' (e.g. "FF0000"). Table data / list items as JSON strings.
6. If user mentions `[Working on file: X]`, always use file X.
7. Be concise but helpful. Answer questions, summarise, suggest improvements.
"""

_agent = None


def create_agent(
    model_id: str = "llama-3.3-70b-versatile",
    db_file: str | None = None,
):
    """Create and return a fresh Agno Agent instance."""
    from agno.agent import Agent
    from agno.models.groq import Groq
    from agno.db.sqlite import SqliteDb
    from doc_editor_agent.doc_tools import ALL_TOOLS

    if db_file is None:
        db_file = str(Path(__file__).resolve().parent.parent / "agent_sessions.db")

    agent_db = SqliteDb(db_file=db_file)

    return Agent(
        name="DocBot",
        model=Groq(id=model_id),
        db=agent_db,
        add_history_to_context=True,
        num_history_runs=3,
        store_tool_messages=False,
        description=(
            "DocBot — an intelligent document assistant that can read, discuss, "
            "summarise, question-answer, edit, and format .docx files via "
            "natural-language prompts."
        ),
        instructions=AGENT_INSTRUCTION,
        tools=ALL_TOOLS,
        markdown=True,
    )


def get_agent():
    """Singleton accessor — creates the agent on first call, reuses afterwards."""
    global _agent
    if _agent is None:
        _agent = create_agent()
    return _agent
