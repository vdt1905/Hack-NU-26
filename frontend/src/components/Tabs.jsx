import React from 'react';
import { cn } from './Button';

export function Tabs({ defaultValue, value, onValueChange, children, className }) {
    const [activeTab, setActiveTab] = React.useState(defaultValue || value);

    // Controlled vs uncontrolled logic
    const currentTab = value !== undefined ? value : activeTab;

    const handleTabChange = (newVal) => {
        if (value === undefined) {
            setActiveTab(newVal);
        }
        if (onValueChange) {
            onValueChange(newVal);
        }
    };

    return (
        <div className={cn("w-full", className)}>
            {React.Children.map(children, child => {
                if (!React.isValidElement(child)) return child;
                return React.cloneElement(child, {
                    activeTab: currentTab,
                    onChange: handleTabChange
                });
            })}
        </div>
    );
}

export function TabsList({ children, className, activeTab, onChange }) {
    return (
        <div
            className={cn(
                "inline-flex h-10 items-center justify-center rounded-md bg-[var(--color-surface-200)] p-1 text-[var(--color-text-muted)] w-fit",
                className
            )}
        >
            {React.Children.map(children, child => {
                if (!React.isValidElement(child)) return child;
                return React.cloneElement(child, {
                    isActive: child.props.value === activeTab,
                    onClick: () => onChange(child.props.value)
                });
            })}
        </div>
    );
}

export function TabsTrigger({ value, children, className, isActive, onClick }) {
    return (
        <button
            type="button"
            onClick={onClick}
            className={cn(
                "inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-white transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary-500)] disabled:pointer-events-none disabled:opacity-50",
                isActive ? "bg-white text-[var(--color-text-main)] shadow-sm" : "hover:text-[var(--color-text-main)]",
                className
            )}
        >
            {children}
        </button>
    );
}

export function TabsContent({ value, children, className, activeTab }) {
    if (value !== activeTab) return null;

    return (
        <div
            className={cn(
                "mt-2 ring-offset-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary-500)]",
                className
            )}
        >
            {children}
        </div>
    );
}
