import React, { useState } from 'react';
import { Maximize2, Minimize2, Settings2, FileCode2 } from 'lucide-react';
import { RichTextEditor } from './RichTextEditor';
import { Tabs, TabsList, TabsTrigger } from './Tabs';
import { cn } from './Button';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import MDEditor from '@uiw/react-md-editor';
import rehypeSanitize from "rehype-sanitize";
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.css';

function unescapeMarkdown(text) {
    if (!text) return '';

    // 1. Trim leading and trailing whitespace completely
    let unescaped = text.trim();

    // 2. Unescape common HTML entities
    unescaped = unescaped
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&quot;/g, '"')
        .replace(/&#39;/g, "'")
        .replace(/&amp;/g, '&');

    // 3. Strip wrapping <pre><code> HTML tags, being generous with spaces/newlines
    // The (?:\s*<code[^>]*>)? matches an optional <code> tag and any spaces before it.
    unescaped = unescaped.replace(/^<pre>(?:\s*<code[^>]*>)?\s*/i, '');
    unescaped = unescaped.replace(/\s*(?:<\/code>\s*)?<\/pre>$/i, '');

    // 4. Strip rogue markdown codeblock wrappers if the LLM outputted them instead of HTML
    unescaped = unescaped.replace(/^```[a-z]*\s*\n/i, '');
    unescaped = unescaped.replace(/\n\s*```$/i, '');

    return unescaped;
}

export function SplitEditors({ originalContent, convertedContent, onConvertedChange }) {
    const [viewMode, setViewMode] = useState('editor'); // editor, preview

    return (
        <div className="flex flex-col h-full w-full rounded-[var(--radius-lg)] border border-[var(--color-surface-300)] bg-white shadow-sm overflow-hidden">

            {/* Editor Header / Controls */}
            <div className="flex items-center justify-between px-4 py-2 border-b border-[var(--color-surface-200)] bg-[var(--color-surface-50)]">
                <Tabs value={viewMode} onValueChange={setViewMode}>
                    <TabsList className="h-8">
                        <TabsTrigger value="editor" className="text-xs h-6 px-2">Editor</TabsTrigger>
                        <TabsTrigger value="preview" className="text-xs h-6 px-2">Preview</TabsTrigger>
                    </TabsList>
                </Tabs>

                <div className="flex items-center gap-2">
                    <button className="p-1.5 text-[var(--color-text-muted)] hover:bg-[var(--color-surface-200)] hover:text-[var(--color-text-main)] rounded-md transition-colors">
                        <Settings2 className="w-4 h-4" />
                    </button>
                    <button className="p-1.5 text-[var(--color-text-muted)] hover:bg-[var(--color-surface-200)] hover:text-[var(--color-text-main)] rounded-md transition-colors">
                        <Maximize2 className="w-4 h-4" />
                    </button>
                </div>
            </div>

            {/* Editors Area */}
            <div className="flex flex-1 overflow-hidden relative">

                {/* Left Panel: Raw Markdown */}
                <div className={cn(
                    "h-full overflow-hidden transition-all duration-300 ease-in-out border-r border-[var(--color-surface-200)] bg-[var(--color-surface-50)]",
                    viewMode === 'editor' ? "w-1/2 flex-shrink-0" : "w-0 border-none opacity-0"
                )}>
                    {viewMode === 'editor' && (
                        <div className="flex flex-col h-full">
                            <div className="px-4 py-2 bg-blue-50/50 border-b border-[var(--color-surface-200)] text-xs font-semibold text-[var(--color-primary-600)] uppercase tracking-wider sticky top-0 z-10 w-full flex justify-between items-center">
                                <span>Raw Markdown (Editable)</span>
                                <span className="flex h-2 w-2 relative">
                                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                                    <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
                                </span>
                            </div>
                            <div className="flex-1 overflow-hidden w-full relative">
                                <div className="absolute inset-0 overflow-y-auto scroll-smooth">
                                    <RichTextEditor
                                        content={convertedContent}
                                        onChange={onConvertedChange}
                                    />
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Right Panel: Markdown Preview */}
                <div className={cn(
                    "h-full overflow-hidden transition-all duration-300 ease-in-out",
                    viewMode === 'editor' ? "w-1/2 flex-shrink-0" :
                        viewMode === 'preview' ? "w-full" : "w-0 opacity-0"
                )}>
                    {(viewMode === 'editor' || viewMode === 'preview') && (
                        <div className="flex flex-col h-full bg-white">
                            <div className="px-4 py-2 bg-[var(--color-surface-50)] border-b border-[var(--color-surface-200)] text-xs font-semibold text-[var(--color-text-main)] uppercase tracking-wider sticky top-0 z-20 w-full flex justify-between items-center">
                                <span>Markdown Preview</span>
                                <FileCode2 className="w-4 h-4 text-[var(--color-text-muted)]" />
                            </div>
                            <div className="flex-1 overflow-hidden w-full relative">
                                <div className="absolute inset-0 overflow-y-auto scroll-smooth p-6" data-color-mode="light">
                                    <div className="max-w-none text-[var(--color-text-main)]">
                                        <MDEditor.Markdown
                                            source={unescapeMarkdown(convertedContent) || 'No markdown generated yet.'}
                                            rehypePlugins={[[rehypeSanitize], [rehypeKatex]]}
                                            remarkPlugins={[[remarkGfm], [remarkMath]]}
                                            style={{ background: 'transparent', color: 'var(--color-text-main)' }}
                                            components={{
                                                sup: ({ node, ...props }) => <sup style={{ fontSize: '0.7em', lineHeight: 0 }} {...props} />
                                            }}
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

            </div>
        </div>
    );
}
