import React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs) {
    return twMerge(clsx(inputs));
}

export function Button({
    children,
    variant = 'primary',
    size = 'md',
    className,
    ...props
}) {
    const baseStyles = "inline-flex items-center justify-center rounded-[var(--radius-md)] font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-[var(--color-primary-500)] focus:ring-offset-1 disabled:opacity-50 disabled:pointer-events-none shadow-sm";

    const variants = {
        primary: "bg-[var(--color-primary-600)] text-white hover:bg-[var(--color-primary-500)]",
        secondary: "bg-white text-[var(--color-text-main)] border border-[var(--color-surface-300)] hover:bg-white",
        ghost: "bg-transparent text-[var(--color-text-muted)] hover:bg-white hover:text-[var(--color-text-main)] shadow-none",
        danger: "bg-red-600 text-white hover:bg-red-500",
    };

    const sizes = {
        sm: "h-8 px-3 text-xs",
        md: "h-10 px-4 py-2 text-sm",
        lg: "h-12 px-6 py-3 text-base",
        icon: "h-10 w-10",
    };

    return (
        <button
            className={cn(baseStyles, variants[variant], sizes[size], className)}
            {...props}
        >
            {children}
        </button>
    );
}
