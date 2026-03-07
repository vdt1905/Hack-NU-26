import React from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { FileText, Code2, ArrowRight, CheckCircle } from 'lucide-react';
import { Button } from '../components/Button';

export function Landing() {
    const navigate = useNavigate();

    return (
        <div className="min-h-screen bg-[var(--color-surface-50)] flex flex-col font-sans overflow-x-hidden">

            {/* Minimal Header */}
            <header className="w-full p-6 flex items-center justify-between z-20 absolute top-0 left-0 right-0">
                <div className="flex items-center gap-3">
                    <img
                        src="/duck-logo.png"
                        alt="Docling"
                        className="w-10 h-10 rounded-[var(--radius-md)] object-cover shadow-sm bg-[#fdfceb]"
                    />
                    <span className="text-[var(--color-primary-600)] font-extrabold text-3xl tracking-tighter font-karla">
                        Docling
                    </span>
                </div>
                <div className="flex gap-4 items-center">
                    {/* <button
                        onClick={() => navigate('/auth')}
                        className="text-[var(--color-primary-600)] font-bold hover:text-[var(--color-primary-900)] transition-colors px-4 py-2"
                    >
                        Sign In
                    </button> */}
                    <Button
                        onClick={() => navigate('/upload')}
                        className="shadow-md bg-[var(--color-primary-600)] hover:bg-[var(--color-primary-900)] text-white"
                    >
                        Get Started
                    </Button>
                </div>
            </header>

            {/* Hero Section */}
            <main className="flex-1 flex justify-center items-center relative pt-20 pb-12 px-4 sm:px-6 lg:px-8">

                {/* Abstract Decorative Background Elements */}
                <div className="absolute top-1/4 -left-32 w-96 h-96 bg-[var(--color-primary-100)] rounded-full blur-[100px] opacity-40 z-0 animate-pulse-slow"></div>
                <div className="absolute bottom-1/4 -right-32 w-[500px] h-[500px] bg-[var(--color-primary-500)] rounded-full blur-[120px] opacity-20 z-0"></div>

                <div className="max-w-5xl mx-auto text-center z-10">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.6 }}
                        className="mb-8 flex justify-center"
                    >
                        {/* <span className="bg-[var(--color-primary-50)] text-[var(--color-primary-900)] px-4 py-1.5 rounded-full text-sm font-bold tracking-wide border border-[var(--color-primary-100)] shadow-sm">
                            The Future of Academic Publishing
                        </span> */}
                    </motion.div>

                    <motion.h1
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.6, delay: 0.1 }}
                        className="text-7xl sm:text-8xl lg:text-[100px] font-anton tracking-tight text-[var(--color-text-main)] leading-[1.05] mb-8"
                    >
                        <span className="block">
                            Write Your Research
                        </span>

                        <span className="block mt-4 text-5xl sm:text-6xl lg:text-[80px] text-[var(--color-primary-500)]">
                            We Handle the Rest...
                        </span>
                    </motion.h1>    

                    <motion.p
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.6, delay: 0.2 }}
                        className="text-md sm:text-lg text-[var(--color-text-muted)] max-w-3xl mx-auto mb-12 font-medium leading-relaxed"
                    >
                        Upload your manuscript and instantly convert it into a publication-ready format.
                    </motion.p>

                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.6, delay: 0.3 }}
                        className="flex flex-col sm:flex-row gap-4 justify-center items-center"
                    >
                        <Button
                            size="lg"
                            className="w-full sm:w-auto px-10 py-6 text-lg shadow-xl bg-[var(--color-primary-600)] hover:bg-[var(--color-primary-900)] group"
                            onClick={() => navigate('/upload')}
                        >
                            Start Formatting Free
                            <ArrowRight className="ml-2 w-5 h-5 group-hover:translate-x-1 transition-transform" />
                        </Button>
                    </motion.div>
                </div>
            </main>

            {/* Features Preview Section */}
            <section className="w-full bg-[var(--color-primary-600)] py-20 px-4 sm:px-6 lg:px-8 relative z-10 border-t border-[var(--color-primary-900)]/20">
                <div className="max-w-6xl mx-auto">
                    <div className="text-center mb-16">
                        <h2 className="text-4xl lg:text-5xl font-anton text-[var(--color-primary-50)] tracking-wide mb-4">
                           Everything Your Paper Needs to Get Published
                        </h2>
                        <p className="text-[var(--color-primary-100)] text-xl  mx-auto font-medium">
                            
                            Our agents automatically structure, format, and validate your manuscript for journal submission.
                        </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                        {/* Feature 1 */}
                        <div className="bg-[var(--color-surface-50)] flex flex-col items-center text-center rounded-3xl p-8 shadow-xl hover:shadow-2xl transition-shadow border border-[var(--color-surface-200)] group transform hover:-translate-y-1 duration-300">
                            <div className="w-16 h-16 bg-[var(--color-primary-50)] rounded-2xl flex items-center justify-center mb-6 shadow-inner border 2 border-[var(--color-primary-100)] group-hover:scale-105 transition-transform">
                                <FileText className="w-8 h-8 text-[var(--color-primary-600)]" />
                            </div>
                            <h3 className="text-xl font-bold text-[var(--color-text-main)] mb-3 font-karla text-[22px]">Smart Structuring</h3>
                            <p className="text-[var(--color-text-muted)] leading-relaxed font-medium">
                                Upload a raw Document. Our AI parses headings, abstracts, and figures, instantly mapping them to correct semantic identifiers.
                            </p>
                        </div>

                        {/* Feature 2 */}
                        <div className="bg-[var(--color-surface-50)] flex flex-col items-center text-center rounded-3xl p-8 shadow-xl hover:shadow-2xl transition-shadow border border-[var(--color-surface-200)] group transform hover:-translate-y-1 duration-300">
                            <div className="w-16 h-16 bg-[var(--color-primary-50)] rounded-2xl flex items-center justify-center mb-6 shadow-inner border 2 border-[var(--color-primary-100)] group-hover:scale-105 transition-transform">
                                <CheckCircle className="w-8 h-8 text-[var(--color-primary-600)]" />
                            </div>
                            <h3 className="text-xl font-bold text-[var(--color-text-main)] mb-3 font-karla text-[22px]">Citation Sync</h3>
                            <p className="text-[var(--color-text-muted)] leading-relaxed font-medium">
                                Never worry about mismatched references again. We auto-check inline citations against your bibliography format rules.
                            </p>
                        </div>

                        {/* Feature 3 */}
                        <div className="bg-[var(--color-surface-50)] flex flex-col items-center text-center rounded-3xl p-8 shadow-xl hover:shadow-2xl transition-shadow border border-[var(--color-surface-200)] group transform hover:-translate-y-1 duration-300">
                            <div className="w-16 h-16 bg-[var(--color-primary-50)] rounded-2xl flex items-center justify-center mb-6 shadow-inner border 2 border-[var(--color-primary-100)] group-hover:scale-105 transition-transform">
                                <Code2 className="w-8 h-8 text-[var(--color-primary-600)]" />
                            </div>
                            <h3 className="text-xl font-bold text-[var(--color-text-main)] mb-3 font-karla text-[22px]">LaTeX Compilation</h3>
                            <p className="text-[var(--color-text-muted)] leading-relaxed font-medium">
                                Need absolute precision? Jump into our integrated LaTeX editor that guarantees error-free outputs for submission.
                            </p>
                        </div>
                    </div>
                </div>
            </section>
        </div>
    );
}
