import React from 'react';
import { cn } from './Button';

export function Badge({ children, variant = 'default', className, ...props }) {
    const variants = {
        default: "bg-[var(--color-surface-200)] text-[var(--color-text-main)]",
        primary: "bg-[var(--color-primary-100)] text-[var(--color-primary-600)]",
        success: "bg-green-100 text-green-700",
        warning: "bg-yellow-100 text-yellow-700",
        danger: "bg-red-100 text-red-700",

        // Specific business logic variants
        Pending: "bg-[var(--color-surface-200)] text-[var(--color-text-muted)]",
        Running: "bg-[var(--color-surface-200)] text-[var(--color-primary-900)] animate-pulse border border-[var(--color-surface-300)]",
        Done: "bg-[var(--color-primary-50)] text-[var(--color-primary-600)] border border-[var(--color-primary-100)]",
        Low: "bg-blue-50 text-blue-600 border border-blue-200",
        Medium: "bg-yellow-50 text-yellow-600 border border-yellow-200",
        High: "bg-red-50 text-red-600 border border-red-200",
    };

    return (
        <span
            className={cn(
                "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-[var(--color-primary-500)] focus:ring-offset-2",
                variants[variant] || variants.default,
                className
            )}
            {...props}
        >
            {children}
        </span>
    );
}
