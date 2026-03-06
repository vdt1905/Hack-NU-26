"""
Streamlit App — Document Editor Agent
======================================

Interactive UI to chat with the DocBot agent and manage .docx documents.
Connects to the FastAPI backend (api.py) running on port 8081.

Run:
    streamlit run streamlit_app.py
"""

import json
import time

import requests
import streamlit as st

# ── Config ───────────────────────────────────────────────────────────────
API_BASE = "http://localhost:8081"


def api(method: str, path: str, **kwargs) -> dict | list | str | None:
    """Call the FastAPI backend. Returns parsed JSON or None on error."""
    try:
        resp = getattr(requests, method)(f"{API_BASE}{path}", timeout=60, **kwargs)
        if resp.status_code >= 400:
            st.error(f"API Error {resp.status_code}: {resp.text}")
            return None
        ct = resp.headers.get("content-type", "")
        if "application/json" in ct:
            return resp.json()
        if "text/html" in ct:
            return resp.text
        return resp.json() if resp.text else None
    except requests.ConnectionError:
        st.error("Cannot connect to API. Make sure the server is running on port 8081.")
        return None
    except Exception as e:
        st.error(f"Request failed: {e}")
        return None


def get_snapshot(filename: str) -> dict | None:
    """Get a quick document snapshot for before/after comparison."""
    return api("get", f"/documents/{filename}/snapshot")


