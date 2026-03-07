import React from 'react';
import { NavLink } from 'react-router-dom';
import { Upload, Settings, Play, Code2, MessageSquare, PenTool } from 'lucide-react';
import { cn } from './Button';

export function Navbar() {
    const links = [
        { name: 'Upload', path: '/upload', icon: Upload },
        { name: 'Configure', path: '/configure', icon: Settings },
        { name: 'Process', path: '/process', icon: Play },
        { name: 'Editor', path: '/editor', icon: PenTool },
        { name: 'LaTeX', path: '/latex', icon: Code2 },
        { name: 'Agent', path: '/agent', icon: MessageSquare },
    ];

    return (
        <header className="flex h-16 w-full shrink-0 items-center px-6 lg:px-10 justify-between border-b border-[var(--color-surface-200)]">
            <nav className="flex items-center gap-6">
                {links.map(link => (
                    <NavLink
                        key={link.path}
                        to={link.path}
                        className={({ isActive }) => cn(
                            "flex items-center gap-2 font-semibold text-sm border-b-2 py-2 transition-colors",
                            isActive
                                ? "text-[var(--color-text-main)] border-[var(--color-primary-500)]"
                                : "text-[var(--color-text-muted)] border-transparent hover:text-[var(--color-text-main)]"
                        )}
                    >
                        <link.icon className="w-4 h-4" /> {link.name}
                    </NavLink>
                ))}
            </nav>
        </header>
    );
}
