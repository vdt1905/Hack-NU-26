import { create } from 'zustand';

const useAppStore = create((set) => ({
    // File State
    uploadedFile: null,
    setUploadedFile: (file) => set({ uploadedFile: file }),
    removeFile: () => set({ uploadedFile: null }),

    // Pipeline State
    currentStep: 1, // 1: Upload, 2: Configure, 3: Process, 4: LaTeX, 5: Agent
    setStep: (step) => set({ currentStep: step }),

    // Form Config State
    targetStyle: 'apa7',
    setTargetStyle: (style) => set({ targetStyle: style }),
    llmEngine: 'llama-3.3-70b-versatile',
    setLlmEngine: (engine) => set({ llmEngine: engine }),

    // Static formatting result
    formattedFile: null,       // filename of the statically formatted .docx
    setFormattedFile: (name) => set({ formattedFile: name }),
    complianceScore: null,
    setComplianceScore: (score) => set({ complianceScore: score }),

    // Editor Content (markdown preview of formatted doc)
    originalContent: "",
    setOriginalContent: (content) => set({ originalContent: content }),
    convertedContent: "",
    setConvertedContent: (content) => set({ convertedContent: content }),

    // LaTeX Content
    latexContent: "",
    setLatexContent: (content) => set({ latexContent: content || "" }),

    // Logs
    processLogs: [],
    addProcessLog: (log) => set((state) => ({ processLogs: [...state.processLogs, log] })),
    clearProcessLogs: () => set({ processLogs: [] }),

    // MCP Agent chat
    mcpSessionId: null,
    setMcpSessionId: (id) => set({ mcpSessionId: id }),
}));

export default useAppStore;
