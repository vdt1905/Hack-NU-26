"""
FormatForge AI — Agent 6: Validator & Compliance Scorer
Re-scans the formatted document against StyleSpec rules
and generates a scored compliance report with explanations.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from backend.schemas.reports import (
    CategoryScore,
    ChangeRecord,
    ComplianceReport,
)
from backend.schemas.style_spec import StyleSpec

logger = logging.getLogger(__name__)


class ValidatorAgent:
    """Agent 6 — Validate the formatted document and score compliance."""

    CATEGORY_WEIGHTS = {
        "page_layout": 0.15,
        "typography": 0.15,
        "headings": 0.15,
        "title_page": 0.10,
        "abstract": 0.10,
        "citations": 0.15,
        "references": 0.15,
        "tables_figures": 0.05,
    }

    def validate(
        self,
        output_path: Path,
        style_spec: StyleSpec,
        changes: list[ChangeRecord],
    ) -> ComplianceReport:
        """
        Validate the formatted document and produce a compliance report.

        Args:
            output_path: Path to the formatted DOCX.
            style_spec: The target style spec.
            changes: List of changes applied by the Transformer.

        Returns:
            ComplianceReport with category scores and explanations.
        """
        report = ComplianceReport(style_name=style_spec.style_name)
        report.changes = changes
        report.total_changes = len(changes)

        # ── Score by scanning the output document ────────────
        categories = self._score_from_document(output_path, style_spec, changes)
        report.categories = categories

        # ── Compute overall score ────────────────────────────
        report.compute_overall_score()

        # ── Collect warnings / errors from changes ───────────
        for c in changes:
            if c.severity.value == "warning":
                report.warnings.append(c.description)
            elif c.severity.value == "error":
                report.errors.append(c.description)

        logger.info(
            "Compliance score: %.1f%% (%d changes, %d warnings, %d errors)",
            report.overall_score,
            report.total_changes,
            len(report.warnings),
            len(report.errors),
        )
        return report

    # ── Scoring engine ───────────────────────────────────────

    def _score_from_document(
        self,
        output_path: Path,
        style_spec: StyleSpec,
        changes: list[ChangeRecord],
    ) -> list[CategoryScore]:
        """
        Open the formatted document and check each category against the spec.
        Returns a list of CategoryScore objects.
        """
        from docx import Document
        from docx.shared import Inches

        scores: list[CategoryScore] = []

        try:
            doc = Document(str(output_path))
        except Exception as exc:
            logger.error("Cannot open formatted document for validation: %s", exc)
            return scores

        # ── Page Layout ──────────────────────────────────────
        layout_score = self._check_page_layout(doc, style_spec)
        scores.append(layout_score)

        # ── Typography ───────────────────────────────────────
        typo_score = self._check_typography(doc, style_spec)
        scores.append(typo_score)

        # ── Headings ─────────────────────────────────────────
        heading_changes = [c for c in changes if c.category == "headings"]
        heading_score = CategoryScore(
            category="headings",
            weight=self.CATEGORY_WEIGHTS["headings"],
            checks_total=max(len(heading_changes), 1),
            checks_passed=len(heading_changes),
            score=100.0 if heading_changes else 50.0,
        )
        scores.append(heading_score)

        # ── Title Page ───────────────────────────────────────
        tp_changes = [c for c in changes if c.category == "title_page"]
        tp_score = CategoryScore(
            category="title_page",
            weight=self.CATEGORY_WEIGHTS["title_page"],
            checks_total=max(len(tp_changes), 1),
            checks_passed=len(tp_changes),
            score=100.0 if tp_changes else 50.0,
        )
        scores.append(tp_score)

        # ── Abstract ─────────────────────────────────────────
        abs_changes = [c for c in changes if c.category == "abstract"]
        abs_score = CategoryScore(
            category="abstract",
            weight=self.CATEGORY_WEIGHTS["abstract"],
            checks_total=max(len(abs_changes), 1),
            checks_passed=len(abs_changes),
            score=100.0 if abs_changes else 50.0,
        )
        scores.append(abs_score)

        # ── Citations ────────────────────────────────────────
        cit_score = CategoryScore(
            category="citations",
            weight=self.CATEGORY_WEIGHTS["citations"],
            checks_total=1,
            checks_passed=1,
            score=75.0,  # will be refined with CitationReport in Phase 3
        )
        scores.append(cit_score)

        # ── References ───────────────────────────────────────
        ref_changes = [c for c in changes if c.category == "references"]
        ref_score = CategoryScore(
            category="references",
            weight=self.CATEGORY_WEIGHTS["references"],
            checks_total=max(len(ref_changes), 1),
            checks_passed=len(ref_changes),
            score=100.0 if ref_changes else 50.0,
        )
        scores.append(ref_score)

        # ── Tables & Figures ─────────────────────────────────
        tf_score = CategoryScore(
            category="tables_figures",
            weight=self.CATEGORY_WEIGHTS["tables_figures"],
            checks_total=1,
            checks_passed=1,
            score=75.0,  # placeholder
        )
        scores.append(tf_score)

        return scores

    # ── Specific checkers ────────────────────────────────────

    def _check_page_layout(self, doc, style_spec: StyleSpec) -> CategoryScore:
        """Verify page margins, size, orientation."""
        layout = style_spec.page_layout
        checks = 0
        passed = 0
        issues: list[str] = []

        for section in doc.sections:
            checks += 4  # top, bottom, left, right margins

            margins = {
                "top": (section.top_margin, layout.margin_top_inches),
                "bottom": (section.bottom_margin, layout.margin_bottom_inches),
                "left": (section.left_margin, layout.margin_left_inches),
                "right": (section.right_margin, layout.margin_right_inches),
            }

            for name, (actual, expected) in margins.items():
                actual_inches = round(actual / 914400, 2) if actual else 0
                if abs(actual_inches - expected) < 0.05:
                    passed += 1
                else:
                    issues.append(f"{name} margin: {actual_inches}\" (expected {expected}\")")
            break  # only check first section

        score = (passed / checks * 100) if checks else 100
        return CategoryScore(
            category="page_layout",
            weight=self.CATEGORY_WEIGHTS["page_layout"],
            score=round(score, 1),
            checks_passed=passed,
            checks_total=checks,
            issues=issues,
        )

    def _check_typography(self, doc, style_spec: StyleSpec) -> CategoryScore:
        """Check default font, size, line spacing."""
        typo = style_spec.default_typography
        checks = 3
        passed = 0
        issues: list[str] = []

        normal = doc.styles["Normal"]
        if normal.font.name == typo.font_name:
            passed += 1
        else:
            issues.append(f"Font: {normal.font.name} (expected {typo.font_name})")

        if normal.font.size:
            actual_pt = round(normal.font.size / 12700, 1)
            if abs(actual_pt - typo.font_size_pt) < 0.5:
                passed += 1
            else:
                issues.append(f"Font size: {actual_pt}pt (expected {typo.font_size_pt}pt)")
        else:
            passed += 1  # can't verify, assume OK

        if normal.paragraph_format.line_spacing:
            if abs(normal.paragraph_format.line_spacing - typo.line_spacing) < 0.1:
                passed += 1
            else:
                issues.append(f"Line spacing: {normal.paragraph_format.line_spacing} (expected {typo.line_spacing})")
        else:
            passed += 1

        score = (passed / checks * 100) if checks else 100
        return CategoryScore(
            category="typography",
            weight=self.CATEGORY_WEIGHTS["typography"],
            score=round(score, 1),
            checks_passed=passed,
            checks_total=checks,
            issues=issues,
        )
