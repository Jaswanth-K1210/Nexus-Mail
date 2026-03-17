import { useState, useCallback, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
    Briefcase, Tag, BellOff, Landmark, KeyRound, Receipt,
    Inbox, Sparkles, GripVertical, CheckCircle2, User,
    GraduationCap, Rocket, Mic, Monitor, Building2, Heart,
    Scale, BookOpen, Wrench, Home, HandHeart, PieChart,
    Megaphone, Users, Calendar, DollarSign, FileText,
    Shield, Search, BarChart3, Handshake, Star, Layers,
    ClipboardList, Truck, CalendarClock, UserCheck, TrendingUp,
    Mail, Banknote, MonitorSmartphone, FolderOpen, ShoppingCart,
    Settings2, HeartPulse, FlaskConical, Microscope, Gavel,
    Package, ShieldCheck, FileSignature, BarChart2, CalendarDays,
    ClipboardCheck, UserPlus, Link2,
    type LucideIcon,
} from 'lucide-react';
import { MailThreadCard, type EmailThread } from './MailThreadCard';
import { useKeyboardShortcut } from '../hooks/useKeyboardShortcut';
import { EmailDetailModal } from './panel/EmailDetailModal';
import { getRoleLanes, type LaneConfig as RoleLaneConfig } from '../config/roleCategories';

// Icon resolver — maps string icon names from roleCategories.ts to Lucide components
const ICON_MAP: Record<string, LucideIcon> = {
    Briefcase, Tag, BellOff, Landmark, KeyRound, Receipt, Inbox, Sparkles,
    GripVertical, CheckCircle2, User, GraduationCap, Rocket, Mic, Monitor,
    Building2, Heart, Scale, BookOpen, Wrench, Home, HandHeart, PieChart,
    Megaphone, Users, Calendar, DollarSign, FileText, Shield, Search,
    BarChart3, Handshake, Star, Layers, ClipboardList, Truck, CalendarClock,
    UserCheck, TrendingUp, Mail, Banknote, MonitorSmartphone, FolderOpen,
    ShoppingCart, Settings2, HeartPulse, FlaskConical, Microscope, Gavel,
    Package, ShieldCheck, FileSignature, BarChart2, CalendarDays,
    ClipboardCheck, UserPlus, Link2,
};

/** Convert role-based LaneConfig (string icon + categories array) to internal LaneConfig (component icon + match fn) */
function roleLanesToInternalLanes(roleLanes: RoleLaneConfig[]): LaneConfig[] {
    return roleLanes.map(rl => ({
        key: rl.key,
        label: rl.label,
        icon: ICON_MAP[rl.icon] || Inbox,
        color: rl.color,
        dot: rl.dot,
        border: rl.border,
        bg: rl.bg,
        headerBg: rl.headerBg,
        match: (c: string) => rl.categories.includes(c),
    }));
}

export interface SplitInboxProps {
    inbox: EmailThread[];
    mode: 'important' | 'all';
    onEmailRead?: (emailId: string) => void;
    roleKey?: string;
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

// Lanes ordered by user's requested priority:
// Work/Important → Bank → OTPs → Bills → Promotions → Do Not Reply → Other
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
        // FIX: Include ALL backend AI categories that belong here.
        // The AI returns "requires_response" and "meeting_invitation" which were
        // previously unmatched, causing them to land in "Other" incorrectly.
        match: (c: string) => [
            'work', 'business', 'professional', 'important',
            'requires_response', 'meeting_invitation',
        ].includes(c),
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
    {
        key: 'promotions',
        label: 'Promotions',
        icon: Tag,
        color: 'text-purple-400',
        dot: 'bg-purple-400',
        border: 'border-purple-500/25',
        bg: 'bg-purple-500/5',
        headerBg: 'bg-purple-500/10',
        // FIX: "newsletter" is a backend AI category — include it here
        match: (c: string) => ['promotional', 'newsletter', 'marketing', 'promotions'].includes(c),
    },
    {
        key: 'personal',
        label: 'Personal',
        icon: User,
        color: 'text-cyan-400',
        dot: 'bg-cyan-400',
        border: 'border-cyan-500/25',
        bg: 'bg-cyan-500/5',
        headerBg: 'bg-cyan-500/10',
        match: (c: string) => ['personal', 'family', 'friends'].includes(c),
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
        // FIX: "spam" is a backend AI category that was unmatched → fell into "Other"
        match: (c: string) => ['transactional', 'noreply', 'no-reply', 'automated', 'social', 'spam'].includes(c),
    },
];

