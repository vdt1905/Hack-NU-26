import React from 'react';
import { Bot, Sparkles, Check } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from './Button';
import { Badge } from './Badge';
import { ComplianceGauge } from './ComplianceGauge';
import { useToast } from './Toasts';
import useAppStore from '../store/useAppStore';

export function SuggestionPanel() {
    const { suggestions, removeSuggestion, validationSummary, setValidationSummary } = useAppStore();
    const { toast } = useToast();

    const handleApplyFix = (id, title) => {
        // Remove suggestion
        removeSuggestion(id);

        // Simulate updating score
        setValidationSummary({
            ...validationSummary,
            score: Math.min(100, validationSummary.score + Math.floor(Math.random() * 5) + 2)
        });

        // Show toast
        toast({
            title: 'Fix applied',
            description: `Successfully applied: ${title}`,
            variant: 'success'
        });
    };

    return (
        <div className="flex flex-col h-full bg-white rounded-[var(--radius-lg)] border border-[var(--color-surface-300)] shadow-sm overflow-hidden">

            {/* Header */}
            <div className="p-4 border-b border-[var(--color-surface-200)] bg-[var(--color-surface-50)] flex items-center justify-between">
                <h2 className="font-semibold text-[var(--color-text-main)] flex items-center gap-2">
                    <Bot className="h-5 w-5 text-[var(--color-primary-600)]" />
                    FormatForge Agent
                </h2>
                <Badge variant={validationSummary.score === 100 ? 'success' : 'default'}>
                    {suggestions.length} issues
                </Badge>
            </div>

            <div className="flex-1 overflow-y-auto p-0">

                {/* Gauge Section */}
                <div className="py-6 border-b border-[var(--color-surface-200)] bg-gradient-to-b from-white to-[var(--color-surface-50)]">
                    <ComplianceGauge score={validationSummary.score} className="mx-auto" />
                </div>

                {/* Suggestions List */}
                <div className="p-4">
                    <h3 className="text-sm font-semibold text-[var(--color-text-main)] mb-3 flex items-center gap-2">
                        <Sparkles className="h-4 w-4 text-purple-500" /> Prioritized Fixes
                    </h3>

                    <div className="space-y-3">
                        <AnimatePresence>
                            {suggestions.length === 0 ? (
                                <motion.div
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    className="flex flex-col items-center justify-center py-8 text-center text-[var(--color-text-muted)] border border-dashed border-[var(--color-surface-300)] rounded-lg bg-[var(--color-surface-50)]"
                                >
                                    <Check className="h-8 w-8 text-green-500 mb-2" />
                                    <p className="text-sm font-medium">All clear!</p>
                                    <p className="text-xs">No formatting suggestions remaining.</p>
                                </motion.div>
                            ) : (
                                suggestions.map((suggestion) => (
                                    <motion.div
                                        key={suggestion.id}
                                        layout
                                        initial={{ opacity: 0, scale: 0.95 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        exit={{ opacity: 0, scale: 0.95, height: 0, marginBottom: 0 }}
                                        transition={{ duration: 0.2 }}
                                        className="p-3 bg-white border border-[var(--color-surface-200)] rounded-[var(--radius-md)] shadow-sm group hover:border-[var(--color-primary-300)] hover:shadow-md transition-all"
                                    >
                                        <div className="flex justify-between items-start mb-2">
                                            <h4 className="text-sm font-semibold text-[var(--color-text-main)] leading-tight">{suggestion.title}</h4>
                                            <Badge variant={suggestion.severity} className="text-[10px] px-1.5 py-0">
                                                {suggestion.severity}
                                            </Badge>
                                        </div>
                                        <p className="text-xs text-[var(--color-text-muted)] mb-3">
                                            {suggestion.description}
                                        </p>
                                        <Button
                                            size="sm"
                                            variant="secondary"
                                            className="w-full text-xs h-7 py-0 group-hover:bg-[var(--color-primary-50)] group-hover:text-[var(--color-primary-600)] group-hover:border-[var(--color-primary-200)]"
                                            onClick={() => handleApplyFix(suggestion.id, suggestion.title)}
                                        >
                                            <Sparkles className="h-3 w-3 mr-1.5" /> Apply Fix
                                        </Button>
                                    </motion.div>
                                ))
                            )}
                        </AnimatePresence>
                    </div>
                </div>
            </div>
        </div>
    );
}
