import { useState, useCallback, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
    Briefcase, Tag, BellOff, Landmark, KeyRound, Receipt,
    Inbox, Sparkles,
} from 'lucide-react';
import { MailThreadCard, type EmailThread } from './MailThreadCard';
import { useKeyboardShortcut } from '../hooks/useKeyboardShortcut';
import { EmailDetailModal } from './panel/EmailDetailModal';

export interface SplitInboxProps {
    inbox: EmailThread[];
    mode: 'important' | 'all';
}

// ─── Category Config ─────────────────────────────────────────────────────────
interface LaneConfig {
    key: string;
    label: string;
    icon: React.ComponentType<{ className?: string }>;
    color: string;
    dot: string;
    border: string;
    bg: string;
    headerBg: string;
    match: (c: string) => boolean;
}

const CATEGORY_LANES: LaneConfig[] = [
    {
        key: 'work',
        label: 'Work',
        icon: Briefcase,
        color: 'text-blue-400',
        dot: 'bg-blue-400',
        border: 'border-blue-500/25',
        bg: 'bg-blue-500/5',
        headerBg: 'bg-blue-500/10',
        match: (c: string) => ['work', 'business', 'professional', 'important'].includes(c),
    },
    {
        key: 'promotions',
        label: 'Promotions',
        icon: Tag,
        color: 'text-purple-400',
        dot: 'bg-purple-400',
        border: 'border-purple-500/25',
        bg: 'bg-purple-500/5',
        headerBg: 'bg-purple-500/10',
        match: (c: string) => ['promotional', 'newsletter', 'marketing', 'promotions'].includes(c),
    },
    {
        key: 'donotreply',
        label: 'Do Not Reply',
        icon: BellOff,
        color: 'text-slate-400',
        dot: 'bg-slate-400',
        border: 'border-slate-500/25',
        bg: 'bg-slate-500/5',
        headerBg: 'bg-slate-500/10',
        match: (c: string) => ['transactional', 'noreply', 'no-reply', 'automated', 'social'].includes(c),
    },
    {
        key: 'bank',
        label: 'Bank',
        icon: Landmark,
        color: 'text-emerald-400',
        dot: 'bg-emerald-400',
        border: 'border-emerald-500/25',
        bg: 'bg-emerald-500/5',
        headerBg: 'bg-emerald-500/10',
        match: (c: string) => ['bank', 'finance', 'financial', 'banking', 'payment'].includes(c),
    },
    {
        key: 'otps',
        label: 'OTPs',
        icon: KeyRound,
        color: 'text-amber-400',
        dot: 'bg-amber-400',
        border: 'border-amber-500/25',
        bg: 'bg-amber-500/5',
        headerBg: 'bg-amber-500/10',
        match: (c: string) => ['otp', 'alert', 'notification', 'security', 'verification'].includes(c),
    },
    {
        key: 'bills',
        label: 'Bills',
        icon: Receipt,
        color: 'text-rose-400',
        dot: 'bg-rose-400',
        border: 'border-rose-500/25',
        bg: 'bg-rose-500/5',
        headerBg: 'bg-rose-500/10',
        match: (c: string) => ['bill', 'invoice', 'receipt', 'subscription', 'billing'].includes(c),
    },
];

function getCategoryLane(category: string): LaneConfig | null {
    const cat = (category || '').toLowerCase().trim();
    return CATEGORY_LANES.find(lane => lane.match(cat)) ?? null;
}

// ─── Single Category Column (for the 4-grid layout) ──────────────────────────
function CategoryColumn({
    lane,
    threads,
    allThreads,
    selectedIndex,
    onSelect,
}: {
    lane: LaneConfig;
    threads: EmailThread[];
    allThreads: EmailThread[];
    selectedIndex: number;
    onSelect: (thread: EmailThread) => void;
}) {
    const Icon = lane.icon;
    return (
        <div className={`flex flex-col rounded-xl border ${lane.border} ${lane.bg} overflow-hidden h-full`}>
            {/* Sticky column header */}
            <div className={`flex items-center justify-between px-3 py-2.5 ${lane.headerBg} border-b ${lane.border}`}>
                <div className="flex items-center gap-2">
                    <Icon className={`w-3.5 h-3.5 flex-shrink-0 ${lane.color}`} />
                    <span className={`text-xs font-bold uppercase tracking-wide ${lane.color}`}>{lane.label}</span>
                </div>
                <span className={`text-[10px] font-mono min-w-[18px] text-center px-1.5 py-0.5 rounded-full ${lane.color} bg-black/20 border ${lane.border}`}>
                    {threads.length}
                </span>
            </div>

            {/* Scrollable email list */}
            <div className="flex-1 overflow-y-auto custom-scrollbar p-2 flex flex-col gap-2">
                {threads.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-8 gap-2 opacity-25">
                        <Icon className={`w-7 h-7 ${lane.color}`} />
                        <p className="text-[10px] text-nexus-textMuted">Empty</p>
                    </div>
                ) : (
                    threads.map(thread => (
                        <MailThreadCard
                            key={thread.id}
                            thread={thread}
                            isSelected={allThreads[selectedIndex]?.id === thread.id}
                            onClick={() => onSelect(thread)}
                        />
                    ))
                )}
            </div>
        </div>
    );
}

