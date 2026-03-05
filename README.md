# 🎓 FormatForge AI — Agent Paperpal

> Agentic Manuscript Formatting System | HackaMined 2026

An AI-powered system that automatically reformats research manuscripts to match journal-specific style guides (APA 7, Vancouver, IEEE, etc.).

## Quick Start

```bash
# 1. Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up API keys in .env
# Edit .env and add your OPENAI_API_KEY or GROQ_API_KEY

# 4. Run the Streamlit app
streamlit run app.py

# OR run the FastAPI backend
uvicorn backend.api:app --reload
```

## Architecture

**Hybrid: LLM Brain + Deterministic Hands**

| Agent | Role |
|-------|------|
| Agent 1: Ingest & Parse | DOCX/PDF → DocIR JSON |
| Agent 2: Rule Interpreter | Guidelines → StyleSpec JSON |
| Agent 3: Structure Detector | Label paragraphs with roles |
| Agent 4: Citation Engine | Parse, format, validate citations |
| Agent 5: Transformer | Apply formatting to DOCX |
| Agent 6: Validator | Compliance scoring & explanations |

## Team

HackaMined 2026 — Cactus Communications / Paperpal Track
