import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { cn } from './Button';

export function ComplianceGauge({ score = 100, className }) {
    const [currentScore, setCurrentScore] = useState(0);

    useEffect(() => {
        // Animate score from 0
        const duration = 1500;
        const startTime = performance.now();

        const animate = (time) => {
            const elapsed = time - startTime;
            const progress = Math.min(elapsed / duration, 1);
            // easeOutQuart
            const easeProgress = 1 - Math.pow(1 - progress, 4);

            setCurrentScore(Math.round(easeProgress * score));

            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };

        requestAnimationFrame(animate);
    }, [score]);

    // SVG parameters
    const size = 160;
    const strokeWidth = 14;
    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    // Semicircle
    const offset = circumference - (currentScore / 100) * (circumference / 2);

    const getScoreColor = () => {
        if (currentScore >= 95) return 'text-green-500 stroke-green-500';
        if (currentScore >= 80) return 'text-blue-500 stroke-blue-500';
        if (currentScore >= 60) return 'text-yellow-500 stroke-yellow-500';
        return 'text-red-500 stroke-red-500';
    };

    return (
        <div className={cn("relative flex flex-col items-center justify-center", className)}>
            <div className="relative" style={{ width: size, height: size / 2 + 10 }}>
                {/* Background Arc */}
                <svg fill="transparent" width={size} height={size} className="absolute top-0 rotate-180">
                    <circle
                        stroke="var(--color-surface-200)"
                        strokeWidth={strokeWidth}
                        strokeLinecap="round"
                        strokeDasharray={`${circumference / 2} ${circumference}`}
                        r={radius}
                        cx={size / 2}
                        cy={size / 2}
                    />
                </svg>
                {/* Foreground Arc */}
                <svg fill="transparent" width={size} height={size} className={cn("absolute top-0 rotate-180 transition-all duration-300", getScoreColor())}>
                    <motion.circle
                        stroke="currentColor"
                        strokeWidth={strokeWidth}
                        strokeLinecap="round"
                        strokeDasharray={`${circumference / 2} ${circumference}`}
                        strokeDashoffset={offset}
                        r={radius}
                        cx={size / 2}
                        cy={size / 2}
                    />
                </svg>

                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-[20%] text-center">
                    <span className={cn("text-4xl font-extrabold tracking-tighter", getScoreColor().split(' ')[0])}>
                        {currentScore}%
                    </span>
                    <p className="text-[10px] uppercase font-bold text-[var(--color-text-muted)] tracking-wider mt-1">Compliance</p>
                </div>
            </div>
        </div>
    );
}
