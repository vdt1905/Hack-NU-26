"""
FormatForge AI — Agent 2: Rule Interpreter  (Phase 4 — Full Implementation)
Converts style guideline text / URL → StyleSpec JSON using LLM.
Also loads hardcoded StyleSpec files as ground truth.

Capabilities:
  • Fetch style guide from URL (with HTML extraction)
  • Accept raw guideline text
  • Chunk long guidelines for LLM token limits
  • Multi-pass LLM extraction (main pass + optional refinement)
  • Pydantic schema validation with detailed error handling
  • Graceful fallback to hardcoded specs on failure
  • Merge partial LLM output with defaults so no field is ever missing
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from backend.config import STYLES_DIR
from backend.schemas.style_spec import StyleSpec

logger = logging.getLogger(__name__)

# Maximum characters per LLM chunk (conservative for ~4 K tokens)
_MAX_CHUNK_CHARS = 6000
# Maximum total characters we will send even after chunking
_MAX_TOTAL_CHARS = 24000


# ── Utility helpers ──────────────────────────────────────────


def _fetch_url_text(url: str, timeout: int = 15) -> str:
    """
    Fetch a URL and return the visible text content.
    Uses ``requests`` + ``BeautifulSoup`` when available;
    falls back to ``urllib`` if bs4 is not installed.
    """
    import urllib.request
    import urllib.error

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }

    try:
        # Try with requests + bs4 first
        import requests as req_lib  # type: ignore
        from bs4 import BeautifulSoup  # type: ignore

        resp = req_lib.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove scripts, styles, nav, footer
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)

    except ImportError:
        # Fallback to urllib (no HTML parsing — raw text)
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp_obj:
            raw = resp_obj.read().decode("utf-8", errors="replace")
        # Crude tag stripping
        text = re.sub(r"<[^>]+>", " ", raw)
        text = re.sub(r"\s+", " ", text).strip()

    logger.info("Fetched %d characters from %s", len(text), url)
    return text


def _clean_text(text: str) -> str:
    """Normalise whitespace and strip visual decorations."""
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[═─━]{5,}", "", text)
    return text.strip()


def _chunk_text(text: str, max_chars: int = _MAX_CHUNK_CHARS) -> list[str]:
    """
    Split *text* into chunks of at most *max_chars* characters,
    trying to break on paragraph boundaries.
    """
    text = text[:_MAX_TOTAL_CHARS]
    if len(text) <= max_chars:
        return [text]

    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 2 > max_chars:
            if current:
                chunks.append(current.strip())
            current = para
        else:
            current = current + "\n\n" + para if current else para
    if current.strip():
        chunks.append(current.strip())
    return chunks


def _deep_merge(base: dict, override: dict) -> dict:
    """
    Recursively merge *override* into *base*.
    Only non-None leaf values from *override* replace *base*.
    """
    merged = dict(base)
    for key, val in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(val, dict):
            merged[key] = _deep_merge(merged[key], val)
        elif val is not None:
            merged[key] = val
    return merged


# ══════════════════════════════════════════════════════════════


class RuleInterpreterAgent:
    """Agent 2 — Interpret formatting rules from guidelines or load hardcoded specs."""

    # ── Hardcoded style file map ─────────────────────────────

    STYLE_FILES: dict[str, str] = {
        "apa7": "apa7.json",
        "vancouver": "vancouver.json",
        "ieee": "ieee.json",
        "mla": "mla.json",
        "chicago": "chicago.json",
    }

    # ── Public API ───────────────────────────────────────────

    def get_style_spec(
        self,
        style_id: str = "apa7",
        guidelines_text: Optional[str] = None,
        guidelines_url: Optional[str] = None,
    ) -> StyleSpec:
        """
        Get a StyleSpec by id, raw guideline text, or URL.

        Priority:
            1. *guidelines_text* — LLM interprets provided text
            2. *guidelines_url*  — fetch URL, then interpret
            3. *style_id*        — load hardcoded JSON

        Returns:
            A validated StyleSpec object.
        """
        # 1) Raw text takes priority
        if guidelines_text and guidelines_text.strip():
            logger.info("Interpreting custom guideline text with LLM…")
            return self._interpret_with_llm(guidelines_text, style_id)

        # 2) URL fetch
        if guidelines_url and guidelines_url.strip():
            logger.info("Fetching guideline from URL: %s", guidelines_url)
            try:
                fetched = _fetch_url_text(guidelines_url)
                fetched = _clean_text(fetched)
                if len(fetched) < 50:
                    raise ValueError("Fetched content too short — likely an error page.")
                return self._interpret_with_llm(fetched, style_id)
            except Exception as exc:
                logger.error("URL fetch/interpret failed (%s) — falling back to hardcoded.", exc)
                return self._load_hardcoded(style_id)

        # 3) Hardcoded
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

    def _interpret_with_llm(
        self,
        guidelines_text: str,
        style_hint: str = "",
    ) -> StyleSpec:
        """
        Use LLM to extract formatting rules from raw guideline text.

        Steps:
            1. Clean & chunk the text
            2. For each chunk, ask LLM to extract partial StyleSpec fields
            3. Merge all chunk results into a single dict
            4. Deep-merge with defaults (so missing fields are populated)
            5. Validate with Pydantic
            6. Fall back to hardcoded spec if anything goes wrong
        """
        from backend.llm.client import get_llm_client
        from backend.llm.prompts import (
            RULE_INTERPRETER_SYSTEM,
            RULE_INTERPRETER_USER,
            RULE_INTERPRETER_REFINEMENT_USER,
        )

        try:
            client = get_llm_client()
        except Exception as exc:
            logger.error("Cannot get LLM client (%s) — fallback to hardcoded.", exc)
            return self._load_hardcoded(style_hint or "apa7")

        guidelines_text = _clean_text(guidelines_text)
        chunks = _chunk_text(guidelines_text)
        logger.info("Guideline split into %d chunk(s) for LLM.", len(chunks))

        merged_data: dict[str, Any] = {}

        # ── Pass 1: extract from each chunk ──────────────
        for idx, chunk in enumerate(chunks, 1):
            try:
                user_prompt = RULE_INTERPRETER_USER.format(
                    style_name=style_hint or "Custom Style",
                    guideline_text=chunk,
                )
                data = client.chat_json(
                    system_prompt=RULE_INTERPRETER_SYSTEM,
                    user_prompt=user_prompt,
                    temperature=0.1,
                    max_tokens=4096,
                )
                merged_data = _deep_merge(merged_data, data)
                logger.info("Chunk %d/%d extracted %d top-level keys.", idx, len(chunks), len(data))
            except Exception as exc:
                logger.warning("Chunk %d/%d failed (%s) — skipping.", idx, len(chunks), exc)

        if not merged_data:
            logger.error("All LLM chunks failed — falling back to hardcoded.")
            return self._load_hardcoded(style_hint or "apa7")

        # ── Pass 2: optional refinement ──────────────────
        try:
            refinement_prompt = RULE_INTERPRETER_REFINEMENT_USER.format(
                style_name=style_hint or "Custom Style",
                draft_json=json.dumps(merged_data, indent=2)[:6000],
                guideline_summary=guidelines_text[:2000],
            )
            refined = client.chat_json(
                system_prompt=RULE_INTERPRETER_SYSTEM,
                user_prompt=refinement_prompt,
                temperature=0.05,
                max_tokens=4096,
            )
            merged_data = _deep_merge(merged_data, refined)
            logger.info("Refinement pass merged successfully.")
        except Exception as exc:
            logger.warning("Refinement pass failed (%s) — using first-pass result.", exc)

        # ── Merge with defaults & validate ───────────────
        spec = self._validate_and_merge(merged_data, style_hint)
        return spec

    # ── Validation & default-merging ─────────────────────────

    def _validate_and_merge(self, llm_data: dict[str, Any], style_hint: str) -> StyleSpec:
        """
        Merge LLM-extracted data with default StyleSpec values,
        then validate. Falls back to hardcoded on failure.
        """
        defaults = json.loads(StyleSpec().model_dump_json())
        final_data = _deep_merge(defaults, llm_data)

        try:
            spec = StyleSpec.model_validate(final_data)
            logger.info("LLM-extracted StyleSpec validated: %s", spec.style_name)
            return spec
        except Exception as exc:
            logger.error(
                "Pydantic validation failed (%s) — attempting field-level recovery.", exc
            )
            return self._recover_spec(final_data, defaults, style_hint)

    def _recover_spec(
        self,
        bad_data: dict[str, Any],
        defaults: dict[str, Any],
        style_hint: str,
    ) -> StyleSpec:
        """
        Try to build a StyleSpec by keeping valid top-level sections
        and replacing invalid ones with defaults.
        """
        recovered = dict(defaults)
        section_keys = [
            "style_name", "style_id", "csl_style",
            "page_layout", "default_typography", "title_page",
            "abstract", "headings", "running_head", "references",
            "tables", "figures", "in_text_citations",
        ]
        for key in section_keys:
            if key in bad_data:
                try:
                    test = dict(recovered)
                    test[key] = bad_data[key]
                    StyleSpec.model_validate(test)
                    recovered[key] = bad_data[key]
                except Exception:
                    logger.warning("Section '%s' invalid — using default.", key)

        try:
            return StyleSpec.model_validate(recovered)
        except Exception as exc:
            logger.error("Recovery failed (%s) — full fallback to hardcoded.", exc)
            return self._load_hardcoded(style_hint or "apa7")

    # ── Comparison utility ───────────────────────────────────

    def compare_specs(self, spec_a: StyleSpec, spec_b: StyleSpec) -> dict[str, Any]:
        """
        Compare two StyleSpecs field-by-field.
        Returns a dict of {field_path: {"a": val_a, "b": val_b}} for differing fields.
        Useful for testing LLM output against ground truth.
        """
        a_data = json.loads(spec_a.model_dump_json())
        b_data = json.loads(spec_b.model_dump_json())
        return self._diff_dicts(a_data, b_data, prefix="")

    def _diff_dicts(self, a: Any, b: Any, prefix: str) -> dict[str, Any]:
        diffs: dict[str, Any] = {}
        if isinstance(a, dict) and isinstance(b, dict):
            all_keys = set(a.keys()) | set(b.keys())
            for k in sorted(all_keys):
                path = f"{prefix}.{k}" if prefix else k
                diffs.update(self._diff_dicts(a.get(k), b.get(k), path))
        elif a != b:
            diffs[prefix] = {"a": a, "b": b}
        return diffs
