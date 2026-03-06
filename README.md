# Document Editor Agent

A full-fledged **document editing AI agent** built with **Google ADK** and a
**custom MCP server** — no cloud dependencies.  Upload `.docx` files, edit
them with plain-English prompts, and download the result.  Ships with a
**FastAPI deployment server** ready to integrate with any web app.

## Architecture

```
┌─────────────┐   HTTP/JSON   ┌────────────────┐  stdio/MCP  ┌──────────────────┐
│  Web App /  │ ───────────▶  │  FastAPI Server │ ──────────▶ │  Custom MCP      │
│  Frontend   │ ◀───────────  │  (server.py)    │ ◀────────── │  Server          │
└─────────────┘               │                 │             │  (mcp_server/)   │
                              │  ADK Runner     │             │  python-docx     │
                              │  + Gemini LLM   │             │  local .docx     │
                              └────────────────┘             └──────────────────┘
```

**Components:**

| Layer | Role |
|---|---|
| **Custom MCP Server** (`mcp_server/server.py`) | 22 tools for CRUD, formatting, search, tables, lists on local `.docx` files |
| **ADK Agent** (`doc_editor_agent/agent.py`) | Gemini-powered agent with a human-in-the-loop instruction |
| **FastAPI Server** (`server.py`) | REST API: `/chat`, `/upload`, `/documents`, `/download` |

## Capabilities

| Category | Tools |
|---|---|
| **Read** | `list_documents`, `read_document`, `read_paragraph`, `read_table`, `search_text`, `get_document_info` |
| **Edit** | `create_document`, `add_paragraph`, `insert_paragraph_after`, `delete_paragraph`, `edit_paragraph_text`, `add_heading`, `add_page_break`, `add_table`, `add_bullet_list`, `add_numbered_list`, `search_and_replace` |
| **Format** | `format_text` (bold/italic/underline/strikethrough/font/colour/highlight), `format_paragraph`, `set_paragraph_style`, `set_paragraph_alignment` |
| **Manage** | `delete_document`, `duplicate_document`, `export_to_text` |

Every write operation requires **human-in-the-loop confirmation** — the agent describes the planned change and waits for your "yes" before executing.

---

## Quick Start

### Prerequisites

| Tool | Version |
|---|---|
| **Python** | 3.10+ |
| **pip** | latest |

### 1. Install dependencies

```bash
cd "c:\Users\harsh khanna\Desktop\VS CODE\google adk"
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

### 2. Set your Gemini API key

Edit `doc_editor_agent/.env`:

```env
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=<your-gemini-api-key>
```

Get a key at [Google AI Studio](https://aistudio.google.com/apikey).

### 3. Run with ADK Web UI (development)

```bash
adk web --no-reload
```

Open `http://localhost:8000`, select **doc_editor_agent**, and start chatting.

### 4. Run as a deployable REST API

```bash
python server.py
# or
uvicorn server:app --host 0.0.0.0 --port 8080
```

The API is now live at `http://localhost:8080`.

---

## API Reference

### `POST /chat`

Send a natural-language message to the agent.

**Request:**
```json
{
  "message": "Bold the title in report.docx",
  "user_id": "user1",
  "session_id": "optional-existing-session-id"
}
```

**Response:**
```json
{
  "response": "I will apply bold formatting to paragraph 0 ('Project Report'). Shall I proceed?",
  "user_id": "user1",
  "session_id": "abc-123-def"
}
```

Conversation state is maintained per `session_id` — send the returned
`session_id` back in subsequent requests to continue the conversation.

### `POST /upload`

Upload a `.docx` file.

```bash
curl -F "file=@report.docx" http://localhost:8080/upload
```

### `GET /documents`

List all documents in the store.

### `GET /documents/{filename}/download`

Download a document.

### `DELETE /documents/{filename}`

Delete a document.

### `GET /health`

Health check.

---

## Project Structure

```
google adk/
├── doc_editor_agent/
│   ├── __init__.py          # Package marker
│   ├── agent.py             # ADK agent (Gemini + MCP toolset + HITL)
│   └── .env                 # Gemini API key
├── mcp_server/
│   ├── __init__.py
│   └── server.py            # Custom MCP server (22 tools, python-docx)
├── documents/               # Document store (auto-created, git-ignored)
├── server.py                # FastAPI deployment server
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## Web App Integration Example

```javascript
// Upload a document
const formData = new FormData();
formData.append('file', fileInput.files[0]);
await fetch('http://localhost:8080/upload', { method: 'POST', body: formData });

// Chat with the agent
let sessionId = null;

async function sendMessage(message) {
  const res = await fetch('http://localhost:8080/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      user_id: 'web_user',
      session_id: sessionId,
    }),
  });
  const data = await res.json();
  sessionId = data.session_id;  // reuse for conversation continuity
  return data.response;
}

// Example conversation
await sendMessage("Show me the content of report.docx");
await sendMessage("Bold the title");
await sendMessage("Yes, go ahead");

// Download the edited document
window.location.href = 'http://localhost:8080/documents/report.docx/download';
```

---

## Usage Examples

```
You:   What documents do I have?
Agent: [lists documents]

You:   Show me report.docx
Agent: [displays full content with paragraph indices]

You:   Bold the title "Project Report"
Agent: I'll apply bold formatting to paragraph 0 ("Project Report").
       Shall I proceed?
You:   Yes
Agent: Done — paragraph 0 is now bold.

You:   Add a "Conclusions" heading and a paragraph saying "The project succeeded."
Agent: I'll:
       1. Add a Heading 1 "Conclusions"
       2. Add a Normal paragraph "The project succeeded."
       Shall I proceed?
You:   Do it
Agent: Done — heading and paragraph added.

You:   Replace all occurrences of "2025" with "2026"
Agent: I'll search-and-replace "2025" → "2026" across the entire document.
       Shall I proceed?
You:   Yes
Agent: Done — 4 replacements made.
```

---

## Deployment

### Docker

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 8080
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
```

```bash
docker build -t doc-editor-agent .
docker run -p 8080:8080 -e GOOGLE_API_KEY=<key> doc-editor-agent
```

### Cloud (Railway / Render / Fly.io)

1. Push the repo.
2. Set the `GOOGLE_API_KEY` environment variable.
3. Set the start command: `uvicorn server:app --host 0.0.0.0 --port $PORT`

---

## License

MIT
