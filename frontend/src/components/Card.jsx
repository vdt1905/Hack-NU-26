import React from 'react';
import { cn } from './Button';

export function Card({ className, children, ...props }) {
    return (
        <div
            className={cn("notion-card", className)}
            {...props}
        >
            {children}
        </div>
    );
}

export function CardHeader({ className, children, ...props }) {
    return (
        <div
            className={cn("flex flex-col space-y-1.5 p-6", className)}
            {...props}
        >
            {children}
        </div>
    );
}

export function CardTitle({ className, children, ...props }) {
    return (
        <h3
            className={cn("font-semibold leading-none tracking-tight", className)}
            {...props}
        >
            {children}
        </h3>
    );
}

export function CardDescription({ className, children, ...props }) {
    return (
        <p
            className={cn("text-sm text-[var(--color-text-muted)]", className)}
            {...props}
        >
            {children}
        </p>
    );
}

export function CardContent({ className, children, ...props }) {
    return (
        <div className={cn("p-6 pt-0", className)} {...props}>
            {children}
        </div>
    );
}

export function CardFooter({ className, children, ...props }) {
    return (
        <div
            className={cn("flex items-center p-6 pt-0 border-t border-[var(--color-surface-200)]", className)}
            {...props}
        >
            {children}
        </div>
    );
}
