import React, { useRef, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Editor from '@monaco-editor/react';
import { Play, FileDown, Code, FileText, CheckCircle, ImagePlus, X, ListOrdered, ChevronRight, ChevronDown, ArrowRight } from 'lucide-react';
import { Button } from '../components/Button';
import useAppStore from '../store/useAppStore';

export function Latex() {
    const navigate = useNavigate();
    const { latexContent, setLatexContent, setStep } = useAppStore();
    const formRef = useRef(null);
    const editorRef = useRef(null);
    const [compiling, setCompiling] = useState(false);
    const [compiled, setCompiled] = useState(false);
    const [assets, setAssets] = useState([]);
    const [outline, setOutline] = useState([]);
    const [expandedSections, setExpandedSections] = useState({});

    // Parse LaTeX content for sections
    useEffect(() => {
        if (!latexContent) {
            setOutline([]);
            return;
        }

        const lines = latexContent.split('\n');
        const newOutline = [];

        // Regex to match \section{title}, \subsection{title}, \subsubsection{title}
        const sectionRegex = /^\\(sub)*section\*?\{([^}]+)\}/;

        lines.forEach((line, index) => {
            const match = line.trim().match(sectionRegex);
            if (match) {
                const level = match[1] ? match[1].length / 3 + 1 : 1; // section=1, subsection=2, subsubsection=3
                const title = match[2];
                newOutline.push({
                    title,
                    level,
                    line: index + 1, // Monaco lines are 1-indexed
                    id: `sec-${index}`
                });
            }
        });

        setOutline(newOutline);
    }, [latexContent]);

    const handleOutlineClick = (lineNumber) => {
        if (editorRef.current) {
            editorRef.current.revealLineInCenter(lineNumber);
            editorRef.current.setPosition({ lineNumber, column: 1 });
            editorRef.current.focus();
        }
    };

    const toggleSection = (id) => {
        setExpandedSections(prev => ({
            ...prev,
            [id]: !prev[id]
        }));
    };

    const handleFileUpload = (e) => {
        if (e.target.files && e.target.files.length > 0) {
            const newFiles = Array.from(e.target.files);
            setAssets(prev => {
                const existingNames = new Set(prev.map(f => f.name));
                const uniqueNewFiles = newFiles.filter(f => !existingNames.has(f.name));
                return [...prev, ...uniqueNewFiles];
            });
        }
        // Force the input to clear so the same file sequence can be uploaded again if deleted
        e.target.value = '';
    };

    const handleDragOver = (e) => {
        e.preventDefault();
        e.stopPropagation();
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            const newFiles = Array.from(e.dataTransfer.files);
            setAssets(prev => {
                const existingNames = new Set(prev.map(f => f.name));
                const uniqueNewFiles = newFiles.filter(f => !existingNames.has(f.name));
                return [...prev, ...uniqueNewFiles];
            });
        }
    };

    const removeAsset = (indexToRemove) => {
        setAssets(prev => prev.filter((_, idx) => idx !== indexToRemove));
    };

    // Robust pre-processor to handle improperly nested document structures
    const sanitizeLatex = (code) => {
        // Extract the preamble (everything before the first \begin{document})
        const beginDocRegex = /\\begin\{document\}/;
        const firstBeginIndex = code.search(beginDocRegex);
        let preamble = "";
        let restOfCode = code;

        if (firstBeginIndex !== -1) {
            preamble = code.substring(0, firstBeginIndex);
            restOfCode = code.substring(firstBeginIndex);
        } else {
            // No begin document found, might just be snippets
            return `\\documentclass{article}\n\\begin{document}\n${code}\n\\end{document}`;
        }

        // Clean up preamble: keep ONLY the first \documentclass
        let hasDocClass = false;
        let docClassLine = '';
        preamble = preamble.split('\n').filter(line => {
            if (line.trim().startsWith('\\documentclass')) {
                if (hasDocClass) return false;
                hasDocClass = true;
                docClassLine = line.trim();
                return true;
            }
            return true;
        }).join('\n');

        if (!hasDocClass) {
            preamble = '\\documentclass{article}\n' + preamble;
            docClassLine = '\\documentclass{article}';
        }

        const isIEEE = /IEEEtran/.test(docClassLine);

        // Fix conflicting packages: natbib and biblatex cannot coexist
        const hasNatbib = /\\usepackage(\[.*?\])?\{natbib\}/.test(preamble);
        const hasBiblatex = /\\usepackage(\[.*?\])?\{biblatex\}/.test(preamble);
        if (hasNatbib && hasBiblatex) {
            preamble = preamble.replace(/\\usepackage(\[.*?\])?\{biblatex\}\n?/g, '');
        }

        // IEEE: remove geometry (IEEEtran handles its own margins)
        if (isIEEE) {
            preamble = preamble.replace(/\\usepackage(\[.*?\])?\{geometry\}\n?/g, '');
            // remove natbib for IEEE (use cite instead)
            preamble = preamble.replace(/\\usepackage(\[.*?\])?\{natbib\}\n?/g, '');
            // remove setspace/doublespacing (IEEE is single-spaced)
            preamble = preamble.replace(/\\usepackage(\[.*?\])?\{setspace\}\n?/g, '');
            preamble = preamble.replace(/\\doublespacing\n?/g, '');
            // remove indentfirst (IEEE handles its own indentation)
            preamble = preamble.replace(/\\usepackage(\[.*?\])?\{indentfirst\}\n?/g, '');
            // remove times (IEEEtran uses its own font setup)
            preamble = preamble.replace(/\\usepackage(\[.*?\])?\{times\}\n?/g, '');
            // remove subcaption (conflicts with IEEEtran subfig handling)
            preamble = preamble.replace(/\\usepackage(\[.*?\])?\{subcaption\}\n?/g, '');
        }

        // Remove duplicate usepackage lines
        const seenPackages = new Set();
        preamble = preamble.split('\n').filter(line => {
            const pkgMatch = line.trim().match(/^\\usepackage(\[.*?\])?\{(.+?)\}$/);
            if (pkgMatch) {
                const pkg = pkgMatch[2];
                if (seenPackages.has(pkg)) return false;
                seenPackages.add(pkg);
            }
            return true;
        }).join('\n');

        // Strip ALL structural tags from the body
        let body = restOfCode.replace(/\\begin\{document\}/g, '');
        body = body.replace(/\\end\{document\}/g, '');
        body = body.replace(/\\documentclass(\[.*?\])?\{.*?\}/g, '');

        // Fix \printbibliography when using natbib (not biblatex)
        if (hasNatbib && !hasBiblatex) {
            body = body.replace(/\\printbibliography/g, '');
        }

        // Remove empty abstract environments
        body = body.replace(/\\begin\{abstract\}\s*\\end\{abstract\}/g, '');

        // Fix: convert \section{Abstract} to \begin{abstract}...\end{abstract}
        body = body.replace(
            /\\section\*?\{Abstract\}\s*\n([\s\S]*?)(?=\\section(?:\*?\{)|\\begin\{thebibliography|$)/i,
            (match, content) => {
                const trimmed = content.trim();
                if (!trimmed) return '';
                return `\\begin{abstract}\n${trimmed}\n\\end{abstract}\n\n`;
            }
        );

        // Extract any \usepackage that got trapped in the body content
        const packageRegex = /\\(usepackage|usetikzlibrary)(\[.*?\])?\{.*?\}/g;
        let packagesToHoist = "";

        let pkgMatch;
        while ((pkgMatch = packageRegex.exec(body)) !== null) {
            packagesToHoist += pkgMatch[0] + "\n";
        }
        body = body.replace(packageRegex, '');

        // Remove stray \parindent / \setlength from body that belong in preamble
        const preambleCommands = /\\(setlength|setcounter|renewcommand)\{[^}]*\}\{[^}]*\}/g;
        let cmdMatch;
        while ((cmdMatch = preambleCommands.exec(body)) !== null) {
            if (body.indexOf(cmdMatch[0]) < 200) {  // only if near top of body
                packagesToHoist += cmdMatch[0] + "\n";
            }
        }
        body = body.substring(0, 200).replace(preambleCommands, '') + body.substring(200);

        // Clean up excessive blank lines
        body = body.replace(/\n{4,}/g, '\n\n\n');

        return `${preamble}\n${packagesToHoist}\n\\begin{document}\n${body}\n\\end{document}`;
    };

    const handleCompile = React.useCallback(() => {
        if (!formRef.current) return;

        setCompiling(true);

        const form = formRef.current;

        // Clean up any previously added dynamic file inputs
        const oldDynamicInputs = form.querySelectorAll('.dynamic-asset');
        oldDynamicInputs.forEach(el => el.remove());

        // Inject the sanitized code right before submission
        const hiddenInput = form.querySelector('input[name="filecontents[]"]');
        if (hiddenInput) {
            hiddenInput.value = sanitizeLatex(latexContent);
        }

        // Add file inputs for assets
        assets.forEach((file) => {
            const nameInput = document.createElement('input');
            nameInput.type = 'hidden';
            nameInput.name = 'filename[]';
            nameInput.value = file.name;
            nameInput.className = 'dynamic-asset';
            form.appendChild(nameInput);

            const fileInput = document.createElement('input');
            fileInput.type = 'file';
            fileInput.name = 'filecontents[]';
            fileInput.className = 'dynamic-asset';

            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(file);
            fileInput.files = dataTransfer.files;

            form.appendChild(fileInput);
        });

        // The form submission causes the browser to navigate the iframe, bypassing CORS
        // and avoiding the 431 Request Length Limit by using a POST request body.
        form.submit();

        // Emulate compilation time to improve UX
        setTimeout(() => {
            setCompiling(false);
            setCompiled(true);
        }, 1500);
    }, [latexContent, assets, setCompiling, setCompiled, sanitizeLatex]);

    useEffect(() => {
        const handleKeyDown = (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                handleCompile();
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [handleCompile]);

    return (
        <div className="flex flex-col h-[calc(100vh-4rem)] w-full bg-[var(--color-surface-50)]">

            {/* Header / Toolbar */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 py-3 px-6 bg-white border-b border-[var(--color-surface-300)] shadow-sm shrink-0">
                <div>
                    <h1 className="text-xl font-bold tracking-tight text-[var(--color-text-main)] flex items-center gap-2">
                        <Code className="h-6 w-6 text-[var(--color-primary-500)]" />
                        LaTeX Environment
                    </h1>
                    <p className="text-sm text-[var(--color-text-muted)]">Edit and compile your source code securely.</p>
                </div>

                <div className="flex items-center gap-3">
                    {compiled && !compiling && (
                        <span className="text-sm font-medium text-green-600 flex items-center gap-1.5 mr-4 px-3 py-1 bg-green-50 rounded-full border border-green-200">
                            <CheckCircle className="h-4 w-4" /> Ready
                        </span>
                    )}
                    <Button
                        variant="primary"
                        onClick={handleCompile}
                        disabled={compiling}
                        className="shadow-sm font-semibold h-10 px-6"
                    >
                        {compiling ? (
                            <>
                                <span className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                                Compiling...
                            </>
                        ) : (
                            <>
                                <Play className="h-4 w-4 mr-2 fill-current" /> Compile PDF
                            </>
                        )}
                    </Button>
                </div>
            </div>

            {/* Split Workspace */}
            <div className="flex flex-1 flex-row min-h-0 bg-[var(--color-surface-100)]">

                {/* Outline Sidebar (Left) */}
                <div className="hidden md:flex flex-col w-64 bg-[#1e1e1e] border-r border-[#333] shrink-0 text-[#cccccc] overflow-hidden select-none">
                    <div className="flex items-center px-4 py-3 border-b border-[#333] shrink-0">
                        <ListOrdered className="h-4 w-4 mr-2" />
                        <span className="text-xs font-semibold uppercase tracking-wider">File Outline</span>
                    </div>

                    <div className="flex-1 overflow-y-auto py-2">
                        {outline.length === 0 ? (
                            <div className="px-4 py-4 text-xs text-[#888] italic text-center">
                                No sections found. Use \section&#123;...&#125; to build an outline.
                            </div>
                        ) : (
                            <div className="flex flex-col">
                                {outline.map((item, index) => {
                                    // Calculate precise indentation based on level (1, 2, 3)
                                    const indentClass = item.level === 1 ? 'pl-4' : item.level === 2 ? 'pl-8' : 'pl-12';
                                    const fontSizeClass = item.level === 1 ? 'text-[13px] font-medium text-white' : item.level === 2 ? 'text-[12px] text-[#e0e0e0]' : 'text-[11px] text-[#b0b0b0]';
                                    const isExpanded = expandedSections[item.id] !== false; // Default true

                                    // Check if this item has children
                                    const hasChildren = index < outline.length - 1 && outline[index + 1].level > item.level;

                                    return (
                                        <div key={item.id} className="group relative">
                                            {/* Active/Hover Background styled to match VS Code outline */}
                                            <div
                                                className={`flex items-center w-full py-1 cursor-pointer hover:bg-[#2a2d2e] transition-colors ${indentClass}`}
                                                onClick={() => handleOutlineClick(item.line)}
                                            >
                                                {/* Left border indicator for sections */}
                                                {item.level === 1 && (
                                                    <div className="absolute left-0 top-0 bottom-0 w-[2px] bg-transparent group-hover:bg-[#007acc]"></div>
                                                )}

                                                <div
                                                    className="w-4 h-4 mr-1 flex items-center justify-center shrink-0"
                                                    onClick={(e) => {
                                                        if (hasChildren) {
                                                            e.stopPropagation();
                                                            toggleSection(item.id);
                                                        }
                                                    }}
                                                >
                                                    {hasChildren ? (
                                                        isExpanded ?
                                                            <ChevronDown className="h-3.5 w-3.5 text-[#888] hover:text-[#ccc]" /> :
                                                            <ChevronRight className="h-3.5 w-3.5 text-[#888] hover:text-[#ccc]" />
                                                    ) : (
                                                        <span className="w-3.5" /> // Spacer
                                                    )}
                                                </div>

                                                <span className={`${fontSizeClass} truncate pr-4 block`} title={item.title}>
                                                    {item.title}
                                                </span>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                </div>

                {/* Editor Section (Middle) */}
                <div
                    className="flex flex-col flex-1 lg:w-1/2 bg-white border-r border-[var(--color-surface-300)] overflow-hidden"
                    onDragOver={handleDragOver}
                    onDrop={handleDrop}
                >
                    <div className="flex items-center justify-between px-4 py-2 border-b border-[var(--color-surface-200)] bg-[var(--color-surface-50)] shrink-0">
                        <div className="flex items-center gap-2">
                            <FileText className="h-4 w-4 text-[var(--color-text-muted)]" />
                            <span className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-main)]">main.tex</span>
                        </div>
                        <div>
                            <input
                                type="file"
                                accept="image/*, .sty, .bib, .cls"
                                multiple
                                onChange={handleFileUpload}
                                className="hidden"
                                id="asset-upload"
                            />
                            <label
                                htmlFor="asset-upload"
                                className="cursor-pointer flex items-center gap-1.5 px-2 py-1 text-xs font-medium text-[var(--color-primary-600)] bg-[var(--color-primary-50)] hover:bg-[var(--color-primary-100)] rounded transition-colors"
                                title="Click to upload or drag & drop files anywhere in the editor panel"
                            >
                                <ImagePlus className="h-4 w-4" /> Upload Multiple Images/Files
                            </label>
                        </div>
                    </div>

                    {assets.length > 0 && (
                        <div className="flex flex-wrap items-center gap-2 px-4 py-2 bg-[var(--color-surface-100)] border-b border-[var(--color-surface-200)] shrink-0">
                            {assets.map((file, idx) => (
                                <div key={idx} className="flex items-center gap-1.5 px-2 py-1 bg-white border border-[var(--color-surface-300)] rounded-md shadow-sm whitespace-nowrap">
                                    <span className="text-xs font-medium text-[var(--color-text-main)] max-w-[120px] truncate" title={file.name}>{file.name}</span>
                                    <button
                                        onClick={() => removeAsset(idx)}
                                        className="text-[var(--color-text-muted)] hover:text-red-500 transition-colors"
                                    >
                                        <X className="h-3 w-3" />
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}

                    <div className="flex-1 w-full relative">
                        <Editor
                            height="100%"
                            defaultLanguage="latex"
                            value={latexContent}
                            onChange={setLatexContent}
                            theme="vs-light"
                            onMount={(editor, monaco) => {
                                // Add editorRef capturing
                                editorRef.current = editor;

                                // Add a custom command that will dispatch a synthetic keydown
                                // event to the window so the `useEffect` hook with the fresh
                                // `handleCompile` closure in the broader component scope 
                                // catches it rather than grabbing a stale closure here.
                                editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
                                    window.dispatchEvent(
                                        new KeyboardEvent('keydown', {
                                            key: 'Enter',
                                            ctrlKey: true
                                        })
                                    );
                                });
                            }}
                            options={{
                                minimap: { enabled: false },
                                fontSize: 14,
                                wordWrap: 'on',
                                lineNumbers: 'on',
                                padding: { top: 16 },
                                scrollBeyondLastLine: false,
                                smoothScrolling: true,
                            }}
                        />
                    </div>
                </div>

                {/* PDF Preview Section (Right) */}
                <div className="flex flex-col flex-1 lg:w-1/2 bg-white overflow-hidden">
                    <div className="flex items-center justify-between px-4 py-2 border-b border-[var(--color-surface-200)] bg-[var(--color-surface-50)] shrink-0">
                        <div className="flex items-center gap-2">
                            <FileDown className="h-4 w-4 text-[var(--color-text-muted)]" />
                            <span className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-main)]">Preview</span>
                        </div>
                    </div>

                    <div className="flex-1 w-full bg-[#525659] relative">
                        {/* 
                            Important Note: We keep the iframe persistent and target it from the hidden form.
                            This handles all compilation requests safely and renders natively.
                        */}
                        <iframe
                            name="latex-pdf-preview"
                            className={`w-full h-full border-none transition-opacity duration-300 ${compiling ? 'opacity-50' : 'opacity-100'}`}
                            title="Compiled PDF"
                        />

                        {!compiled && !compiling && (
                            <div className="absolute inset-0 flex flex-col items-center justify-center text-white/70 bg-[#525659]">
                                <FileDown className="h-16 w-16 mb-4 opacity-50" />
                                <p className="text-lg font-medium">No PDF Generated</p>
                                <p className="text-sm mt-1">Write your LaTeX code and click Compile PDF</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Next Step: Agent Editing */}
            <div className="flex items-center justify-end px-4 py-3 border-t border-[var(--color-surface-200)] bg-[var(--color-surface-50)]">
                <Button
                    variant="primary"
                    onClick={() => { setStep(5); navigate('/agent'); }}
                    className="flex items-center gap-2"
                >
                    Next: Agent Editing <ArrowRight className="w-4 h-4" />
                </Button>
            </div>

            {/* Hidden Form for native POST compilation without CORS/URL limit issues */}
            <form
                action="https://texlive.net/cgi-bin/latexcgi"
                method="POST"
                encType="multipart/form-data"
                target="latex-pdf-preview"
                className="hidden"
                ref={formRef}
            >
                <input type="hidden" name="filecontents[]" value={latexContent} />
                <input type="hidden" name="filename[]" value="document.tex" />
                <input type="hidden" name="engine" value="pdflatex" />
                <input type="hidden" name="return" value="pdf" />
            </form>

        </div>
    );
}
