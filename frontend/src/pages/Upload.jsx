import React, { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { UploadCloud, File, X, ArrowRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '../components/Button';
import { StepProgress } from '../components/StepProgress';
import useAppStore from '../store/useAppStore';

const steps = ["Upload", "Configure", "Process", "LaTeX", "Agent"];

export function Upload() {
    const navigate = useNavigate();
    const { uploadedFile, setUploadedFile, removeFile, setStep } = useAppStore();
    const [isDragging, setIsDragging] = useState(false);
    const fileInputRef = useRef(null);

    // Initialize step on mount
    React.useEffect(() => {
        setStep(1);
    }, [setStep]);

    const handleDragOver = (e) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = (e) => {
        e.preventDefault();
        setIsDragging(false);
    };

    const handleDrop = (e) => {
        e.preventDefault();
        setIsDragging(false);

        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            const file = e.dataTransfer.files[0];
            if (file.name.endsWith('.docx') || file.name.endsWith('.pdf')) {
                setUploadedFile(file);
            } else {
                alert("Please upload a .docx or .pdf file.");
            }
        }
    };

    const handleFileInput = (e) => {
        if (e.target.files && e.target.files.length > 0) {
            setUploadedFile(e.target.files[0]);
        }
    };

    const handleNext = () => {
        setStep(2);
        navigate('/configure');
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="max-w-3xl mx-auto py-8 px-4"
        >
            <div className="text-center mb-10">
                <h1 className="text-4xl font-anton font-normal tracking-wide text-[var(--color-text-main)] mb-2">Upload Manuscript</h1>
                <p className="text-[var(--color-text-muted)]">Upload your `.docx` file to begin the automated formatting process.</p>
            </div>

            <StepProgress currentStep={1} steps={steps} />

            <div className="bg-white rounded-[var(--radius-xl)] shadow-[var(--shadow-card)] border border-[var(--color-surface-200)] p-8 md:p-12 mb-8 mt-12">
                <AnimatePresence mode="wait">
                    {!uploadedFile ? (
                        <motion.div
                            key="upload-zone"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className={`border-2 border-dashed rounded-[var(--radius-lg)] p-12 text-center transition-all ${isDragging ? 'border-[var(--color-primary-500)] bg-[var(--color-primary-50)]' : 'border-[var(--color-surface-300)] hover:bg-white'
                                } cursor-pointer`}
                            onDragOver={handleDragOver}
                            onDragLeave={handleDragLeave}
                            onDrop={handleDrop}
                            onClick={() => fileInputRef.current?.click()}
                        >
                            <input
                                type="file"
                                ref={fileInputRef}
                                onChange={handleFileInput}
                                accept=".docx,.pdf"
                                className="hidden"
                            />
                            <div className="mx-auto w-16 h-16 rounded-full bg-[var(--color-primary-100)] flex items-center justify-center mb-4">
                                <UploadCloud className="w-8 h-8 text-[var(--color-primary-600)]" />
                            </div>
                            <h3 className="text-lg font-medium text-[var(--color-text-main)] mb-1">
                                Drag and drop your manuscript (.docx) or click to upload
                            </h3>
                            <p className="text-sm text-[var(--color-text-muted)]">
                                Maximum file size 50MB. Word documents (.docx) preferred.
                            </p>
                        </motion.div>
                    ) : (
                        <motion.div
                            key="file-preview"
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.95 }}
                            className="flex flex-col items-center justify-center py-8"
                        >
                            <div className="w-24 h-24 bg-[var(--color-primary-50)] rounded-[var(--radius-xl)] flex items-center justify-center border border-[var(--color-primary-100)] shadow-sm mb-6">
                                <File className="w-12 h-12 text-[var(--color-primary-600)]" />
                            </div>
                            <h3 className="text-xl font-medium text-[var(--color-text-main)] mb-2 truncate max-w-xs">{uploadedFile.name}</h3>
                            <p className="text-sm text-[var(--color-text-muted)] mb-8">
                                {(uploadedFile.size / 1024 / 1024).toFixed(2)} MB • Uploaded just now
                            </p>

                            <div className="flex gap-4">
                                <Button variant="secondary" onClick={(e) => { e.stopPropagation(); removeFile(); }}>
                                    <X className="w-4 h-4 mr-2" /> Remove File
                                </Button>
                                <Button variant="primary" onClick={handleNext}>
                                    Analyze Document <ArrowRight className="w-4 h-4 ml-2" />
                                </Button>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </motion.div>
    );
}
