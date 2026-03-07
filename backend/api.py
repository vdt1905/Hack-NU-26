"""
FormatForge AI — FastAPI Application
REST API for the formatting pipeline.
"""

from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from backend.config import (
    API_HOST,
    API_PORT,
    APP_DESCRIPTION,
    APP_NAME,
    APP_VERSION,
    AVAILABLE_STYLES,
    OUTPUT_FORMATTED_DIR,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── FastAPI app ──────────────────────────────────────────────

app = FastAPI(
    title=APP_NAME,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include Agno LLM streaming router ───────────────────────
try:
    from backend.agno_router import agno_router
    app.include_router(agno_router)
    logger.info("Unified pipeline router loaded (/api/v2/pipeline/stream)")
except Exception as exc:
    logger.warning(f"Agno router not loaded: {exc}")


# ── Health check ─────────────────────────────────────────────

@app.get("/api/v1/health")
def health():
    return {"status": "ok", "version": APP_VERSION}


# ── Available styles ─────────────────────────────────────────

@app.get("/api/v1/styles")
def list_styles():
    return {"available_styles": AVAILABLE_STYLES}


# ── Full formatting pipeline ────────────────────────────────

@app.post("/api/v1/format")
async def format_document(
    file: UploadFile = File(...),
    style: str = Form("apa7"),
    guidelines_text: Optional[str] = Form(None),
):
    """
    Upload a manuscript, select a style, and get a formatted document back.
    """
    # Validate style
    if style not in AVAILABLE_STYLES and not guidelines_text:
        raise HTTPException(status_code=400, detail=f"Unknown style '{style}'. Available: {list(AVAILABLE_STYLES.keys())}")

    # Save uploaded file to temp
    suffix = Path(file.filename or "upload.docx").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        from backend.agents.orchestrator import Orchestrator
        orchestrator = Orchestrator()
        result = await orchestrator.run(
            input_path=tmp_path,
            style_id=style,
            guidelines_text=guidelines_text,
        )

        if not result.success:
            raise HTTPException(status_code=500, detail=result.error_message or "Pipeline failed")

        return JSONResponse(content={
            "success": True,
            "output_filename": result.output_filename,
            "compliance_report": result.compliance_report.model_dump(),
            "citation_report": result.citation_report.model_dump(),
            "structure_summary": result.structure_summary,
            "processing_time_seconds": result.processing_time_seconds,
        })

    finally:
        tmp_path.unlink(missing_ok=True)


# ── Parse only (structure detection) ─────────────────────────

@app.post("/api/v1/parse")
async def parse_document(file: UploadFile = File(...)):
    """Upload a manuscript and get the detected structure (DocIR)."""
    suffix = Path(file.filename or "upload.docx").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        from backend.agents.ingest import IngestAgent
        from backend.agents.structure_detector import StructureDetectorAgent

        ingest = IngestAgent()
        detector = StructureDetectorAgent()

        docir = ingest.parse(tmp_path)
        docir = detector.detect(docir)

        return JSONResponse(content=docir.model_dump(mode="json"))

    finally:
        tmp_path.unlink(missing_ok=True)


# ── Download formatted file ──────────────────────────────────

@app.get("/api/v1/download/{filename}")
def download_file(filename: str):
    """Download a formatted output file."""
    file_path = OUTPUT_FORMATTED_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        str(file_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
    )


# ── Main entry ───────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api:app", host=API_HOST, port=API_PORT, reload=True)
