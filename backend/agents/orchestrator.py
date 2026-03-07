"""
FormatForge AI — Agent 0: Orchestrator
Main pipeline controller. Routes tasks to agents and maintains shared state.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

from backend.schemas.docir import DocIR
from backend.schemas.reports import ComplianceReport, CitationReport, FormatResult
from backend.schemas.style_spec import StyleSpec

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Central pipeline controller.

    Flow:
        1. Ingest & Parse  → DocIR
        2. Rule Interpret   → StyleSpec  (or load hardcoded)
        3. Structure Detect → Labeled DocIR
        4. Citation Engine  → Formatted refs + citation report
        5. Transformer      → Formatted DOCX + change log
        6. Validator        → Compliance report
    """

    def __init__(self) -> None:
        # Lazy imports to avoid circular deps & keep module light
        from backend.agents.ingest import IngestAgent
        from backend.agents.structure_detector import StructureDetectorAgent
        from backend.agents.rule_interpreter import RuleInterpreterAgent
        from backend.agents.citation_engine import CitationEngineAgent
        from backend.agents.transformer import TransformerAgent
        from backend.agents.validator import ValidatorAgent

        self.ingest = IngestAgent()
        self.structure_detector = StructureDetectorAgent(use_llm=True)
        self.rule_interpreter = RuleInterpreterAgent()
        self.citation_engine = CitationEngineAgent()
        self.transformer = TransformerAgent()
        self.validator = ValidatorAgent()

    # ── Full pipeline ────────────────────────────────────────

    async def run(
        self,
        input_path: Path,
        style_id: str = "apa7",
        guidelines_text: Optional[str] = None,
        guidelines_url: Optional[str] = None,
        output_dir: Optional[Path] = None,
    ) -> FormatResult:
        """
        Execute the full formatting pipeline.

        Args:
            input_path: Path to the input manuscript (.docx / .pdf / .txt).
            style_id: Style identifier (e.g. "apa7").
            guidelines_text: Optional raw guideline text for LLM interpretation.
            guidelines_url: Optional URL to a style guide page.
            output_dir: Directory for output files.

        Returns:
            FormatResult with formatted doc path, compliance report, etc.
        """
        start = time.time()
        result = FormatResult()

        try:
            # ── Step 1: Ingest ───────────────────────────────
            logger.info("Step 1/6 — Ingesting %s", input_path.name)
            docir: DocIR = self.ingest.parse(input_path)

            # ── Step 2: Get StyleSpec ────────────────────────
            logger.info("Step 2/6 — Loading style spec: %s", style_id)
            style_spec: StyleSpec = self.rule_interpreter.get_style_spec(
                style_id=style_id,
                guidelines_text=guidelines_text,
                guidelines_url=guidelines_url,
            )

            # ── Step 3: Structure Detection ──────────────────
            logger.info("Step 3/6 — Detecting document structure")
            docir = self.structure_detector.detect(docir)

            # Build structure summary
            role_counts: dict[str, int] = {}
            for elem in docir.elements:
                role_counts[elem.role.value] = role_counts.get(elem.role.value, 0) + 1
            result.structure_summary = role_counts

            # ── Step 4: Citation Engine ──────────────────────
            logger.info("Step 4/6 — Processing citations & references")
            docir, citation_report = self.citation_engine.process(docir, style_spec)
            result.citation_report = citation_report

            # ── Step 5: Transformer ──────────────────────────
            logger.info("Step 5/6 — Applying formatting")
            output_path, changes = self.transformer.transform(
                docir=docir,
                style_spec=style_spec,
                input_path=input_path,
                output_dir=output_dir,
                formatted_bibliography=citation_report.formatted_bibliography,
            )
            result.output_filename = str(output_path)

            # ── Step 6: Validator ────────────────────────────
            logger.info("Step 6/6 — Validating compliance")
            compliance: ComplianceReport = self.validator.validate(
                output_path=output_path,
                style_spec=style_spec,
                changes=changes,
                citation_report=citation_report,
            )
            result.compliance_report = compliance

            result.success = True

        except Exception as exc:
            logger.exception("Pipeline failed: %s", exc)
            result.success = False
            result.error_message = str(exc)

        result.processing_time_seconds = round(time.time() - start, 2)
        logger.info("Pipeline completed in %.2fs — success=%s", result.processing_time_seconds, result.success)
        return result