# ═════════════════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ═════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="DocBot — Document Editor Agent",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ───────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stChatMessage { max-width: 100%; }
    .block-container { padding-top: 1rem; }
    div[data-testid="stSidebar"] { background-color: #f8f9fa; }
    .doc-card {
        background: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 12px 16px;
        margin: 4px 0;
        transition: box-shadow 0.2s;
    }
    .doc-card:hover {
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .snapshot-box {
        background: #f0f7ff;
        border: 1px solid #b3d4fc;
        border-radius: 6px;
        padding: 10px 14px;
        margin: 6px 0;
        font-size: 0.9em;
    }
    .change-indicator {
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.85em;
        font-weight: 600;
    }
    .change-up { background: #d4edda; color: #155724; }
    .change-down { background: #f8d7da; color: #721c24; }
    .change-same { background: #e2e3e5; color: #383d41; }
</style>
""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════
#  SESSION STATE
# ═════════════════════════════════════════════════════════════════════════

if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "selected_doc" not in st.session_state:
    st.session_state.selected_doc = None
if "user_id" not in st.session_state:
    st.session_state.user_id = "streamlit_user"
if "last_snapshot" not in st.session_state:
    st.session_state.last_snapshot = None


def new_session():
    resp = api("post", "/sessions")
    if resp:
        st.session_state.session_id = resp.get("session_id")
    st.session_state.messages = []
    st.session_state.last_snapshot = None


# ═════════════════════════════════════════════════════════════════════════
#  SIDEBAR — Document Management
# ═════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.title("📝 DocBot")
    st.caption("AI Document Editor Agent")

    # ── Health Check ─────────────────────────────────────────────────────
    health = api("get", "/health")
    if health:
        c1, c2 = st.columns(2)
        c1.metric("Agent", "✅ ON" if health.get("agent_available") else "❌ OFF")
        c2.metric("Docs", health.get("document_count", 0))
    else:
        st.warning("API offline")

    st.divider()

    # ── Session ──────────────────────────────────────────────────────────
    if st.button("🔄 New Chat Session", use_container_width=True):
        new_session()
        st.rerun()

    if st.session_state.session_id:
        st.caption(f"Session: `{st.session_state.session_id[:12]}…`")

    st.divider()

    # ── Document List ────────────────────────────────────────────────────
    st.subheader("📄 Documents")

    docs = api("get", "/documents")
    if docs:
        for doc in docs:
            fname = doc["filename"]
            size_kb = doc["size_bytes"] / 1024
            col1, col2 = st.columns([3, 1])
            with col1:
                if st.button(f"📄 {fname}", key=f"sel_{fname}", use_container_width=True):
                    st.session_state.selected_doc = fname
                    st.session_state.last_snapshot = get_snapshot(fname)
                    st.rerun()
            with col2:
                st.caption(f"{size_kb:.1f} KB")
    else:
        st.info("No documents found.")

    st.divider()

    # ── Create Document ──────────────────────────────────────────────────
    st.subheader("➕ Create Document")
    new_doc_title = st.text_input("Document title", key="new_doc_title", placeholder="My Report")
    if st.button("Create", key="btn_create", use_container_width=True) and new_doc_title:
        result = api("post", "/documents", json={"title": new_doc_title})
        if result:
            st.success(f"Created: {result.get('filename')}")
            st.session_state.selected_doc = result.get("filename")
            st.session_state.last_snapshot = get_snapshot(result.get("filename"))
            time.sleep(0.5)
            st.rerun()

    st.divider()

    # ── Upload Document ──────────────────────────────────────────────────
    st.subheader("📤 Upload Document")
    uploaded = st.file_uploader("Upload .docx", type=["docx"], key="uploader")
    if uploaded:
        files = {"file": (uploaded.name, uploaded.getvalue(),
                          "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        result = api("post", "/documents/upload", files=files)
        if result:
            st.success(f"Uploaded: {result.get('filename')}")
            st.session_state.selected_doc = result.get("filename")
            st.session_state.last_snapshot = get_snapshot(result.get("filename"))
            time.sleep(0.5)
            st.rerun()


# ═════════════════════════════════════════════════════════════════════════
#  HELPER: RENDER INLINE PREVIEW
# ═════════════════════════════════════════════════════════════════════════

def render_inline_preview(filename: str, label: str = "Document Preview"):
    """Render a compact inline preview of the document."""
    info = api("get", f"/documents/{filename}")
    if info:
        c1, c2, c3 = st.columns(3)
        c1.metric("Paragraphs", info.get("paragraph_count", 0))
        c2.metric("Words", info.get("word_count", 0))
        c3.metric("Tables", info.get("table_count", 0))

    html = api("get", f"/documents/{filename}/preview")
    if html and isinstance(html, str):
        st.components.v1.html(
            f'<div style="background:white;padding:20px;border-radius:8px;'
            f'border:1px solid #ddd;min-height:200px;">{html}</div>',
            height=400,
            scrolling=True,
        )


def render_change_summary(before: dict | None, after: dict | None):
    """Show what changed between two snapshots."""
    if not before or not after:
        return
    bp = before.get("paragraph_count", 0)
    ap = after.get("paragraph_count", 0)
    bw = before.get("word_count", 0)
    aw = after.get("word_count", 0)
    bt = before.get("table_count", 0)
    at_ = after.get("table_count", 0)

    dp = ap - bp
    dw = aw - bw
    dt = at_ - bt

    changes = []
    if dp != 0:
        sign = "+" if dp > 0 else ""
        changes.append(f"Paragraphs: {bp} → {ap} ({sign}{dp})")
    if dw != 0:
        sign = "+" if dw > 0 else ""
        changes.append(f"Words: {bw} → {aw} ({sign}{dw})")
    if dt != 0:
        sign = "+" if dt > 0 else ""
        changes.append(f"Tables: {bt} → {at_} ({sign}{dt})")

    if changes:
        st.info("📊 **Changes detected:**\n" + "\n".join(f"- {c}" for c in changes))
    else:
        st.caption("No structural changes detected.")

    # Show new/changed paragraphs at the end
    after_last = after.get("last_paragraphs", [])
    if after_last:
        with st.expander("📋 Last paragraphs in document", expanded=False):
            for p in after_last:
                st.text(f"[P{p['index']}|{p['style']}] {p['text']}")


# ═════════════════════════════════════════════════════════════════════════
#  MAIN AREA — Tabs
# ═════════════════════════════════════════════════════════════════════════

tab_chat, tab_preview, tab_tools = st.tabs(["💬 Chat", "👁️ Preview", "🛠️ Tools"])


# ── TAB 1: CHAT ─────────────────────────────────────────────────────────
with tab_chat:
    # If a document is selected, mention it in context
    if st.session_state.selected_doc:
        st.info(f"Working on: **{st.session_state.selected_doc}**")

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if prompt := st.chat_input("Ask DocBot anything about your documents…"):
        # If no session, create one
        if not st.session_state.session_id:
            new_session()

        # Prepend current document context
        full_prompt = prompt
        if st.session_state.selected_doc:
            full_prompt = f"[Working on file: {st.session_state.selected_doc}]\n{prompt}"

        # Take a BEFORE snapshot for comparison
        before_snapshot = None
        if st.session_state.selected_doc:
            before_snapshot = get_snapshot(st.session_state.selected_doc)

        # Show user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Call API
        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                result = api("post", "/chat", json={
                    "message": full_prompt,
                    "user_id": st.session_state.user_id,
                    "session_id": st.session_state.session_id,
                })

            if result:
                response = result.get("response", "(no response)")
                # Update session_id (may have changed due to tool_use_failed retry)
                st.session_state.session_id = result.get("session_id", st.session_state.session_id)
            else:
                response = "⚠️ Failed to get a response. Try clicking **New Chat Session** in the sidebar and retry."

            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

            # After a successful response, show change summary + inline preview
            if result and st.session_state.selected_doc:
                after_snapshot = get_snapshot(st.session_state.selected_doc)
                st.session_state.last_snapshot = after_snapshot

                # Detect if document changed
                if before_snapshot and after_snapshot:
                    bp = before_snapshot.get("paragraph_count", 0)
                    ap = after_snapshot.get("paragraph_count", 0)
                    bw = before_snapshot.get("word_count", 0)
                    aw = after_snapshot.get("word_count", 0)
                    if bp != ap or bw != aw:
                        st.divider()
                        render_change_summary(before_snapshot, after_snapshot)
                        with st.expander("👁️ Quick Preview", expanded=True):
                            render_inline_preview(st.session_state.selected_doc)


# ── TAB 2: PREVIEW ──────────────────────────────────────────────────────
with tab_preview:
    if st.session_state.selected_doc:
        st.subheader(f"Preview: {st.session_state.selected_doc}")

        p1, p2, p3 = st.columns([1, 1, 1])
        with p1:
            if st.button("🔄 Refresh Preview", key="refresh_preview"):
                st.rerun()
        with p2:
            if st.button("⬇️ Download", key="download_doc"):
                st.markdown(
                    f'<a href="{API_BASE}/documents/{st.session_state.selected_doc}/download" '
                    f'target="_blank">Click to download</a>',
                    unsafe_allow_html=True,
                )
        with p3:
            if st.button("📊 Snapshot", key="take_snapshot"):
                snap = get_snapshot(st.session_state.selected_doc)
                st.session_state.last_snapshot = snap

        # Info metrics
        info = api("get", f"/documents/{st.session_state.selected_doc}")
        if info:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Paragraphs", info.get("paragraph_count", 0))
            c2.metric("Words", info.get("word_count", 0))
            c3.metric("Tables", info.get("table_count", 0))
            c4.metric("Styles", len(info.get("styles_used", [])))

        st.divider()

        # HTML preview
        html = api("get", f"/documents/{st.session_state.selected_doc}/preview")
        if html and isinstance(html, str):
            st.components.v1.html(
                f'<div style="background:white;padding:20px;border-radius:8px;'
                f'border:1px solid #ddd;min-height:400px;">{html}</div>',
                height=600,
                scrolling=True,
            )

        st.divider()

        # Raw content
        with st.expander("📋 Raw Paragraph Content", expanded=False):
            content = api("get", f"/documents/{st.session_state.selected_doc}/content")
            if content and "paragraphs" in content:
                total = content.get("total_paragraphs", len(content["paragraphs"]))
                st.caption(f"Showing {len(content['paragraphs'])} of {total} paragraphs")
                for p in content["paragraphs"]:
                    st.text(f"[P{p['index']}|{p['style']}] {p['text']}")
                if content.get("has_more"):
                    st.info(f"Document has {total} paragraphs. Use the Chat tab to read more.")
    else:
        st.info("Select a document from the sidebar to preview it.")


# ── TAB 3: TOOLS ────────────────────────────────────────────────────────
with tab_tools:
    st.subheader("🛠️ Direct Document Tools")

    if not st.session_state.selected_doc:
        st.info("Select a document first.")
    else:
        fname = st.session_state.selected_doc
        st.info(f"Operating on: **{fname}**")

        tool = st.selectbox("Choose a tool", [
            "Search Text",
            "Search & Replace",
            "Add Paragraph",
            "Add Heading",
            "Add Bullet List",
            "Add Numbered List",
            "Add Table",
            "Edit Paragraph Text",
            "Delete Paragraph",
            "Format Paragraph",
            "Set Paragraph Style",
            "Set Paragraph Alignment",
            "Delete Document",
        ], key="tool_select")

        st.divider()

        if tool == "Search Text":
            q = st.text_input("Search query", key="tool_search_q")
            cs = st.checkbox("Case sensitive", key="tool_search_cs")
            if st.button("Search", key="btn_search") and q:
                r = api("post", f"/documents/{fname}/search",
                        json={"query": q, "case_sensitive": cs})
                if r:
                    st.json(r)

        elif tool == "Search & Replace":
            find = st.text_input("Find text", key="tool_find")
            repl = st.text_input("Replace with", key="tool_repl")
            cs = st.checkbox("Case sensitive", key="tool_repl_cs")
            if st.button("Replace All", key="btn_replace") and find:
                r = api("post", f"/documents/{fname}/replace",
                        json={"find_text": find, "replace_with": repl, "case_sensitive": cs})
                if r:
                    st.json(r)

        elif tool == "Add Paragraph":
            txt = st.text_area("Text", key="tool_addp_text")
            sty = st.selectbox("Style", ["Normal", "Heading 1", "Heading 2", "Heading 3",
                                          "List Bullet", "List Number"], key="tool_addp_style")
            if st.button("Add", key="btn_addp") and txt:
                r = api("post", f"/documents/{fname}/paragraphs",
                        json={"text": txt, "style": sty})
                if r:
                    st.success(r.get("message", "Done"))

        elif tool == "Add Heading":
            txt = st.text_input("Heading text", key="tool_heading_txt")
            lvl = st.slider("Level", 1, 4, 1, key="tool_heading_lvl")
            if st.button("Add Heading", key="btn_heading") and txt:
                r = api("post", f"/documents/{fname}/headings",
                        json={"text": txt, "level": lvl})
                if r:
                    st.success(r.get("message", "Done"))

        elif tool == "Add Bullet List":
            items_raw = st.text_area("Items (one per line)", key="tool_bullet_items")
            if st.button("Add Bullets", key="btn_bullets") and items_raw:
                items = [x.strip() for x in items_raw.strip().split("\n") if x.strip()]
                r = api("post", f"/documents/{fname}/lists/bullet", json={"items": items})
                if r:
                    st.success(r.get("message", "Done"))

        elif tool == "Add Numbered List":
            items_raw = st.text_area("Items (one per line)", key="tool_num_items")
            if st.button("Add Numbers", key="btn_numbers") and items_raw:
                items = [x.strip() for x in items_raw.strip().split("\n") if x.strip()]
                r = api("post", f"/documents/{fname}/lists/numbered", json={"items": items})
                if r:
                    st.success(r.get("message", "Done"))

        elif tool == "Add Table":
            rows = st.number_input("Rows", 1, 20, 3, key="tool_tbl_rows")
            cols = st.number_input("Cols", 1, 10, 3, key="tool_tbl_cols")
            data_raw = st.text_area("Data (JSON 2D array, optional)",
                                    placeholder='[["A","B","C"],["1","2","3"]]',
                                    key="tool_tbl_data")
            if st.button("Add Table", key="btn_table"):
                body = {"rows": rows, "cols": cols}
                if data_raw.strip():
                    try:
                        body["data"] = json.loads(data_raw)
                    except json.JSONDecodeError:
                        st.error("Invalid JSON for table data.")
                r = api("post", f"/documents/{fname}/tables", json=body)
                if r:
                    st.success(r.get("message", "Done"))

        elif tool == "Edit Paragraph Text":
            idx = st.number_input("Paragraph index (0-based)", 0, 999, 0, key="tool_edit_idx")
            new_txt = st.text_area("New text", key="tool_edit_txt")
            if st.button("Update", key="btn_edit") and new_txt:
                r = api("put", f"/documents/{fname}/paragraphs/{idx}",
                        json={"new_text": new_txt})
                if r:
                    st.success(r.get("message", "Done"))

        elif tool == "Delete Paragraph":
            idx = st.number_input("Paragraph index", 0, 999, 0, key="tool_del_idx")
            if st.button("Delete Paragraph", key="btn_del_para", type="primary"):
                r = api("delete", f"/documents/{fname}/paragraphs/{idx}")
                if r:
                    st.success(r.get("message", "Done"))

        elif tool == "Format Paragraph":
            idx = st.number_input("Paragraph index", 0, 999, 0, key="tool_fmt_idx")
            c1, c2, c3 = st.columns(3)
            bold = c1.checkbox("Bold", key="tool_fmt_bold")
            italic = c2.checkbox("Italic", key="tool_fmt_italic")
            underline = c3.checkbox("Underline", key="tool_fmt_underline")
            font_size = st.number_input("Font size (pt, 0=skip)", 0.0, 72.0, 0.0,
                                        key="tool_fmt_size")
            alignment = st.selectbox("Alignment", ["(skip)", "left", "center", "right", "justify"],
                                     key="tool_fmt_align")
            if st.button("Apply Formatting", key="btn_fmt"):
                body = {}
                if bold:
                    body["bold"] = True
                if italic:
                    body["italic"] = True
                if underline:
                    body["underline"] = True
                if font_size > 0:
                    body["font_size"] = font_size
                if alignment != "(skip)":
                    body["alignment"] = alignment
                r = api("put", f"/documents/{fname}/paragraphs/{idx}/format", json=body)
                if r:
                    st.json(r)

        elif tool == "Set Paragraph Style":
            idx = st.number_input("Paragraph index", 0, 999, 0, key="tool_sty_idx")
            style = st.selectbox("Style", ["Normal", "Heading 1", "Heading 2", "Heading 3",
                                            "Heading 4", "Title", "List Bullet", "List Number",
                                            "Quote"], key="tool_sty_val")
            if st.button("Set Style", key="btn_style"):
                r = api("put", f"/documents/{fname}/paragraphs/{idx}/style",
                        json={"style": style})
                if r:
                    st.success(r.get("message", "Done"))

        elif tool == "Set Paragraph Alignment":
            idx = st.number_input("Paragraph index", 0, 999, 0, key="tool_align_idx")
            align = st.selectbox("Alignment", ["left", "center", "right", "justify"],
                                 key="tool_align_val")
            if st.button("Set Alignment", key="btn_align"):
                r = api("put", f"/documents/{fname}/paragraphs/{idx}/align",
                        json={"alignment": align})
                if r:
                    st.success(r.get("message", "Done"))

        elif tool == "Delete Document":
            st.warning(f"⚠️ This will permanently delete **{fname}**!")
            if st.button("🗑️ Delete Document", key="btn_del_doc", type="primary"):
                r = api("delete", f"/documents/{fname}")
                if r:
                    st.success(r.get("message", "Deleted"))
                    st.session_state.selected_doc = None
                    time.sleep(0.5)
                    st.rerun()