const RESPONDED_LANE: LaneConfig = {
    key: 'responded',
    label: 'Responded',
    icon: CheckCircle2,
    color: 'text-green-400',
    dot: 'bg-green-400',
    border: 'border-green-500/25',
    bg: 'bg-green-500/5',
    headerBg: 'bg-green-500/10',
    match: () => false, // special handling — matched by `replied` flag, not category
};

const OTHER_LANE: LaneConfig = {
    key: 'other',
    label: 'Other',
    icon: Inbox,
    color: 'text-nexus-textMuted',
    dot: 'bg-nexus-textMuted',
    border: 'border-nexus-border',
    bg: 'bg-white/[0.02]',
    headerBg: 'bg-white/5',
    match: () => false,
};



// ─── Persistent lane order (localStorage) ────────────────────────────────────
const LANE_ORDER_KEY = 'nexus_lane_order';

function getDefaultOrder(lanes: LaneConfig[]): string[] {
    return [...lanes.map(l => l.key), 'responded', 'other'];
}

function loadLaneOrder(lanes: LaneConfig[]): string[] {
    try {
        const stored = localStorage.getItem(LANE_ORDER_KEY);
        if (stored) {
            const parsed = JSON.parse(stored) as string[];
            const defaults = getDefaultOrder(lanes);
            // Validate: must contain all known keys, no extras
            if (defaults.every(k => parsed.includes(k)) && parsed.length === defaults.length) {
                return parsed;
            }
        }
    } catch { /* ignore */ }
    return getDefaultOrder(lanes);
}

function saveLaneOrder(order: string[]) {
    localStorage.setItem(LANE_ORDER_KEY, JSON.stringify(order));
}

// ─── Single Category Column (fixed height, scrollable content) ───────────────
function CategoryColumn({
    lane,
    threads,
    allThreads,
    selectedIndex,
    onSelect,
    onDragStart,
    onDragOver,
    onDrop,
    isDragging,
    isDropTarget,
}: {
    lane: LaneConfig;
    threads: EmailThread[];
    allThreads: EmailThread[];
    selectedIndex: number;
    onSelect: (thread: EmailThread) => void;
    onDragStart: () => void;
    onDragOver: (e: React.DragEvent) => void;
    onDrop: () => void;
    isDragging: boolean;
    isDropTarget: boolean;
}) {
    const Icon = lane.icon;
    return (
        <div
            draggable
            onDragStart={onDragStart}
            onDragOver={onDragOver}
            onDrop={onDrop}
            className={`flex flex-col rounded-xl border ${lane.border} ${lane.bg} overflow-hidden transition-all duration-200
                ${isDragging ? 'opacity-40 scale-[0.97]' : ''}
                ${isDropTarget ? 'ring-2 ring-nexus-primary/50 scale-[1.01]' : ''}
            `}
            style={{ height: '100%' }}
        >
            {/* Sticky column header with drag handle */}
            <div className={`flex items-center justify-between px-3 py-2.5 ${lane.headerBg} border-b ${lane.border} cursor-grab active:cursor-grabbing select-none`}>
                <div className="flex items-center gap-2">
                    <GripVertical className="w-3 h-3 text-nexus-textMuted/40 flex-shrink-0" />
                    <Icon className={`w-3.5 h-3.5 flex-shrink-0 ${lane.color}`} />
                    <span className={`text-xs font-bold uppercase tracking-wide ${lane.color}`}>{lane.label}</span>
                </div>
                <span className={`text-[10px] font-mono min-w-[18px] text-center px-1.5 py-0.5 rounded-full ${lane.color} bg-black/20 border ${lane.border}`}>
                    {threads.length}
                </span>
            </div>

            {/* Scrollable email list — fills remaining height */}
            <div className="flex-1 overflow-y-auto custom-scrollbar p-2 flex flex-col gap-2 min-h-0">
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

// ─── Important View — sorted by date (newest first), priority as tiebreaker ──
// Show everything EXCEPT known low-value categories
const NON_IMPORTANT_CATEGORIES = [
    'promotional', 'newsletter', 'marketing', 'social',
    'transactional', 'spam', 'noreply', 'no-reply', 'automated',
];

function formatTimeAgo(dateStr?: string): string {
    if (!dateStr) return '';
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'Just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    return `${days}d ago`;
}

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
    // All emails except low-value categories, sorted by date (newest first) then priority
    const filtered = inbox
        .filter(e => {
            const cat = (e.category || '').toLowerCase().trim();
            return !NON_IMPORTANT_CATEGORIES.includes(cat);
        })
        .sort((a, b) => {
            // Primary sort: newest date first
            const tA = a.receivedAt ? new Date(a.receivedAt).getTime() : 0;
            const tB = b.receivedAt ? new Date(b.receivedAt).getTime() : 0;
            if (tB !== tA) return tB - tA;
            // Tiebreaker: higher priority first
            return b.priorityScore - a.priorityScore;
        });

    // Group into time buckets
    const now = Date.now();
    const oneHour = 3600000;
    const oneDay = 86400000;
    const recent = filtered.filter(e => e.receivedAt && now - new Date(e.receivedAt).getTime() < oneHour);
    const today = filtered.filter(e => e.receivedAt && now - new Date(e.receivedAt).getTime() >= oneHour && now - new Date(e.receivedAt).getTime() < oneDay);
    const older = filtered.filter(e => !e.receivedAt || now - new Date(e.receivedAt).getTime() >= oneDay);

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
                    <div key={thread.id} className="relative">
                        <MailThreadCard
                            thread={thread}
                            isSelected={allThreads[selectedIndex]?.id === thread.id}
                            onClick={() => onSelect(thread)}
                        />
                        {/* Time label overlay */}
                        <span className="absolute top-2 right-2 text-[10px] font-mono text-nexus-textMuted/70 bg-black/30 px-1.5 py-0.5 rounded">
                            {formatTimeAgo(thread.receivedAt)}
                        </span>
                    </div>
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
            <Section label="Last Hour" threads={recent} accent="text-rose-400" dot="bg-rose-400" />
            <Section label="Today" threads={today} accent="text-amber-400" dot="bg-amber-400" />
            <Section label="Earlier" threads={older} accent="text-blue-400" dot="bg-blue-400" />
        </div>
    );
}