// ─── Important View ───────────────────────────────────────────────────────────
// Only these categories should appear in the Important tab
const IMPORTANT_CATEGORIES = [
    'important', 'requires_response', 'meeting_invitation',
];

function ImportantView({
    inbox,
    allThreads,
    selectedIndex,
    onSelect,
}: {
    inbox: EmailThread[];
    allThreads: EmailThread[];
    selectedIndex: number;
    onSelect: (thread: EmailThread) => void;
}) {
    // Only show emails with explicitly important categories
    const filtered = inbox.filter(e => {
        const cat = (e.category || '').toLowerCase().trim();
        return IMPORTANT_CATEGORIES.includes(cat);
    });

    const critical = filtered.filter(e => e.priorityScore >= 85);
    const high = filtered.filter(e => e.priorityScore >= 60 && e.priorityScore < 85);
    const moderate = filtered.filter(e => e.priorityScore >= 35 && e.priorityScore < 60);

    const Section = ({
        label, threads, accent, dot,
    }: { label: string; threads: EmailThread[]; accent: string; dot: string }) => {
        if (threads.length === 0) return null;
        return (
            <div className="flex flex-col gap-2">
                <div className="flex items-center gap-2 px-1">
                    <span className={`w-2 h-2 rounded-full ${dot}`} />
                    <span className={`text-xs font-mono font-semibold uppercase tracking-widest ${accent}`}>{label}</span>
                    <span className="text-xs text-nexus-textMuted">({threads.length})</span>
                </div>
                {threads.map(thread => (
                    <MailThreadCard
                        key={thread.id}
                        thread={thread}
                        isSelected={allThreads[selectedIndex]?.id === thread.id}
                        onClick={() => onSelect(thread)}
                    />
                ))}
            </div>
        );
    };

    if (filtered.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center h-full gap-4 opacity-40">
                <Sparkles className="w-10 h-10 text-nexus-primary" />
                <p className="text-sm text-nexus-textMuted italic">No important emails right now.</p>
            </div>
        );
    }

    return (
        <div className="flex flex-col gap-5 p-4 overflow-y-auto custom-scrollbar flex-1 pb-20">
            <Section label="Critical" threads={critical} accent="text-rose-400" dot="bg-rose-400" />
            <Section label="High Priority" threads={high} accent="text-amber-400" dot="bg-amber-400" />
            <Section label="Moderate" threads={moderate} accent="text-blue-400" dot="bg-blue-400" />
        </div>
    );
}

// ─── All Emails / 4-Grid Category View ───────────────────────────────────────
function AllCategoriesView({
    inbox,
    allThreads,
    selectedIndex,
    onSelect,
}: {
    inbox: EmailThread[];
    allThreads: EmailThread[];
    selectedIndex: number;
    onSelect: (thread: EmailThread) => void;
}) {
    // Bucket emails into lanes
    const laneEmails = new Map<string, EmailThread[]>(
        CATEGORY_LANES.map(lane => [lane.key, []])
    );
    const uncategorised: EmailThread[] = [];

    for (const email of inbox) {
        const lane = getCategoryLane(email.category);
        if (lane) {
            laneEmails.get(lane.key)!.push(email);
        } else {
            uncategorised.push(email);
        }
    }

    if (inbox.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center h-full gap-4 opacity-40">
                <Inbox className="w-10 h-10 text-nexus-textMuted" />
                <p className="text-sm text-nexus-textMuted italic">All clear — inbox is empty.</p>
            </div>
        );
    }

    const otherLane: LaneConfig = {
        key: 'other' as never,
        label: 'Other',
        icon: Inbox,
        color: 'text-nexus-textMuted',
        dot: 'bg-nexus-textMuted',
        border: 'border-nexus-border',
        bg: 'bg-white/[0.02]',
        headerBg: 'bg-white/5',
        match: () => false,
    };

    return (
        // Scrollable wrapper that fills the flex-1 space of the panel
        <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar p-3">
            {/* 4-column grid — 2 cols on md, 4 on xl */}
            <div className="grid grid-cols-2 xl:grid-cols-4 gap-3" style={{ minHeight: '100%' }}>
                {CATEGORY_LANES.map(lane => (
                    <div key={lane.key} className="min-h-[280px] flex flex-col">
                        <CategoryColumn
                            lane={lane}
                            threads={laneEmails.get(lane.key) ?? []}
                            allThreads={allThreads}
                            selectedIndex={selectedIndex}
                            onSelect={onSelect}
                        />
                    </div>
                ))}
                {uncategorised.length > 0 && (
                    <div className="min-h-[280px] flex flex-col">
                        <CategoryColumn
                            lane={otherLane}
                            threads={uncategorised}
                            allThreads={allThreads}
                            selectedIndex={selectedIndex}
                            onSelect={onSelect}
                        />
                    </div>
                )}
            </div>
        </div>
    );
}

