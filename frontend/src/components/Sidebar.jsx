import React from 'react';
import { NavLink } from 'react-router-dom';
import {
    Upload,
    Settings,
    Play,
    Code2,
    MessageSquare,
    PenTool,
    ChevronLeft,
    ChevronRight,
} from 'lucide-react';
import { cn } from './Button';

export function Sidebar({ isOpen, toggleSidebar }) {
    const navItems = [
        { name: 'Upload', path: '/upload', icon: Upload },
        { name: 'Configure', path: '/configure', icon: Settings },
        { name: 'Process', path: '/process', icon: Play },
        { name: 'Editor', path: '/editor', icon: PenTool },
        { name: 'LaTeX', path: '/latex', icon: Code2 },
        { name: 'Agent', path: '/agent', icon: MessageSquare },
    ];

    return (
        <aside
            className={cn(
                "z-30 flex h-full flex-col bg-[var(--color-primary-500)] rounded-[var(--radius-xl)] shadow-[var(--shadow-card)] transition-all duration-300 ease-in-out overflow-hidden text-white",
                isOpen ? "w-64" : "w-18"
            )}
        >
            <div className="flex h-20 items-center p-4">
                <div className="flex items-center gap-3 overflow-hidden">
                    <img
                        src="/duck-logo.png"
                        alt="Docling"
                        className="w-10 h-10 rounded-[var(--radius-md)] object-cover shadow-sm shrink-0 bg-[#fdfceb]"
                    />
                    <span className={cn(
                        "text-[#fdfceb] font-extrabold text-4xl tracking-tighter font-karla my-2 mb-2 whitespace-nowrap transition-opacity duration-200",
                        isOpen ? "opacity-100" : "opacity-0 hidden"
                    )}>
                        Docling
                    </span>
                </div>
            </div>

            {/* Pipeline Steps Label */}
            {isOpen && (
                <div className="px-4 mb-1">
                    <span className="text-[10px] uppercase tracking-widest text-white/50 font-bold">Pipeline</span>
                </div>
            )}

            <div className="flex flex-col gap-2 p-3 flex-1 overflow-y-auto w-full">
                {navItems.map((item) => (
                    <NavLink
                        key={item.path}
                        to={item.path}
                        className={({ isActive }) => cn(
                            "flex items-center gap-3 rounded-[var(--radius-md)] px-3 py-3 text-sm font-medium transition-all group overflow-hidden whitespace-nowrap",
                            isActive
                                ? "bg-white/20 text-white font-bold"
                                : "text-white/70 hover:bg-white/10 hover:text-white"
                        )}
                        title={!isOpen ? item.name : undefined}
                    >
                        <item.icon className="h-5 w-5 shrink-0 transition-colors" />
                        <span className={cn(
                            "transition-opacity duration-200",
                            isOpen ? "opacity-100" : "opacity-0 hidden"
                        )}>
                            {item.name}
                        </span>
                    </NavLink>
                ))}
            </div>

            <div className="flex flex-col p-3 border-t border-white/20 gap-2">
                <button
                    onClick={toggleSidebar}
                    className="flex w-full items-center justify-center rounded-[var(--radius-md)] p-2 text-white/70 hover:bg-white/10 hover:text-white transition-colors"
                >
                    {isOpen ? <ChevronLeft className="h-6 w-6" /> : <ChevronRight className="h-6 w-6" />}
                </button>
            </div>
        </aside>
    );
}
