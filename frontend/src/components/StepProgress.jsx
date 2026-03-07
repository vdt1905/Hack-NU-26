import React from 'react';
import { Check } from 'lucide-react';
import { cn } from './Button';

export function StepProgress({ currentStep, steps }) {
    // Calculate how far along the bar should be filled (0% to 100%)
    const maxSteps = steps.length;
    const fillPercentage = maxSteps > 1 ? ((currentStep - 1) / (maxSteps - 1)) * 100 : 0;

    return (
        <div className="relative flex items-center justify-between w-full max-w-3xl mx-auto mb-16 mt-4 px-6 sm:px-10">
            {/* Continuous Background Line */}
            <div className="absolute left-[10%] right-[10%] top-5 h-1.5 bg-[var(--color-surface-200)] rounded-full z-0 overflow-hidden shadow-inner">
                {/* Animated Fill Line */}
                <div
                    className="h-full bg-[var(--color-primary-600)] transition-all duration-1000 ease-in-out relative shadow-sm"
                    style={{ width: `${fillPercentage}%` }}
                >
                    {/* Flowing Shimmer Effect */}
                    <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent w-full animate-shimmer"></div>
                </div>
            </div>

            {/* Step Circles */}
            {steps.map((step, index) => {
                const stepNumber = index + 1;
                const isActive = stepNumber === currentStep;
                const isCompleted = stepNumber < currentStep;

                return (
                    <div key={step} className="flex flex-col items-center relative z-10 w-20">
                        <div
                            className={cn(
                                "w-11 h-11 flex items-center justify-center rounded-full border-[3px] text-[15px] transition-all duration-500 font-extrabold",
                                isActive ? "bg-white border-[var(--color-primary-600)] text-[var(--color-primary-600)] shadow-lg scale-110 ring-4 ring-[var(--color-primary-50)]" :
                                    isCompleted ? "bg-[var(--color-primary-600)] border-[var(--color-primary-600)] text-white scale-100" :
                                        "bg-[var(--color-surface-50)] border-[var(--color-surface-300)] text-[var(--color-text-muted)] scale-100 shadow-sm"
                            )}
                        >
                            {isCompleted ? <Check className="w-5 h-5" strokeWidth={3} /> : stepNumber}
                        </div>
                        <span
                            className={cn(
                                "absolute top-14 text-[13px] font-bold whitespace-nowrap transition-colors duration-500",
                                isActive ? "text-[var(--color-text-main)]" :
                                    isCompleted ? "text-[var(--color-text-main)]" :
                                        "text-[var(--color-text-muted)]"
                            )}
                        >
                            {step}
                        </span>
                    </div>
                );
            })}
        </div>
    );
}