// ─── Main SplitInbox ──────────────────────────────────────────────────────────
export function SplitInbox({ inbox, mode }: SplitInboxProps) {
    const sorted = [...inbox].sort((a, b) => b.priorityScore - a.priorityScore);
    const allThreads = sorted;

    const [selectedIndex, setSelectedIndex] = useState<number>(0);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [openEmailId, setOpenEmailId] = useState<string | null>(null);

    useEffect(() => {
        if (selectedIndex >= allThreads.length) {
            setSelectedIndex(0);
        }
    }, [allThreads.length, selectedIndex]);

    const handleNext = useCallback(() => {
        if (isModalOpen) return;
        setSelectedIndex(prev => Math.min(prev + 1, allThreads.length - 1));
    }, [allThreads.length, isModalOpen]);

    const handlePrev = useCallback(() => {
        if (isModalOpen) return;
        setSelectedIndex(prev => Math.max(prev - 1, 0));
    }, [allThreads.length, isModalOpen]);

    const handleOpen = useCallback(() => {
        const thread = allThreads[selectedIndex];
        if (thread) {
            setOpenEmailId(thread.id);
            setIsModalOpen(true);
        }
    }, [selectedIndex, allThreads]);

    const handleSelect = useCallback((thread: EmailThread) => {
        setSelectedIndex(allThreads.findIndex(t => t.id === thread.id));
        setOpenEmailId(thread.id);
        setIsModalOpen(true);
    }, [allThreads]);

    useKeyboardShortcut({ key: 'j' }, handleNext);
    useKeyboardShortcut({ key: 'ArrowDown' }, handleNext);
    useKeyboardShortcut({ key: 'k' }, handlePrev);
    useKeyboardShortcut({ key: 'ArrowUp' }, handlePrev);
    useKeyboardShortcut({ key: 'Enter' }, handleOpen);

    const isImportant = mode === 'important';

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="glass-panel w-full h-full flex flex-col overflow-hidden border-nexus-primary/10 relative"
        >
            <EmailDetailModal
                isOpen={isModalOpen}
                emailId={openEmailId || ''}
                onClose={() => setIsModalOpen(false)}
            />

            {/* Panel Header */}
            <div className="px-4 py-3 border-b border-nexus-border flex items-center justify-between bg-nexus-bg/80 backdrop-blur-xl z-10 flex-shrink-0">
                <h3 className={`font-semibold flex items-center gap-2 ${isImportant ? 'text-nexus-primary' : 'text-nexus-text'}`}>
                    {isImportant
                        ? <><span className="w-2 h-2 rounded-full bg-nexus-primary animate-pulse" /><Sparkles className="w-4 h-4" /> Important</>
                        : <><Inbox className="w-4 h-4 text-nexus-textMuted" /><span className="text-nexus-textMuted">All Mail</span></>
                    }
                </h3>
                <span className="text-xs bg-nexus-card px-2 py-1 rounded-md text-nexus-textMuted">
                    {inbox.length} {inbox.length === 1 ? 'item' : 'items'}
                </span>
            </div>

            {/* Body — fills remaining height */}
            <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
                {isImportant ? (
                    <ImportantView
                        inbox={sorted}
                        allThreads={allThreads}
                        selectedIndex={selectedIndex}
                        onSelect={handleSelect}
                    />
                ) : (
                    <AllCategoriesView
                        inbox={sorted}
                        allThreads={allThreads}
                        selectedIndex={selectedIndex}
                        onSelect={handleSelect}
                    />
                )}
            </div>

            {/* Bottom fade */}
            <div className="absolute bottom-0 w-full h-10 bg-gradient-to-t from-nexus-bg to-transparent pointer-events-none" />
        </motion.div>
    );
}
