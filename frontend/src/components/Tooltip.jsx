import React, { useState } from 'react';
import { cn } from './Button';
import { motion, AnimatePresence } from 'framer-motion';

export function Tooltip({ text, children, position = 'top', className }) {
    const [isVisible, setIsVisible] = useState(false);

    const getPositionClasses = () => {
        switch (position) {
            case 'bottom':
                return "top-full mt-2 left-1/2 -translate-x-1/2";
            case 'left':
                return "right-full mr-2 top-1/2 -translate-y-1/2";
            case 'right':
                return "left-full ml-2 top-1/2 -translate-y-1/2";
            case 'top':
            default:
                return "bottom-full mb-2 left-1/2 -translate-x-1/2";
        }
    };

    return (
        <div
            className="relative inline-block"
            onMouseEnter={() => setIsVisible(true)}
            onMouseLeave={() => setIsVisible(false)}
            onFocus={() => setIsVisible(true)}
            onBlur={() => setIsVisible(false)}
        >
            {children}

            <AnimatePresence>
                {isVisible && (
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                        transition={{ duration: 0.15 }}
                        className={cn(
                            "absolute z-50 whitespace-nowrap rounded-[var(--radius-md)] bg-gray-900 px-3 py-1.5 text-xs text-white shadow-md",
                            getPositionClasses(),
                            className
                        )}
                        role="tooltip"
                    >
                        {text}
                        {/* Simple arrow for top position */}
                        {position === 'top' && (
                            <div className="absolute left-1/2 top-full -mt-px -translate-x-1/2 border-4 border-transparent border-t-gray-900" />
                        )}
                        {position === 'bottom' && (
                            <div className="absolute left-1/2 bottom-full -mb-px -translate-x-1/2 border-4 border-transparent border-b-gray-900" />
                        )}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
