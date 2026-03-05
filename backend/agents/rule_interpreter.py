"""
FormatForge AI — Agent 2: Rule Interpreter
Converts style guideline text → StyleSpec JSON using LLM.
Also loads hardcoded StyleSpec files as ground truth.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from backend.config import STYLES_DIR
from backend.schemas.style_spec import StyleSpec

logger = logging.getLogger(__name__)


class RuleInterpreterAgent:
    """Agent 2 — Interpret formatting rules from guidelines or load hardcoded specs."""

    # ── Hardcoded style file map ─────────────────────────────

    STYLE_FILES: dict[str, str] = {
        "apa7": "apa7.json",
        "vancouver": "vancouver.json",
        "ieee": "ieee.json",
    }

    # ── Public API ───────────────────────────────────────────

    def get_style_spec(
        self,
        style_id: str = "apa7",
        guidelines_text: Optional[str] = None,
    ) -> StyleSpec:
        """
        Get a StyleSpec by id or by interpreting raw guideline text.

        Args:
            style_id: Identifier for a hardcoded style (e.g. "apa7").
            guidelines_text: If provided, use LLM to extract rules from this text.

        Returns:
            A validated StyleSpec object.
        """
        # If raw guidelines text is given, use LLM to interpret
        if guidelines_text and guidelines_text.strip():
            logger.info("Interpreting custom guideline text with LLM…")
            return self._interpret_with_llm(guidelines_text, style_id)

        # Otherwise, load hardcoded file
        return self._load_hardcoded(style_id)

    # ── Load hardcoded StyleSpec ─────────────────────────────

    def _load_hardcoded(self, style_id: str) -> StyleSpec:
        """Load a pre-built StyleSpec JSON from the styles/ directory."""
        filename = self.STYLE_FILES.get(style_id)
        if not filename:
            logger.warning("Unknown style_id '%s' — falling back to apa7.", style_id)
            filename = "apa7.json"

        path = STYLES_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"Style file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        spec = StyleSpec.model_validate(data)
        logger.info("Loaded hardcoded StyleSpec: %s (%s)", spec.style_name, path.name)
        return spec

    # ── LLM-based interpretation (Phase 4) ───────────────────

    def _interpret_with_llm(self, guidelines_text: str, style_hint: str = "") -> StyleSpec:
        """
        Use LLM to extract formatting rules from raw guideline text.

        Falls back to hardcoded APA 7 if LLM output is invalid.
        """
        # TODO: Implement in Phase 4
        #   1. Chunk guidelines_text if too long
        #   2. Send to LLM with RULE_INTERPRETER_SYSTEM/USER prompts
        #   3. Parse JSON response into StyleSpec
        #   4. Validate with Pydantic; fall back to hardcoded if invalid

        from backend.llm.client import get_llm_client
        from backend.llm.prompts import RULE_INTERPRETER_SYSTEM, RULE_INTERPRETER_USER

        try:
            client = get_llm_client()
            user_prompt = RULE_INTERPRETER_USER.format(
                style_name=style_hint or "Custom Style",
                guideline_text=guidelines_text[:8000],  # truncate for token limit
            )
            data = client.chat_json(
                system_prompt=RULE_INTERPRETER_SYSTEM,
                user_prompt=user_prompt,
            )
            spec = StyleSpec.model_validate(data)
            logger.info("LLM-extracted StyleSpec: %s", spec.style_name)
            return spec

        except Exception as exc:
            logger.error("LLM interpretation failed (%s) — falling back to APA 7.", exc)
            return self._load_hardcoded("apa7")
