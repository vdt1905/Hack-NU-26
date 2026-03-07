import React, { useState, useEffect } from "react";
import "./LatexCompiler.css";

const defaultLatex = `\\documentclass{article}
\\usepackage{amsmath}
\\usepackage{graphicx}

\\title{A Beautiful LaTeX Example}
\\author{Powered by React}
\\date{\\today}

\\begin{document}
\\maketitle

\\section{Introduction}
Welcome to our sleek, web-based LaTeX compiler! 
This editor allows you to write LaTeX code on the left and see the compiled PDF on the right.

\\section{Mathematics}
Here is a beautiful equation:
\\begin{equation}
E = mc^2
\\end{equation}

And here is the quadratic formula:
\\begin{equation}
x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}
\\end{equation}

\\section{Conclusion}
Happy TeXing!

\\end{document}`;

const LatexCompiler = () => {
    const [latexCode, setLatexCode] = useState(defaultLatex);
    const [pdfUrl, setPdfUrl] = useState("");
    const [isCompiling, setIsCompiling] = useState(false);
    const [error, setError] = useState("");

    const compileLatex = async () => {
        setIsCompiling(true);
        setError("");
        try {
            // Using latexonline.cc for compilation
            const encodedText = encodeURIComponent(latexCode);
            const url = `/latex-api/compile?text=${encodedText}`;

            const response = await fetch(url);

            if (!response.ok) {
                // Attempt to parse compilation error from the response
                const errorText = await response.text();
                throw new Error(errorText || "Compilation failed");
            }

            // Convert response to a blob URL to display in iframe
            const blob = await response.blob();
            const objectUrl = URL.createObjectURL(blob);
            setPdfUrl(objectUrl);

        } catch (err) {
            console.error("Compilation Error:", err);
            // Typically the API returns logs in plain text if it fails
            // We limit the error display to prevent massive UI overflow
            const msg = err.message.substring(0, 1000) + (err.message.length > 1000 ? "..." : "");
            setError(msg || "An unknown error occurred during compilation.");
            setPdfUrl("");
        } finally {
            setIsCompiling(false);
        }
    };

    // Compile on mount
    useEffect(() => {
        compileLatex();
    }, []);

    return (
        <div className="compiler-container">
            <header className="compiler-header">
                <div className="logo-section">
                    <div className="tex-logo">TeX</div>
                    <h1>StudioWeb</h1>
                </div>
                <button
                    className={`compile-btn ${isCompiling ? "compiling" : ""}`}
                    onClick={compileLatex}
                    disabled={isCompiling}
                >
                    {isCompiling ? (
                        <>
                            <span className="spinner"></span> Compiling...
                        </>
                    ) : (
                        "Compile PDF"
                    )}
                </button>
            </header>

            <main className="editor-workspace">
                {/* Editor Pane */}
                <div className="pane editor-pane">
                    <div className="pane-header">
                        <span>Editor</span>
                        <span className="badge">LaTeX</span>
                    </div>
                    <textarea
                        className="latex-textarea"
                        value={latexCode}
                        onChange={(e) => setLatexCode(e.target.value)}
                        spellCheck="false"
                        placeholder="Enter your LaTeX code here..."
                    />
                </div>

                {/* Preview Pane */}
                <div className="pane preview-pane">
                    <div className="pane-header">
                        <span>Preview</span>
                        {isCompiling && <span className="badge compile-badge">Building...</span>}
                    </div>
                    <div className="preview-content">
                        {error ? (
                            <div className="error-container">
                                <h3>Compilation Error</h3>
                                <pre>{error}</pre>
                            </div>
                        ) : pdfUrl ? (
                            <iframe
                                src={pdfUrl}
                                title="PDF Preview"
                                className="pdf-viewer"
                            />
                        ) : (
                            <div className="empty-preview">
                                <div className="placeholder-icon">📄</div>
                                <p>Click "Compile PDF" to generate preview</p>
                            </div>
                        )}
                    </div>
                </div>
            </main>
        </div>
    );
};

export default LatexCompiler;
