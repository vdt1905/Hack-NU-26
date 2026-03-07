import os
import sys
import json
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import tempfile
import shutil

# Add the current directory so modules resolve
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))

from agents.transformer import TransformerAgent
from agents.ingest import IngestAgent
from schemas.docir import DocIR
from schemas.style_spec import StyleSpec

app = FastAPI(title="Rule-Based Reconstructor API")

# Setup CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/reconstruct_auto")
async def reconstruct_auto(
    document: UploadFile = File(..., description="The original unstructured DOCX file"),
    style: str = Form(..., description="The target style format (e.g., apa7, chicago, ieee)")
):
    try:
        # Create a temporary directory to perform operations
        temp_dir = Path(tempfile.mkdtemp(prefix="reconstruct_"))
        input_path = temp_dir / document.filename
        
        # Save the uploaded document
        with open(input_path, "wb") as f:
            content = await document.read()
            f.write(content)
            
        # 1. Dynamically load StyleSpec from local styles folder
        style_path = current_dir / "styles" / f"{style}.json"
        if not style_path.exists():
            return {"error": f"Style {style} not found"}, 404
            
        with open(style_path, "r", encoding="utf-8") as f:
            style_data = json.load(f)
        style_spec = StyleSpec.model_validate(style_data)
        
        # 2. Extract layout via IngestAgent directly (simulating DocIR)
        ingest_agent = IngestAgent()
        docir = ingest_agent.parse(input_path)
        
        # 3. Initialize and run the Deterministic Transformer Agent
        transformer = TransformerAgent()
        output_docx, change_records = transformer.transform(
            docir=docir,
            style_spec=style_spec,
            input_path=input_path,
            output_dir=temp_dir
        )
        
        # Return the resulting file to the client
        return FileResponse(
            path=output_docx,
            filename=f"Formatted_{style}_{document.filename}",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}, 500

if __name__ == "__main__":
    print("Starting Rule-Based Reconstructor API on port 8085...")
    uvicorn.run(app, host="127.0.0.1", port=8085)
