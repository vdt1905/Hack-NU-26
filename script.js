const BASE = "http://localhost:8080";

// ── Shorthand ────────────────────────────────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// ── Navigation ───────────────────────────────────────────────────────────
$$(".nav-item").forEach((item) => {
  item.addEventListener("click", () => showPanel(item.dataset.panel));
});

function showPanel(id) {
  $$(".nav-item").forEach((n) => n.classList.remove("active"));
  const navItem = document.querySelector(`.nav-item[data-panel="${id}"]`);
  if (navItem) navItem.classList.add("active");
  $$(".panel").forEach((p) => (p.style.display = "none"));
  const panel = $(`#p-${id}`);
  if (panel) panel.style.display = "block";
}

// ── API Caller ───────────────────────────────────────────────────────────
async function send(method, path, body = null) {
  const statusEl = $("#resp-status");
  const bodyEl = $("#resp-body");
  const timeEl = $("#resp-time");
  const methodEl = $("#resp-method");
  const durationEl = $("#resp-duration");

  bodyEl.innerHTML = '<pre style="text-align:center;color:var(--text2)"><span class="spinner"></span> Loading...</pre>';
  statusEl.style.display = "none";
  timeEl.style.display = "none";

  const start = performance.now();
  try {
    const opts = { method, headers: {} };
    if (body) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    const res = await fetch(`${BASE}${path}`, opts);
    const elapsed = Math.round(performance.now() - start);

    const contentType = res.headers.get("content-type") || "";
    let data;
    if (contentType.includes("json")) {
      data = await res.json();
    } else if (contentType.includes("html")) {
      data = await res.text();
    } else {
      data = await res.text();
    }

    // Show status
    statusEl.style.display = "inline-block";
    statusEl.textContent = res.status;
    statusEl.className = "status-badge " + (res.status < 300 ? "status-2xx" : res.status < 500 ? "status-4xx" : "status-5xx");

    // Show body
    if (typeof data === "object") {
      bodyEl.innerHTML = `<pre>${syntaxHighlight(JSON.stringify(data, null, 2))}</pre>`;
    } else if (contentType.includes("html")) {
      bodyEl.innerHTML = `<pre>${escapeHtml(data)}</pre>`;
    } else {
      bodyEl.innerHTML = `<pre>${escapeHtml(data)}</pre>`;
    }

    // Show timing
    timeEl.style.display = "flex";
    methodEl.textContent = `${method} ${path}`;
    durationEl.textContent = `${elapsed}ms`;

    return { status: res.status, data };
  } catch (err) {
    statusEl.style.display = "inline-block";
    statusEl.textContent = "ERR";
    statusEl.className = "status-badge status-5xx";
    bodyEl.innerHTML = `<pre style="color:var(--red)">⚠ Network Error\n\n${err.message}\n\nIs the server running at ${BASE}?</pre>`;
    timeEl.style.display = "none";
  }
}

// ── Syntax highlighting ──────────────────────────────────────────────────
function syntaxHighlight(json) {
  json = escapeHtml(json);
  return json.replace(
    /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
    (match) => {
      let cls = "color:#ae81ff"; // number
      if (/^"/.test(match)) {
        cls = /:$/.test(match) ? "color:#a6e22e" : "color:#e6db74"; // key : string
      } else if (/true|false/.test(match)) {
        cls = "color:#66d9ef";
      } else if (/null/.test(match)) {
        cls = "color:#f92672";
      }
      return `<span style="${cls}">${match}</span>`;
    }
  );
}

