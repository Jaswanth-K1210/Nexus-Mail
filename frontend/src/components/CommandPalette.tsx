import { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Zap, Command, Settings, X, Mail } from 'lucide-react';
import { useKeyboardShortcut } from '../hooks/useKeyboardShortcut';

interface CommandPaletteProps {
    onAction: (actionId: string) => void;
}

const COMMANDS = [
    { id: 'sync', icon: <Zap className="w-4 h-4 text-yellow-400" />, label: 'Force Sync Inbox', shortcut: 'S' },
    { id: 'compose', icon: <Mail className="w-4 h-4 text-nexus-primary" />, label: 'Compose New Email', shortcut: 'C' },
    { id: 'search', icon: <Search className="w-4 h-4 text-blue-400" />, label: 'Search Emails...', shortcut: '/' },
    { id: 'settings', icon: <Settings className="w-4 h-4 text-gray-400" />, label: 'Preferences', shortcut: ',' },
    { id: 'logout', icon: <X className="w-4 h-4 text-red-400" />, label: 'Logout', shortcut: 'L' }
];

export function CommandPalette({ onAction }: CommandPaletteProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [query, setQuery] = useState('');
    const [activeIndex, setActiveIndex] = useState(0);
    const dialogRef = useRef<HTMLDivElement>(null);
    const returnFocusRef = useRef<HTMLElement | null>(null);

    const open = () => {
        returnFocusRef.current = document.activeElement as HTMLElement | null;
        setQuery('');
        setActiveIndex(0);
        setIsOpen(true);
    };

    const close = () => {
        setIsOpen(false);
        returnFocusRef.current?.focus();
    };

    // Toggle on CMD+K / CTRL+K
    const toggle = (e: KeyboardEvent) => {
        e.preventDefault();
        if (isOpen) close();
        else open();
    };
    useKeyboardShortcut({ key: 'k', metaKey: true }, toggle);
    useKeyboardShortcut({ key: 'k', ctrlKey: true }, toggle);

    // Close on Escape
    useKeyboardShortcut({ key: 'Escape' }, () => {
        if (isOpen) close();
    });

    // Keep Tab / Shift+Tab inside the dialog
    const trapFocus = (e: React.KeyboardEvent) => {
        if (e.key !== 'Tab' || !dialogRef.current) return;
        const focusable = dialogRef.current.querySelectorAll<HTMLElement>(
            'input, button, [href], [tabindex]:not([tabindex="-1"])',
        );
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
            e.preventDefault();
            last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
            e.preventDefault();
            first.focus();
        }
    };

    const filtered = COMMANDS.filter((c) => c.label.toLowerCase().includes(query.toLowerCase()));

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            setActiveIndex((prev) => (prev + 1) % filtered.length);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            setActiveIndex((prev) => (prev - 1 + filtered.length) % filtered.length);
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (filtered[activeIndex]) {
                handleSelect(filtered[activeIndex].id);
            }
        }
    };

    const handleSelect = (id: string) => {
        close();
        onAction(id);
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <div className="fixed inset-0 z-50 flex items-start justify-center pt-32 bg-black/60">
                    {/* Click outside to close */}
                    <div className="absolute inset-0" onClick={close} />

                    <motion.div
                        ref={dialogRef}
                        role="dialog"
                        aria-modal="true"
                        aria-label="Command palette"
                        onKeyDown={trapFocus}
                        initial={{ opacity: 0, scale: 0.95, y: -20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: -20 }}
                        transition={{ duration: 0.15 }}
                        className="relative w-full max-w-xl bg-nexus-card border border-white/10 rounded-xl shadow-[0_0_50px_rgba(177,158,239,0.15)] overflow-hidden flex flex-col"
                    >
                        <div className="flex items-center px-4 py-3 border-b border-white/10 gap-3">
                            <Search className="w-5 h-5 text-gray-400" aria-hidden="true" />
                            <input
                                autoFocus
                                type="text"
                                role="combobox"
                                aria-label="Search commands"
                                aria-expanded="true"
                                aria-controls="command-palette-list"
                                aria-activedescendant={filtered[activeIndex] ? `command-${filtered[activeIndex].id}` : undefined}
                                className="flex-1 bg-transparent border-none outline-none text-white placeholder:text-gray-500 text-lg"
                                placeholder="Type a command or search..."
                                value={query}
                                onChange={(e) => {
                                    setQuery(e.target.value);
                                    setActiveIndex(0);
                                }}
                                onKeyDown={handleKeyDown}
                            />
                            <div className="flex items-center gap-1 opacity-50 text-xs font-mono">
                                <span><Command className="w-3 h-3 inline" /></span>
                                <span>K</span>
                            </div>
                        </div>

                        <div id="command-palette-list" role="listbox" aria-label="Commands" className="py-2 max-h-80 overflow-y-auto custom-scrollbar">
                            {filtered.length === 0 ? (
                                <p className="px-4 py-8 text-center text-gray-500">No matching commands.</p>
                            ) : (
                                filtered.map((cmd, idx) => (
                                    <div
                                        key={cmd.id}
                                        id={`command-${cmd.id}`}
                                        role="option"
                                        aria-selected={idx === activeIndex}
                                        className={`px-4 py-3 mx-2 rounded-lg flex items-center justify-between cursor-pointer transition-colors ${idx === activeIndex ? 'bg-nexus-primary/20 text-white' : 'text-gray-400 hover:bg-white/5'
                                            }`}
                                        onClick={() => handleSelect(cmd.id)}
                                        onMouseEnter={() => setActiveIndex(idx)}
                                    >
                                        <div className="flex items-center gap-3">
                                            {cmd.icon}
                                            <span className="font-medium text-sm">{cmd.label}</span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            {cmd.shortcut && (
                                                <span className="text-xs font-mono bg-black/30 px-2 py-0.5 rounded border border-white/10 opacity-60">
                                                    {cmd.shortcut}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    );
}
