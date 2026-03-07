import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Play, CheckCircle2, ArrowRight, Download } from 'lucide-react';
import { motion } from 'framer-motion';
import { Button } from '../components/Button';
import { Card, CardContent } from '../components/Card';
import { Progress } from '../components/Progress';
import { StepProgress } from '../components/StepProgress';
import useAppStore from '../store/useAppStore';

const steps = ["Upload", "Configure", "Process", "LaTeX", "Agent"];

export function Process() {
    const navigate = useNavigate();
    const {
        setStep,
        processLogs,
        addProcessLog,
        clearProcessLogs,
        uploadedFile,
        targetStyle,
        llmEngine,
        setLatexContent,
        setFormattedFile,
        setComplianceScore,
    } = useAppStore();

    const [processingProgress, setProcessingProgress] = useState(0);
    const [isProcessingDone, setIsProcessingDone] = useState(false);
    const [currentStage, setCurrentStage] = useState(0);
    const [formattedFilename, setFormattedFilename] = useState(null);

    useEffect(() => {
        setStep(3);
        clearProcessLogs();

        let isMounted = true;

        const startProcessing = async () => {
            if (!uploadedFile) {
                const now = new Date();
                addProcessLog({ time: now.toLocaleTimeString(), message: "Error: No file uploaded. Go back to Upload step." });
                setIsProcessingDone(true);
                return;
            }

            const formData = new FormData();
            formData.append('file', uploadedFile);
            formData.append('style', targetStyle);
            formData.append('model', llmEngine);

            try {
                const response = await fetch('http://127.0.0.1:8000/api/v2/pipeline/stream', {
                    method: 'POST',
                    body: formData
                });

                if (!response.body) throw Error('ReadableStream not supported');

                const reader = response.body.getReader();
                const decoder = new TextDecoder("utf-8");

                let done = false;
                let buffer = "";
                let logCount = 0;

                while (!done) {
                    const { value, done: readerDone } = await reader.read();
                    done = readerDone;

                    if (value) {
                        buffer += decoder.decode(value, { stream: true });
                    }

                    const chunks = buffer.split("\n\n");
                    buffer = chunks.pop();

                    for (const chunk of chunks) {
                        if (chunk.trim() === "") continue;

                        if (chunk.startsWith("data: ")) {
                            try {
                                const jsonStr = chunk.substring(6);
                                const payload = JSON.parse(jsonStr);

                                if (payload.stage && isMounted) {
                                    setCurrentStage(payload.stage);
                                }

                                if (payload.log && isMounted) {
                                    const now = new Date();
                                    addProcessLog({ time: now.toLocaleTimeString(), message: payload.log });
                                    logCount++;

                                    // Progress: stage 1 = 0-60%, stage 2 = 60-95%
                                    if (payload.stage === 1) {
                                        setProcessingProgress(Math.min(60, logCount * 6));
                                    } else if (payload.stage === 2) {
                                        setProcessingProgress(Math.min(95, 60 + (logCount - 10) * 8));
                                    }
                                }

                                if (payload.stage_complete === 1 && isMounted) {
                                    setProcessingProgress(60);
                                }

                                if (payload.compliance_score && isMounted) {
                                    setComplianceScore(payload.compliance_score);
                                }

                                if (payload.formatted_file && isMounted) {
                                    setFormattedFile(payload.formatted_file);
                                    setFormattedFilename(payload.formatted_file);
                                }

                                if (payload.is_final && isMounted) {
                                    if (payload.latex) {
                                        setLatexContent(payload.latex);
                                    }
                                    setProcessingProgress(100);
                                    setIsProcessingDone(true);
                                }

                                if (payload.error && isMounted) {
                                    throw new Error(payload.error);
                                }
                            } catch (err) {
                                if (err.message && !err.message.includes('JSON')) {
                                    const now = new Date();
                                    addProcessLog({ time: now.toLocaleTimeString(), message: `Error: ${err.message}` });
                                    setIsProcessingDone(true);
                                }
                            }
                        }
                    }
                }
            } catch (error) {
                if (isMounted) {
                    const now = new Date();
                    addProcessLog({ time: now.toLocaleTimeString(), message: `Error: ${error.message}` });
                    setIsProcessingDone(true);
                }
            }
        };

        startProcessing();

        return () => {
            isMounted = false;
        };
    }, []);

    const handleDownloadFormatted = () => {
        if (formattedFilename) {
            window.open(`http://127.0.0.1:8000/api/v2/download/${formattedFilename}`, '_blank');
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="max-w-3xl mx-auto py-8 px-4"
        >
            <div className="text-center mb-10">
                <h1 className="text-4xl font-anton font-normal tracking-wide text-[var(--color-text-main)] mb-2">Processing Document</h1>
                <p className="text-[var(--color-text-muted)]">
                    {currentStage === 0 && "Initializing pipeline..."}
                    {currentStage === 1 && "Stage 1: Static formatting engine (6-agent pipeline)"}
                    {currentStage === 2 && "Stage 2: LLM-based LaTeX generation"}
                </p>
            </div>

            <StepProgress currentStep={3} steps={steps} />

            <Card className="mt-12">
                <CardContent className="pt-8 pb-8 px-8">

                    <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-semibold text-[var(--color-text-main)] flex items-center gap-2">
                            {isProcessingDone ? <CheckCircle2 className="h-5 w-5 text-[var(--color-primary-600)]" /> : <Play className="h-5 w-5 text-[var(--color-primary-500)] animate-pulse" />}
                            {isProcessingDone ? "Pipeline Complete" : "Processing..."}
                        </span>
                        <span className="text-sm font-medium text-[var(--color-text-muted)]">{processingProgress}%</span>
                    </div>

                    <Progress value={processingProgress} className="mb-8" />

                    {/* Stage indicator */}
                    <div className="flex gap-3 mb-4">
                        <div className={`flex-1 h-1.5 rounded-full transition-colors ${currentStage >= 1 ? 'bg-[var(--color-primary-500)]' : 'bg-[var(--color-surface-200)]'}`} />
                        <div className={`flex-1 h-1.5 rounded-full transition-colors ${currentStage >= 2 ? 'bg-[var(--color-primary-500)]' : 'bg-[var(--color-surface-200)]'}`} />
                    </div>
                    <div className="flex justify-between text-xs text-[var(--color-text-muted)] mb-6">
                        <span>Static Formatting</span>
                        <span>LaTeX Generation</span>
                    </div>

                    {/* Terminal / Log Output */}
                    <div className="bg-gray-900 rounded-[var(--radius-lg)] p-4 h-64 overflow-y-auto font-mono text-sm leading-relaxed border border-gray-800 shadow-inner">
                        {processLogs.map((log, index) => (
                            <motion.div
                                key={index}
                                initial={{ opacity: 0, x: -10 }}
                                animate={{ opacity: 1, x: 0 }}
                                className="flex gap-4 mb-1"
                            >
                                <span className="text-[var(--color-text-muted)] shrink-0 select-none">[{log.time}]</span>
                                <span className={`${index === processLogs.length - 1 && !isProcessingDone ? 'text-green-400' : 'text-gray-300'}`}>
                                    {log.message}
                                </span>
                            </motion.div>
                        ))}
                        {!isProcessingDone && (
                            <motion.div
                                initial={{ opacity: 0 }}
                                animate={{ opacity: [0, 1, 0] }}
                                transition={{ repeat: Infinity, duration: 1 }}
                                className="mt-1 inline-block w-2 h-4 bg-green-400"
                            />
                        )}
                    </div>

                </CardContent>
            </Card>

            {isProcessingDone && (
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex justify-between mt-6"
                >
                    {formattedFilename && (
                        <Button onClick={handleDownloadFormatted} size="lg" variant="secondary">
                            <Download className="w-4 h-4 mr-2" /> Download Formatted DOCX
                        </Button>
                    )}
                    <Button onClick={() => navigate('/latex')} size="lg" variant="primary">
                        Open LaTeX Editor <ArrowRight className="w-4 h-4 ml-2" />
                    </Button>
                </motion.div>
            )}

        </motion.div>
    );
}