function escapeHtml(str) {
  return str.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

// ── Document selectors ───────────────────────────────────────────────────
async function refreshDocs() {
  try {
    const res = await fetch(`${BASE}/documents`);
    const docs = await res.json();
    const options = docs.map(d => `<option value="${d.filename}">${d.filename}</option>`).join("");
    $$(".doc-select").forEach(sel => { sel.innerHTML = options || '<option value="">No documents</option>'; });
  } catch (e) {
    $$(".doc-select").forEach(sel => { sel.innerHTML = '<option value="">Server unavailable</option>'; });
  }
}

// Refresh on load
refreshDocs();

// ── Upload ───────────────────────────────────────────────────────────────
async function uploadFile() {
  const fileInput = $("#upload-file");
  if (!fileInput.files.length) return alert("Select a .docx file first.");
  const form = new FormData();
  form.append("file", fileInput.files[0]);

  const statusEl = $("#resp-status");
  const bodyEl = $("#resp-body");
  bodyEl.innerHTML = '<pre style="text-align:center;color:var(--text2)"><span class="spinner"></span> Uploading...</pre>';

  const start = performance.now();
  try {
    const res = await fetch(`${BASE}/documents/upload`, { method: "POST", body: form });
    const data = await res.json();
    const elapsed = Math.round(performance.now() - start);

    statusEl.style.display = "inline-block";
    statusEl.textContent = res.status;
    statusEl.className = "status-badge " + (res.ok ? "status-2xx" : "status-4xx");
    bodyEl.innerHTML = `<pre>${syntaxHighlight(JSON.stringify(data, null, 2))}</pre>`;
    $("#resp-time").style.display = "flex";
    $("#resp-method").textContent = "POST /documents/upload";
    $("#resp-duration").textContent = `${elapsed}ms`;
    refreshDocs();
  } catch (e) {
    bodyEl.innerHTML = `<pre style="color:var(--red)">Upload failed: ${e.message}</pre>`;
  }
}

// ── Download ─────────────────────────────────────────────────────────────
function downloadDoc() {
  const filename = $("#download-doc").value;
  if (!filename) return;
  const a = document.createElement("a");
  a.href = `${BASE}/documents/${filename}/download`;
  a.download = filename;
  a.click();
  send("GET", `/documents/${filename}/download`);
}

// ── Preview ──────────────────────────────────────────────────────────────
async function fetchPreview() {
  const filename = $("#preview-doc").value;
  if (!filename) return;
  const frame = $("#preview-frame");
  try {
    const res = await fetch(`${BASE}/documents/${filename}/preview`);
    const html = await res.text();
    frame.innerHTML = html;
    frame.style.display = "block";
    // Also update response panel
    send("GET", `/documents/${filename}/preview`);
  } catch (e) {
    frame.innerHTML = `<p style="color:red">Error: ${e.message}</p>`;
    frame.style.display = "block";
  }
}

// ── Add Table ────────────────────────────────────────────────────────────
function addTable() {
  const doc = $("#addt-doc").value;
  const rows = +$("#addt-rows").value;
  const cols = +$("#addt-cols").value;
  const dataStr = $("#addt-data").value.trim();
  let data = null;
  if (dataStr) {
    try { data = JSON.parse(dataStr); } catch { return alert("Invalid JSON for table data."); }
  }
  send("POST", `/documents/${doc}/tables`, { rows, cols, data });
}

// ── Format Paragraph ─────────────────────────────────────────────────────
function formatPara() {
  const doc = $("#fmtp-doc").value;
  const idx = $("#fmtp-idx").value;
  const body = {};
  if ($("#fmtp-bold").checked) body.bold = true;
  if ($("#fmtp-italic").checked) body.italic = true;
  if ($("#fmtp-underline").checked) body.underline = true;
  if ($("#fmtp-strike").checked) body.strikethrough = true;
  if ($("#fmtp-size").value) body.font_size = +$("#fmtp-size").value;
  if ($("#fmtp-font").value) body.font_name = $("#fmtp-font").value;
  if ($("#fmtp-color").value) body.font_color = $("#fmtp-color").value;
  if ($("#fmtp-align").value) body.alignment = $("#fmtp-align").value;
  if ($("#fmtp-style").value) body.style = $("#fmtp-style").value;
  send("PUT", `/documents/${doc}/paragraphs/${idx}/format`, body);
}

// ── Format Matching Text ─────────────────────────────────────────────────
function formatMatchText() {
  const doc = $("#fmtt-doc").value;
  const body = { search_text: $("#fmtt-search").value };
  if ($("#fmtt-bold").checked) body.bold = true;
  if ($("#fmtt-italic").checked) body.italic = true;
  if ($("#fmtt-underline").checked) body.underline = true;
  if ($("#fmtt-strike").checked) body.strikethrough = true;
  if ($("#fmtt-size").value) body.font_size = +$("#fmtt-size").value;
  if ($("#fmtt-color").value) body.font_color = $("#fmtt-color").value;
  if ($("#fmtt-hl").value) body.highlight_color = $("#fmtt-hl").value;
  send("POST", `/documents/${doc}/format-text`, body);
}

// ── Chat ─────────────────────────────────────────────────────────────────
let chatSessionId = null;

async function sendChat() {
  const input = $("#chat-input");
  const msg = input.value.trim();
  if (!msg) return;
  input.value = "";

  const messages = $("#chat-messages");
  messages.innerHTML += `<div class="chat-msg user">${escapeHtml(msg)}</div>`;
  messages.scrollTop = messages.scrollHeight;

  // Show loading
  const loadingId = "loading-" + Date.now();
  messages.innerHTML += `<div class="chat-msg bot" id="${loadingId}"><span class="spinner"></span> Thinking...</div>`;
  messages.scrollTop = messages.scrollHeight;

  try {
    const body = {
      message: msg,
      user_id: $("#chat-user").value || "test_user",
    };
    if (chatSessionId) body.session_id = chatSessionId;
    if ($("#chat-session").value) body.session_id = $("#chat-session").value;

    const res = await fetch(`${BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();

    // Remove loading
    const loadEl = document.getElementById(loadingId);
    if (loadEl) loadEl.remove();

    if (res.ok) {
      chatSessionId = data.session_id;
      $("#chat-session").value = chatSessionId;
      messages.innerHTML += `<div class="chat-msg bot">${formatMarkdown(data.response)}</div>`;
    } else {
      messages.innerHTML += `<div class="chat-msg bot" style="color:var(--red)">Error: ${data.detail || JSON.stringify(data)}</div>`;
    }

    // Also show in response panel
    const statusEl = $("#resp-status");
    statusEl.style.display = "inline-block";
    statusEl.textContent = res.status;
    statusEl.className = "status-badge " + (res.ok ? "status-2xx" : "status-4xx");
    $("#resp-body").innerHTML = `<pre>${syntaxHighlight(JSON.stringify(data, null, 2))}</pre>`;
    $("#resp-time").style.display = "flex";
    $("#resp-method").textContent = "POST /chat";
    $("#resp-duration").textContent = "";
  } catch (e) {
    const loadEl = document.getElementById(loadingId);
    if (loadEl) loadEl.remove();
    messages.innerHTML += `<div class="chat-msg bot" style="color:var(--red)">⚠ ${e.message}</div>`;
  }
  messages.scrollTop = messages.scrollHeight;
}

// Simple markdown-ish formatting
function formatMarkdown(text) {
  let safe = escapeHtml(text);
  safe = safe.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  safe = safe.replace(/\*(.+?)\*/g, "<em>$1</em>");
  safe = safe.replace(/`([^`]+)`/g, '<code style="background:var(--surface);padding:2px 5px;border-radius:3px;font-size:12px;">$1</code>');
  safe = safe.replace(/\n/g, "<br>");
  return safe;
}