// ─── All Emails / Draggable Category Grid View ───────────────────────────────
function AllCategoriesView({
    inbox,
    allThreads,
    selectedIndex,
    onSelect,
    activeLanes,
}: {
    inbox: EmailThread[];
    allThreads: EmailThread[];
    selectedIndex: number;
    onSelect: (thread: EmailThread) => void;
    activeLanes?: LaneConfig[];
}) {
    const lanes = activeLanes || CATEGORY_LANES;
    const [laneOrder, setLaneOrder] = useState<string[]>(() => loadLaneOrder(lanes));
    const [dragSource, setDragSource] = useState<string | null>(null);
    const [dropTarget, setDropTarget] = useState<string | null>(null);

    // Reset lane order when active lanes change (e.g. role switch)
    useEffect(() => {
        setLaneOrder(loadLaneOrder(lanes));
    }, [activeLanes]);

    // Bucket emails into lanes
    const laneEmails = new Map<string, EmailThread[]>(
        lanes.map(lane => [lane.key, []])
    );
    laneEmails.set('responded', []);
    laneEmails.set('other', []);

    for (const email of inbox) {
        if (email.replied) {
            laneEmails.get('responded')!.push(email);
            continue;
        }
        const cat = (email.category || '').toLowerCase().trim();
        const matchedLane = lanes.find(l => l.match(cat));
        if (matchedLane) {
            laneEmails.get(matchedLane.key)!.push(email);
        } else {
            laneEmails.get('other')!.push(email);
        }
    }

    // Build ordered lane list from saved order
    const laneMap = new Map<string, LaneConfig>(
        lanes.map(l => [l.key, l])
    );
    laneMap.set('responded', RESPONDED_LANE);
    laneMap.set('other', OTHER_LANE);

    const orderedLanes: { config: LaneConfig; threads: EmailThread[] }[] = laneOrder
        .map(key => {
            const config = laneMap.get(key);
            if (!config) return null;
            const threads = laneEmails.get(key) ?? [];
            // Show "Other" and "Responded" only if they have emails
            if ((key === 'other' || key === 'responded') && threads.length === 0) return null;
            return { config, threads };
        })
        .filter((x): x is { config: LaneConfig; threads: EmailThread[] } => x !== null);

    // ─── Drag handlers ───
    const handleDragStart = (key: string) => {
        setDragSource(key);
    };

    const handleDragOver = (e: React.DragEvent, key: string) => {
        e.preventDefault();
        if (dragSource && dragSource !== key) {
            setDropTarget(key);
        }
    };

    const handleDrop = (targetKey: string) => {
        if (!dragSource || dragSource === targetKey) {
            setDragSource(null);
            setDropTarget(null);
            return;
        }
        const newOrder = [...laneOrder];
        const srcIdx = newOrder.indexOf(dragSource);
        const dstIdx = newOrder.indexOf(targetKey);
        if (srcIdx !== -1 && dstIdx !== -1) {
            newOrder.splice(srcIdx, 1);
            newOrder.splice(dstIdx, 0, dragSource);
            setLaneOrder(newOrder);
            saveLaneOrder(newOrder);
        }
        setDragSource(null);
        setDropTarget(null);
    };

    const handleDragEnd = () => {
        setDragSource(null);
        setDropTarget(null);
    };

    if (inbox.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center h-full gap-4 opacity-40">
                <Inbox className="w-10 h-10 text-nexus-textMuted" />
                <p className="text-sm text-nexus-textMuted italic">All clear — inbox is empty.</p>
            </div>
        );
    }

    return (
        <div
            className="flex-1 min-h-0 overflow-y-auto custom-scrollbar p-3"
            onDragEnd={handleDragEnd}
        >
            {/* All columns same fixed height, internal content scrolls */}
            <div
                className="grid grid-cols-2 xl:grid-cols-4 gap-3"
                style={{ minHeight: '100%' }}
            >
                {orderedLanes.map(({ config, threads }) => (
                    <div key={config.key} className="flex flex-col" style={{ height: '420px' }}>
                        <CategoryColumn
                            lane={config}
                            threads={threads}
                            allThreads={allThreads}
                            selectedIndex={selectedIndex}
                            onSelect={onSelect}
                            onDragStart={() => handleDragStart(config.key)}
                            onDragOver={(e) => handleDragOver(e, config.key)}
                            onDrop={() => handleDrop(config.key)}
                            isDragging={dragSource === config.key}
                            isDropTarget={dropTarget === config.key}
                        />
                    </div>
                ))}
            </div>
        </div>
    );
}

