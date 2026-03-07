import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Send, Bot, User, Loader2, FileText, Download, Eye, RefreshCw } from 'lucide-react';
import { Button } from '../components/Button';
import useAppStore from '../store/useAppStore';

const MCP_API = 'http://localhost:8082';

export function McpAgent() {
    const { mcpSessionId, setMcpSessionId, formattedFile } = useAppStore();
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [documents, setDocuments] = useState([]);
    const [mcpHealthy, setMcpHealthy] = useState(null);
    const [previewDoc, setPreviewDoc] = useState(null); // filename being previewed
    const [previewHtml, setPreviewHtml] = useState('');
    const [previewLoading, setPreviewLoading] = useState(false);
    const messagesEndRef = useRef(null);
    const inputRef = useRef(null);

    const autoContextSent = useRef(false);

    useEffect(() => {
        checkHealth();
        fetchDocuments();
    }, []);

    // Auto-send context message when formatted file exists so DocBot knows which file to edit
    useEffect(() => {
        if (formattedFile && mcpHealthy && !autoContextSent.current && messages.length === 0) {
            autoContextSent.current = true;
            const contextMsg = `[Working on file: ${formattedFile}] I have uploaded a formatted document called "${formattedFile}". Please use this file for all edits. Start by confirming you can access it and summarize its structure.`;
            setInput('');
            setMessages([{ role: 'user', content: contextMsg }]);
            setLoading(true);
            (async () => {
                try {
                    const res = await fetch(`${MCP_API}/chat`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            message: contextMsg,
                            user_id: 'formatforge_user',
                            session_id: mcpSessionId || undefined,
                        }),
                    });
                    const data = await res.json();
                    if (data.session_id && !mcpSessionId) {
                        setMcpSessionId(data.session_id);
                    }
                    setMessages(prev => [...prev, { role: 'assistant', content: data.response || data.detail || 'No response.' }]);
                    fetchDocuments();
                } catch (err) {
                    setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.message}` }]);
                } finally {
                    setLoading(false);
                }
            })();
        }
    }, [formattedFile, mcpHealthy]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const checkHealth = async () => {
        try {
            const res = await fetch(`${MCP_API}/health`);
            const data = await res.json();
            setMcpHealthy(data.agent_available);
        } catch {
            setMcpHealthy(false);
        }
    };

    const fetchDocuments = async () => {
        try {
            const res = await fetch(`${MCP_API}/documents`);
            const data = await res.json();
            // API returns raw array of {filename, size_bytes, modified}
            const docs = Array.isArray(data) ? data : (data.documents || []);
            setDocuments(docs);
            // Auto-preview the formatted file if no preview is active yet
            if (!previewDoc && formattedFile) {
                const match = docs.find(d => (d.filename || d) === formattedFile);
                if (match) loadPreview(formattedFile);
            } else if (!previewDoc && docs.length > 0) {
                const firstFile = docs[0].filename || docs[0];
                loadPreview(firstFile);
            }
        } catch {
            // MCP server might not be running
        }
    };

    const loadPreview = async (filename) => {
        setPreviewDoc(filename);
        setPreviewLoading(true);
        try {
            const res = await fetch(`${MCP_API}/documents/${encodeURIComponent(filename)}/preview`);
            if (res.ok) {
                const html = await res.text();
                setPreviewHtml(html);
            } else {
                setPreviewHtml(`<p style="color:red;padding:20px;">Failed to load preview for ${filename}</p>`);
            }
        } catch (err) {
            setPreviewHtml(`<p style="color:red;padding:20px;">Error: ${err.message}</p>`);
        } finally {
            setPreviewLoading(false);
        }
    };

    const refreshPreview = () => {
        if (previewDoc) loadPreview(previewDoc);
    };

    const sendMessage = async () => {
        if (!input.trim() || loading) return;

        const userMsg = input.trim();
        setInput('');
        setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
        setLoading(true);

        try {
            const res = await fetch(`${MCP_API}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: userMsg,
                    user_id: 'formatforge_user',
                    session_id: mcpSessionId || undefined,
                }),
            });

            const data = await res.json();
            if (data.session_id && !mcpSessionId) {
                setMcpSessionId(data.session_id);
            }

            setMessages(prev => [...prev, { role: 'assistant', content: data.response || data.detail || 'No response.' }]);

            // Refresh document list and preview after each interaction (agent may have modified docs)
            fetchDocuments();
            if (previewDoc) loadPreview(previewDoc);
        } catch (err) {
            setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.message}. Make sure MCP server is running on port 8082.` }]);
        } finally {
            setLoading(false);
            inputRef.current?.focus();
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="h-[calc(100vh-4rem)] flex flex-col overflow-hidden"
        >
            {/* Compact Header */}
            <div className="text-center py-3 px-4 shrink-0 border-b border-[var(--color-surface-200)] bg-white">
                <h1 className="text-2xl font-anton font-normal tracking-wide text-[var(--color-text-main)]">
                    AI Document Agent
                </h1>
                <p className="text-xs text-[var(--color-text-muted)]">
                    Preview your formatted document and chat with DocBot to edit it in real-time.
                </p>
            </div>

            {/* Main 3-column layout: Documents | Preview | Chat */}
            <div className="flex flex-1 min-h-0 overflow-hidden">

                {/* Left: Documents Panel */}
                <div className="w-52 shrink-0 hidden lg:flex flex-col bg-white border-r border-[var(--color-surface-200)] overflow-hidden">
                    <div className="px-3 py-2 border-b border-[var(--color-surface-200)] shrink-0">
                        <h3 className="text-xs font-bold text-[var(--color-text-main)] flex items-center gap-1.5">
                            <FileText className="w-3.5 h-3.5" /> Documents
                        </h3>
                        <div className={`mt-1.5 px-2 py-1 rounded text-[10px] font-medium ${mcpHealthy === true ? 'bg-green-50 text-green-700' : mcpHealthy === false ? 'bg-red-50 text-red-700' : 'bg-gray-50 text-gray-500'}`}>
                            {mcpHealthy === true ? '● Online' : mcpHealthy === false ? '● Offline' : '● Checking...'}
                        </div>
                    </div>

                    <div className="flex-1 overflow-y-auto p-2 space-y-1">
                        {documents.length === 0 ? (
                            <p className="text-[10px] text-[var(--color-text-muted)] italic py-4 text-center">No documents yet.</p>
                        ) : (
                            documents.map((doc, i) => {
                                const fname = typeof doc === 'string' ? doc : doc.filename;
                                const isActive = fname === previewDoc;
                                return (
                                    <div
                                        key={i}
                                        className={`flex items-center gap-1.5 p-1.5 rounded-md text-[11px] font-medium transition-colors cursor-pointer ${
                                            isActive
                                                ? 'bg-[var(--color-primary-50)] text-[var(--color-primary-700)] border border-[var(--color-primary-200)]'
                                                : 'bg-[var(--color-surface-50)] hover:bg-[var(--color-surface-100)] text-[var(--color-text-main)]'
                                        }`}
                                        onClick={() => loadPreview(fname)}
                                    >
                                        <FileText className="w-3 h-3 shrink-0 text-[var(--color-primary-500)]" />
                                        <span className="truncate">{fname}</span>
                                    </div>
                                );
                            })
                        )}
                    </div>

                    <div className="p-2 border-t border-[var(--color-surface-200)] shrink-0">
                        <p className="text-[9px] text-[var(--color-text-muted)] leading-relaxed">
                            Click a document to preview it. Use the chat to make edits.
                        </p>
                    </div>
                </div>

                {/* Center: Document Preview */}
                <div className="flex-1 flex flex-col bg-[var(--color-surface-50)] border-r border-[var(--color-surface-200)] overflow-hidden min-w-0">
                    <div className="flex items-center justify-between px-4 py-2 border-b border-[var(--color-surface-200)] bg-white shrink-0">
                        <div className="flex items-center gap-2">
                            <Eye className="h-4 w-4 text-[var(--color-text-muted)]" />
                            <span className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-main)]">
                                {previewDoc ? `Preview: ${previewDoc}` : 'Document Preview'}
                            </span>
                        </div>
                        {previewDoc && (
                            <div className="flex items-center gap-2">
                                <button
                                    onClick={refreshPreview}
                                    className="p-1 rounded hover:bg-[var(--color-surface-100)] transition-colors"
                                    title="Refresh preview"
                                >
                                    <RefreshCw className={`w-3.5 h-3.5 text-[var(--color-text-muted)] ${previewLoading ? 'animate-spin' : ''}`} />
                                </button>
                                <a
                                    href={`${MCP_API}/documents/${encodeURIComponent(previewDoc)}/download`}
                                    className="text-[10px] font-medium text-[var(--color-primary-600)] hover:text-[var(--color-primary-700)] flex items-center gap-1"
                                >
                                    <Download className="w-3 h-3" /> Download
                                </a>
                            </div>
                        )}
                    </div>

                    <div className="flex-1 overflow-auto bg-white">
                        {!previewDoc ? (
                            <div className="flex flex-col items-center justify-center h-full text-center py-16">
                                <FileText className="h-12 w-12 mb-3 text-[var(--color-surface-300)]" />
                                <p className="text-sm font-medium text-[var(--color-text-muted)]">No document selected</p>
                                <p className="text-xs text-[var(--color-text-muted)] mt-1">Select a document from the sidebar to preview</p>
                            </div>
                        ) : previewLoading ? (
                            <div className="flex items-center justify-center h-full">
                                <Loader2 className="w-6 h-6 animate-spin text-[var(--color-primary-500)]" />
                            </div>
                        ) : (
                            <iframe
                                srcDoc={previewHtml}
                                className="w-full h-full border-none"
                                title="Document Preview"
                                sandbox="allow-same-origin"
                                style={{ minHeight: '100%' }}
                            />
                        )}
                    </div>
                </div>

                {/* Right: Chat Panel */}
                <div className="w-[420px] shrink-0 flex flex-col bg-white overflow-hidden">
                    <div className="px-4 py-2 border-b border-[var(--color-surface-200)] shrink-0">
                        <div className="flex items-center gap-2">
                            <Bot className="w-4 h-4 text-[var(--color-primary-500)]" />
                            <span className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-main)]">DocBot Chat</span>
                        </div>
                    </div>

                    {/* Messages */}
                    <div className="flex-1 overflow-y-auto p-4 space-y-3">
                        {messages.length === 0 && (
                            <div className="flex flex-col items-center justify-center h-full text-center py-8">
                                <div className="w-12 h-12 bg-[var(--color-primary-50)] rounded-xl flex items-center justify-center mb-3">
                                    <Bot className="w-6 h-6 text-[var(--color-primary-500)]" />
                                </div>
                                <h3 className="text-base font-bold text-[var(--color-text-main)] mb-1">DocBot is ready</h3>
                                <p className="text-xs text-[var(--color-text-muted)] max-w-xs">
                                    {formattedFile
                                        ? `"${formattedFile}" is loaded. Ask me to edit, restructure, or refine it.`
                                        : 'I can create, edit, format, search, and manage your .docx documents.'
                                    }
                                </p>
                                <div className="flex flex-wrap gap-1.5 mt-4 justify-center">
                                    {(formattedFile ? [
                                        "Summarize the document structure",
                                        "Check APA 7 compliance",
                                        "List all headings",
                                        "Format all headings bold",
                                    ] : [
                                        "Create a new document",
                                        "List all documents",
                                        "Format headings bold",
                                        "Search for 'introduction'",
                                    ]).map(suggestion => (
                                        <button
                                            key={suggestion}
                                            className="px-2.5 py-1 text-[10px] font-medium bg-[var(--color-surface-100)] hover:bg-[var(--color-surface-200)] text-[var(--color-text-main)] rounded-full transition-colors"
                                            onClick={() => { setInput(suggestion); inputRef.current?.focus(); }}
                                        >
                                            {suggestion}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}

                        {messages.map((msg, i) => (
                            <motion.div
                                key={i}
                                initial={{ opacity: 0, y: 6 }}
                                animate={{ opacity: 1, y: 0 }}
                                className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                            >
                                {msg.role === 'assistant' && (
                                    <div className="w-6 h-6 rounded-full bg-[var(--color-primary-100)] flex items-center justify-center shrink-0 mt-0.5">
                                        <Bot className="w-3 h-3 text-[var(--color-primary-600)]" />
                                    </div>
                                )}
                                <div className={`max-w-[85%] rounded-xl px-3 py-2 text-xs leading-relaxed whitespace-pre-wrap ${
                                    msg.role === 'user'
                                        ? 'bg-[var(--color-primary-500)] text-white rounded-br-sm'
                                        : 'bg-[var(--color-surface-100)] text-[var(--color-text-main)] rounded-bl-sm'
                                }`}>
                                    {msg.content}
                                </div>
                                {msg.role === 'user' && (
                                    <div className="w-6 h-6 rounded-full bg-[var(--color-surface-200)] flex items-center justify-center shrink-0 mt-0.5">
                                        <User className="w-3 h-3 text-[var(--color-text-muted)]" />
                                    </div>
                                )}
                            </motion.div>
                        ))}

                        {loading && (
                            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-2">
                                <div className="w-6 h-6 rounded-full bg-[var(--color-primary-100)] flex items-center justify-center shrink-0">
                                    <Loader2 className="w-3 h-3 text-[var(--color-primary-600)] animate-spin" />
                                </div>
                                <div className="bg-[var(--color-surface-100)] rounded-xl rounded-bl-sm px-3 py-2">
                                    <div className="flex gap-1">
                                        <span className="w-1.5 h-1.5 bg-[var(--color-text-muted)] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                        <span className="w-1.5 h-1.5 bg-[var(--color-text-muted)] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                        <span className="w-1.5 h-1.5 bg-[var(--color-text-muted)] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                                    </div>
                                </div>
                            </motion.div>
                        )}

                        <div ref={messagesEndRef} />
                    </div>

                    {/* Input */}
                    <div className="border-t border-[var(--color-surface-200)] p-3 shrink-0">
                        <div className="flex gap-2">
                            <textarea
                                ref={inputRef}
                                rows={1}
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyDown={handleKeyDown}
                                placeholder={previewDoc ? `Edit "${previewDoc}"...` : "Ask DocBot..."}
                                className="flex-1 resize-none rounded-lg border border-[var(--color-surface-300)] bg-white px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-[var(--color-primary-500)] focus:border-transparent"
                                disabled={loading}
                            />
                            <Button
                                variant="primary"
                                onClick={sendMessage}
                                disabled={loading || !input.trim()}
                                className="rounded-lg px-3"
                            >
                                <Send className="w-3.5 h-3.5" />
                            </Button>
                        </div>
                    </div>
                </div>
            </div>
        </motion.div>
    );
}
