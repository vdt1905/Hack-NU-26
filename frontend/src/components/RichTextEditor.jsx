import React, { useEffect } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import {
    Bold, Italic, Underline, List, ListOrdered,
    Quote, Heading1, Heading2, Heading3
} from 'lucide-react';
import { cn } from './Button';

const MenuBar = ({ editor }) => {
    if (!editor) {
        return null;
    }

    const isActive = (type, options) => editor.isActive(type, options);

    const ToolbarButton = ({ onClick, active, icon: Icon, title }) => (
        <button
            onClick={onClick}
            className={cn(
                "p-1.5 rounded-[var(--radius-md)] text-[var(--color-text-muted)] hover:bg-[var(--color-surface-200)] hover:text-[var(--color-text-main)] transition-colors",
                active && "bg-[var(--color-primary-100)] text-[var(--color-primary-600)]"
            )}
            title={title}
        >
            <Icon className="w-4 h-4" />
        </button>
    );

    return (
        <div className="flex flex-wrap items-center gap-1 p-2 border-b border-[var(--color-surface-200)] bg-white sticky top-0 z-10 w-full overflow-x-auto">
            <ToolbarButton onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()} active={isActive('heading', { level: 1 })} icon={Heading1} title="Heading 1" />
            <ToolbarButton onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()} active={isActive('heading', { level: 2 })} icon={Heading2} title="Heading 2" />
            <ToolbarButton onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()} active={isActive('heading', { level: 3 })} icon={Heading3} title="Heading 3" />

            <div className="w-px h-4 bg-[var(--color-surface-300)] mx-1" />

            <ToolbarButton onClick={() => editor.chain().focus().toggleBold().run()} active={isActive('bold')} icon={Bold} title="Bold" />
            <ToolbarButton onClick={() => editor.chain().focus().toggleItalic().run()} active={isActive('italic')} icon={Italic} title="Italic" />
            <ToolbarButton onClick={() => editor.chain().focus().toggleStrike().run()} active={isActive('strike')} icon={Underline} title="Strike" />

            <div className="w-px h-4 bg-[var(--color-surface-300)] mx-1" />

            <ToolbarButton onClick={() => editor.chain().focus().toggleBulletList().run()} active={isActive('bulletList')} icon={List} title="Bullet List" />
            <ToolbarButton onClick={() => editor.chain().focus().toggleOrderedList().run()} active={isActive('orderedList')} icon={ListOrdered} title="Numbered List" />
            <ToolbarButton onClick={() => editor.chain().focus().toggleBlockquote().run()} active={isActive('blockquote')} icon={Quote} title="Quote" />
        </div>
    );
};

export function RichTextEditor({ content, onChange, readOnly = false, className }) {
    const editor = useEditor({
        extensions: [
            StarterKit.configure({
                bulletList: { keepMarks: true, keepAttributes: false },
                orderedList: { keepMarks: true, keepAttributes: false },
            }),
        ],
        content: content,
        editable: !readOnly,
        onUpdate: ({ editor }) => {
            onChange?.(editor.getHTML());
        },
        editorProps: {
            attributes: {
                class: cn(
                    "prose prose-sm max-w-none focus:outline-none p-6 min-h-[500px]",
                    readOnly && "opacity-80 cursor-default"
                ),
            },
        },
    });

    // Sync external content changes if it's read-only preview (like original text)
    useEffect(() => {
        if (editor && content && readOnly && editor.getHTML() !== content) {
            editor.commands.setContent(content);
        }
    }, [content, editor, readOnly]);

    return (
        <div className={cn("flex flex-col h-full bg-white relative overflow-hidden", className)}>
            {!readOnly && <MenuBar editor={editor} />}
            <div className="flex-1 overflow-y-auto w-full">
                <EditorContent editor={editor} className="w-full h-full" />
            </div>
        </div>
    );
}
