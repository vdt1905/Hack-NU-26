import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Settings, Check, ArrowRight } from 'lucide-react';
import { motion } from 'framer-motion';
import { Button } from '../components/Button';
import { Card, CardContent } from '../components/Card';
import { StepProgress } from '../components/StepProgress';
import useAppStore from '../store/useAppStore';

const steps = ["Upload", "Configure", "Process", "LaTeX", "Agent"];

export function Configure() {
    const navigate = useNavigate();
    const { setStep, targetStyle, setTargetStyle, llmEngine, setLlmEngine } = useAppStore();

    const [selectedTemplate, setSelectedTemplate] = useState('IEEE Access');
    const [toggles, setToggles] = useState({
        autoFixCitations: true,
        reorderReferences: true,
        normalizeHeadings: true,
        applySpacing: true,
    });

    useEffect(() => {
        setStep(2);
    }, [setStep]);

    const handleNext = () => {
        setStep(3);
        navigate('/process');
    };

    const styles = [
        { id: 'apa7', label: 'APA 7th' },
        { id: 'ieee', label: 'IEEE' },
        { id: 'vancouver', label: 'Vancouver' },
        { id: 'mla', label: 'MLA' },
        { id: 'chicago', label: 'Chicago' },
    ];

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="max-w-3xl mx-auto py-8 px-4"
        >
            <div className="text-center mb-10">
                <h1 className="text-4xl font-anton font-normal tracking-wide text-[var(--color-text-main)] mb-2">Configure Processing</h1>
                <p className="text-[var(--color-text-muted)]">Select the target style and journal template for output formatting.</p>
            </div>

            <StepProgress currentStep={2} steps={steps} />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8 mt-12">

                {/* Target Style & Templates */}
                <Card>
                    <CardContent className="pt-6">
                        <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                            <Settings className="h-5 w-5 text-[var(--color-primary-500)]" /> Target Configuration
                        </h3>

                        <div className="mb-6">
                            <label className="block text-sm font-medium text-[var(--color-text-main)] mb-2">Target Style</label>
                            <div className="grid grid-cols-2 gap-2">
                                {styles.map(s => (
                                    <button
                                        key={s.id}
                                        onClick={() => setTargetStyle(s.id)}
                                        className={`flex items-center justify-between p-3 rounded-[var(--radius-md)] border text-sm font-medium transition-colors ${targetStyle === s.id
                                            ? 'border-[var(--color-primary-500)] bg-[var(--color-primary-50)] text-[var(--color-primary-600)]'
                                            : 'border-[var(--color-surface-300)] bg-white text-[var(--color-text-main)] hover:bg-white'
                                            }`}
                                    >
                                        {s.label}
                                        {targetStyle === s.id && <Check className="h-4 w-4" />}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div className="mb-6">
                            <label className="block text-sm font-medium text-[var(--color-text-main)] mb-2">LLM Engine</label>
                            <select
                                className="w-full rounded-[var(--radius-md)] border border-[var(--color-surface-300)] bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary-500)] focus:border-transparent"
                                value={llmEngine}
                                onChange={(e) => setLlmEngine(e.target.value)}
                            >
                                <option value="meta-llama/llama-4-maverick-17b-128e-instruct">LLaMA-4-Maverick 17b</option>
                                <option value="qwen/qwen3-32b">Qwen-3 32b</option>
                            </select>
                        </div>

                        {/* <div>
                            <label className="block text-sm font-medium text-[var(--color-text-main)] mb-2">Journal Template</label>
                            <select
                                className="w-full rounded-[var(--radius-md)] border border-[var(--color-surface-300)] bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary-500)] focus:border-transparent"
                                value={selectedTemplate}
                                onChange={(e) => setSelectedTemplate(e.target.value)}
                            >
                                {templates.map(template => (
                                    <option key={template} value={template}>{template}</option>
                                ))}
                            </select>
                        </div> */}
                    </CardContent>
                </Card>

                {/* Processing Options */}
                <Card>
                    <CardContent className="pt-6">
                        <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                            <Check className="h-5 w-5 text-[var(--color-primary-500)]" /> Processing Options
                        </h3>

                        <div className="space-y-4">
                            <ToggleOption
                                label="Auto fix citations"
                                checked={toggles.autoFixCitations}
                                onChange={() => setToggles(p => ({ ...p, autoFixCitations: !p.autoFixCitations }))}
                            />
                            <ToggleOption
                                label="Reorder references"
                                checked={toggles.reorderReferences}
                                onChange={() => setToggles(p => ({ ...p, reorderReferences: !p.reorderReferences }))}
                            />
                            <ToggleOption
                                label="Normalize headings"
                                checked={toggles.normalizeHeadings}
                                onChange={() => setToggles(p => ({ ...p, normalizeHeadings: !p.normalizeHeadings }))}
                            />
                            <ToggleOption
                                label="Apply spacing and margins"
                                checked={toggles.applySpacing}
                                onChange={() => setToggles(p => ({ ...p, applySpacing: !p.applySpacing }))}
                            />
                        </div>
                    </CardContent>
                </Card>

            </div>

            <div className="flex justify-end border-t border-[var(--color-surface-200)] pt-6">
                <Button onClick={handleNext} size="lg">
                    Start Processing <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
            </div>

        </motion.div>
    );
}

function ToggleOption({ label, checked, onChange }) {
    return (
        <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-[var(--color-text-main)]">{label}</span>
            <button
                type="button"
                onClick={onChange}
                className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-[var(--color-primary-500)] focus:ring-offset-2 ${checked ? 'bg-[var(--color-primary-600)]' : 'bg-gray-200'
                    }`}
                role="switch"
                aria-checked={checked}
            >
                <span
                    aria-hidden="true"
                    className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${checked ? 'translate-x-5' : 'translate-x-0'
                        }`}
                />
            </button>
        </div>
    );
}
