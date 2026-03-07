import React, { useState } from 'react';
import { Filter, CheckCircle2, AlertCircle } from 'lucide-react';
import { Button } from './Button';
import { Badge } from './Badge';
import { Tabs, TabsList, TabsTrigger } from './Tabs';

export function ValidationReport() {
    const [filter, setFilter] = useState('All');

    const issues = [
        { id: 1, type: 'Citations', title: 'Unlinked Citation detected', description: 'Citation [3] is not linked to any bibliography entry.', location: 'Page 2, Paragraph 3', fixed: false },
        { id: 2, type: 'Headings', title: 'Incorrect Heading Level', description: 'Heading uses Title Case but IEEE requires Sentence case for Level 2.', location: 'Section 2.1', fixed: false },
        { id: 3, type: 'References', title: 'Missing DOI', description: 'Reference 4 is missing a required DOI link.', location: 'Bibliography', fixed: true },
        { id: 4, type: 'Tables', title: 'Table Exceeds Margin', description: 'Table 1 is wider than the column width allowed by the template.', location: 'Page 4', fixed: false },
    ];

    const filteredIssues = filter === 'All'
        ? issues
        : issues.filter(issue => issue.type === filter);

    return (
        <div className="bg-white rounded-[var(--radius-lg)] border border-[var(--color-surface-300)] shadow-sm mt-6 mb-12 overflow-hidden">

            {/* Header & Tabs */}
            <div className="p-4 border-b border-[var(--color-surface-200)] flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <h2 className="text-lg font-bold text-[var(--color-text-main)] flex items-center gap-2">
                    Validation Report
                </h2>

                <div className="flex items-center gap-3">
                    <Filter className="w-4 h-4 text-[var(--color-text-muted)] hidden sm:block" />
                    <Tabs value={filter} onValueChange={setFilter}>
                        <TabsList className="h-8">
                            <TabsTrigger value="All" className="text-xs h-6 px-3">All</TabsTrigger>
                            <TabsTrigger value="Citations" className="text-xs h-6 px-3">Citations</TabsTrigger>
                            <TabsTrigger value="Headings" className="text-xs h-6 px-3">Headings</TabsTrigger>
                            <TabsTrigger value="References" className="text-xs h-6 px-3">References</TabsTrigger>
                            <TabsTrigger value="Tables" className="text-xs h-6 px-3">Tables</TabsTrigger>
                        </TabsList>
                    </Tabs>
                </div>
            </div>

            {/* Issues List */}
            <div className="divide-y divide-[var(--color-surface-200)] bg-[var(--color-surface-50)]">
                {filteredIssues.map(issue => (
                    <div key={issue.id} className="p-4 hover:bg-white transition-colors flex items-start gap-4">
                        <div className="mt-0.5 flex-shrink-0">
                            {issue.fixed
                                ? <CheckCircle2 className="w-5 h-5 text-green-500" />
                                : <AlertCircle className="w-5 h-5 text-orange-500" />
                            }
                        </div>

                        <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between gap-4 mb-1">
                                <h4 className="text-sm font-semibold text-[var(--color-text-main)] truncate">
                                    {issue.title}
                                </h4>
                                <Badge variant="default" className="text-[10px] uppercase font-bold tracking-wider">
                                    {issue.type}
                                </Badge>
                            </div>
                            <p className="text-sm text-[var(--color-text-muted)] mb-2">
                                {issue.description}
                            </p>
                            <div className="flex items-center justify-between">
                                <span className="text-xs font-medium text-[var(--color-surface-400)] text-gray-400">
                                    Location: {issue.location}
                                </span>
                                {!issue.fixed && (
                                    <Button variant="secondary" size="sm" className="h-7 text-xs px-3">
                                        Fix manually
                                    </Button>
                                )}
                            </div>
                        </div>
                    </div>
                ))}

                {filteredIssues.length === 0 && (
                    <div className="p-8 text-center text-[var(--color-text-muted)]">
                        <CheckCircle2 className="w-8 h-8 text-green-500 mx-auto mb-3 opacity-50" />
                        <p>No issues found in this category.</p>
                    </div>
                )}
            </div>

        </div>
    );
}
