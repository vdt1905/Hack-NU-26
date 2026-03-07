import React from 'react';
import { cn } from './Button';

export function Progress({ value = 0, className, ...props }) {
    // Ensure value is between 0 and 100
    const clampedValue = Math.min(100, Math.max(0, value));

    return (
        <div
            className={cn("relative h-4 w-full overflow-hidden rounded-full bg-[var(--color-surface-200)]", className)}
            {...props}
            role="progressbar"
            aria-valuemin="0"
            aria-valuemax="100"
            aria-valuenow={clampedValue}
        >
            <div
                className="h-full w-full flex-1 bg-[var(--color-primary-600)] transition-all duration-500 ease-in-out"
                style={{ transform: `translateX(-${100 - clampedValue}%)` }}
            />
        </div>
    );
}
