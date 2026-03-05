"""
FormatForge AI — Streamlit Frontend
Upload manuscript → Select style → Format → Download.
"""

import asyncio
import json
import logging
import tempfile
from pathlib import Path

import streamlit as st

# ── Page config ──────────────────────────────────────────────

st.set_page_config(
    page_title="FormatForge AI — Agent Paperpal",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────

st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
    }
    .score-card {
        background: #f0f2f6;
        border-radius: 10px;
        padding: 1.2rem;
        text-align: center;
    }
    .change-applied { color: #28a745; }
    .change-warning { color: #ffc107; }
    .change-error   { color: #dc3545; }
</style>
""", unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────

st.markdown('<h1 class="main-header">🎓 FormatForge AI — Agent Paperpal</h1>', unsafe_allow_html=True)
st.markdown(
    '<p style="text-align:center;color:gray;">Agentic Manuscript Formatting System | HackaMined 2026</p>',
    unsafe_allow_html=True,
)

# ── Sidebar ──────────────────────────────────────────────────

with st.sidebar:
    st.header("📤 Upload & Configure")

    uploaded_file = st.file_uploader(
        "Upload Manuscript",
        type=["docx"],
        help="Upload a .docx manuscript file",
    )

    style_choice = st.selectbox(
        "Select Style Guide",
        options=["APA 7th Edition", "Vancouver", "IEEE"],
        index=0,
    )

    STYLE_MAP = {
        "APA 7th Edition": "apa7",
        "Vancouver": "vancouver",
        "IEEE": "ieee",
    }

    custom_guidelines = st.text_area(
        "Or paste custom guidelines…",
        height=120,
        help="Paste journal formatting guidelines for LLM interpretation.",
    )

    st.divider()

    process_btn = st.button("🚀 Format Document", type="primary", use_container_width=True)

    st.divider()
    st.caption("Built for HackaMined 2026 — Cactus Communications / Paperpal")

# ── Main processing logic ────────────────────────────────────

if process_btn and uploaded_file:
    # Save uploaded file to temp directory
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        tmp.write(uploaded_file.getbuffer())
        tmp_path = Path(tmp.name)

    style_id = STYLE_MAP.get(style_choice, "apa7")
    guidelines = custom_guidelines.strip() if custom_guidelines else None

    # Run pipeline
    with st.spinner("⚙️ Processing manuscript…"):
        try:
            from backend.agents.orchestrator import Orchestrator

            orchestrator = Orchestrator()
            result = asyncio.run(orchestrator.run(
                input_path=tmp_path,
                style_id=style_id,
                guidelines_text=guidelines,
            ))

        except Exception as exc:
            st.error(f"❌ Pipeline error: {exc}")
            st.stop()
        finally:
            tmp_path.unlink(missing_ok=True)

    if not result.success:
        st.error(f"❌ Formatting failed: {result.error_message}")
        st.stop()

    # ── Display Results ──────────────────────────────────────

    st.success(f"✅ Formatted in {result.processing_time_seconds}s")

    col1, col2, col3 = st.columns([1, 1, 1])

    # ── Column 1: Structure View ─────────────────────────────
    with col1:
        st.subheader("📄 Detected Structure")

        structure = result.structure_summary
        if structure:
            for role, count in sorted(structure.items()):
                emoji = {
                    "title": "📌",
                    "author_info": "👤",
                    "abstract_label": "📝",
                    "abstract_body": "📝",
                    "heading_1": "📋",
                    "heading_2": "📋",
                    "heading_3": "📋",
                    "body": "📄",
                    "reference_label": "📚",
                    "reference_entry": "📚",
                    "keywords": "🏷️",
                }.get(role, "•")
                st.write(f"{emoji} **{role}**: {count}")
        else:
            st.info("No structure detected.")

    # ── Column 2: Compliance Score ───────────────────────────
    with col2:
        st.subheader("📊 Compliance Score")

        report = result.compliance_report
        overall = report.overall_score

        # Large score display
        color = "#28a745" if overall >= 80 else "#ffc107" if overall >= 60 else "#dc3545"
        st.markdown(
            f'<div class="score-card">'
            f'<h1 style="color:{color};margin:0;">{overall:.1f}%</h1>'
            f'<p style="margin:0;">Overall Compliance</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

        st.write("")

        # Category breakdown
        for cat in report.categories:
            pct = cat.score
            bar_color = "🟢" if pct >= 80 else "🟡" if pct >= 60 else "🔴"
            st.write(f"{bar_color} **{cat.category}**: {pct:.0f}%")
            st.progress(pct / 100)

    # ── Column 3: Changes Log ────────────────────────────────
    with col3:
        st.subheader("📝 Changes Made")

        changes = report.changes
        if changes:
            for c in changes:
                icon = "✅" if c.status.value == "applied" else "⚠️" if c.status.value == "skipped" else "❌"
                rule_str = f" — {c.rule_reference}" if c.rule_reference else ""
                st.write(f"{icon} {c.description}{rule_str}")
        else:
            st.info("No changes recorded.")

        if report.warnings:
            st.subheader("⚠️ Warnings")
            for w in report.warnings:
                st.warning(w)

        if report.errors:
            st.subheader("❌ Errors")
            for e in report.errors:
                st.error(e)

    # ── Download buttons ─────────────────────────────────────
    st.divider()
    dcol1, dcol2, dcol3 = st.columns(3)

    with dcol1:
        if result.output_filename and Path(result.output_filename).exists():
            with open(result.output_filename, "rb") as f:
                st.download_button(
                    "📥 Download Formatted DOCX",
                    data=f,
                    file_name=Path(result.output_filename).name,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )

    with dcol2:
        report_json = json.dumps(report.model_dump(mode="json"), indent=2)
        st.download_button(
            "📊 Download Compliance Report",
            data=report_json,
            file_name="compliance_report.json",
            mime="application/json",
            use_container_width=True,
        )

    with dcol3:
        cit_json = json.dumps(result.citation_report.model_dump(mode="json"), indent=2)
        st.download_button(
            "🔗 Download Citation Report",
            data=cit_json,
            file_name="citation_report.json",
            mime="application/json",
            use_container_width=True,
        )

elif not uploaded_file:
    # Landing page
    st.info("👈 Upload a manuscript (.docx) in the sidebar to get started.")

    st.markdown("""
    ### How It Works
    1. **Upload** your research manuscript (.docx)
    2. **Select** the target style guide (APA 7, Vancouver, IEEE)
    3. **Click** "Format Document"
    4. **Download** the publication-ready formatted DOCX + compliance report

    ### Architecture
    | Agent | Role |
    |-------|------|
    | 🔍 Ingest & Parse | DOCX → Internal Representation |
    | 📖 Rule Interpreter | Guidelines → Formatting Rules |
    | 🏗️ Structure Detector | Label paragraphs with roles |
    | 🔗 Citation Engine | Parse, format, validate citations |
    | 🎨 Transformer | Apply formatting rules to DOCX |
    | ✅ Validator | Compliance scoring & explanations |
    """)