// ─── Main SplitInbox ──────────────────────────────────────────────────────────
export function SplitInbox({ inbox, mode, onEmailRead, roleKey }: SplitInboxProps) {
    const roleLanes = roleKey ? roleLanesToInternalLanes(getRoleLanes(roleKey)) : undefined;
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
    }, [isModalOpen]);

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

    const displayCount = isImportant
        ? sorted.filter(e => !NON_IMPORTANT_CATEGORIES.includes((e.category || '').toLowerCase().trim())).length
        : sorted.length;

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
                onClose={() => {
                    setIsModalOpen(false);
                    if (openEmailId && onEmailRead) {
                        onEmailRead(openEmailId);
                    }
                }}
            />

            {/* Panel Header */}
            <div className="px-4 py-3 border-b border-nexus-border flex items-center justify-between bg-nexus-bg/80 backdrop-blur-xl z-10 flex-shrink-0">
                <h3 className={`font-semibold flex items-center gap-2 ${isImportant ? 'text-nexus-primary' : 'text-nexus-text'}`}>
                    {isImportant
                        ? <><span className="w-2 h-2 rounded-full bg-nexus-primary animate-pulse" /><Sparkles className="w-4 h-4" /> Important</>
                        : <><Inbox className="w-4 h-4 text-nexus-textMuted" /><span className="text-nexus-textMuted">All Mail</span></>
                    }
                </h3>
                <div className="flex items-center gap-3">
                    {!isImportant && (
                        <span className="text-[10px] text-nexus-textMuted/60 flex items-center gap-1">
                            <GripVertical className="w-3 h-3" /> Drag columns to reorder
                        </span>
                    )}
                    <span className="text-xs bg-nexus-card px-2 py-1 rounded-md text-nexus-textMuted">
                        {displayCount} {displayCount === 1 ? 'item' : 'items'}
                    </span>
                </div>
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
                        activeLanes={roleLanes}
                    />
                )}
            </div>

            {/* Bottom fade */}
            <div className="absolute bottom-0 w-full h-10 bg-gradient-to-t from-nexus-bg to-transparent pointer-events-none" />
        </motion.div>
    );
}
