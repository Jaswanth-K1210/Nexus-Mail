import { motion, AnimatePresence } from 'framer-motion';
import { X, Send, Archive, CornerUpLeft, User, Calendar, Loader2, Brain, AlertTriangle, ShieldAlert, MessageSquare, RefreshCw, ClipboardCheck, FileSignature, Banknote, FileCheck, Bell } from 'lucide-react';
import { useEffect, useState } from 'react';
import api from '../../api';

interface EmailDetailModalProps {
    isOpen: boolean;
    onClose: () => void;
    emailId: string;
}

export function EmailDetailModal({ isOpen, onClose, emailId }: EmailDetailModalProps) {
    const [email, setEmail] = useState<any>(null);
    const [threadMessages, setThreadMessages] = useState<any[]>([]);
    const [draft, setDraft] = useState<any>(null);
    const [draftBody, setDraftBody] = useState('');
    const [loading, setLoading] = useState(false);
    const [sending, setSending] = useState(false);
    const [generating, setGenerating] = useState(false);
    const [refining, setRefining] = useState<string | null>(null); // which style is refining
    const [showThread, setShowThread] = useState(false);
    const [showReclassify, setShowReclassify] = useState(false);
    const [reclassifying, setReclassifying] = useState(false);

    useEffect(() => {
        if (isOpen && emailId) {
            setLoading(true);
            setDraft(null);
            setDraftBody('');
            setThreadMessages([]);
            setShowThread(false);

            api.get(`/gmail/emails/${emailId}`).then(async (emailRes) => {
                const emailData = emailRes.data;
                setEmail(emailData);

                // Fetch thread messages if this email belongs to a thread
                if (emailData.thread_id) {
                    try {
                        const threadRes = await api.get(`/gmail/threads/${emailData.thread_id}`);
                        const msgs = threadRes.data.messages || [];
                        if (msgs.length > 1) {
                            setThreadMessages(msgs);
                        }
                    } catch {
                        // Thread fetch is best-effort
                    }
                }

                // Check if a pending draft already exists for this email
                try {
                    const draftsRes = await api.get('/drafts');
                    const drafts = draftsRes.data.drafts || [];
                    const foundDraft = drafts.find((d: any) => d.email_id === emailId);
                    if (foundDraft) {
                        setDraft(foundDraft);
                        setDraftBody(foundDraft.draft_body || '');
                    }
                } catch {
                    // Draft fetch is best-effort
                }
            }).catch(err => {
                console.error("Failed to fetch email details", err);
            }).finally(() => {
                setLoading(false);
            });

        } else {
            setEmail(null);
            setDraft(null);
            setDraftBody('');
            setThreadMessages([]);
        }
    }, [isOpen, emailId]);

    const handleSendDraft = async () => {
        if (!draft) return;
        try {
            setSending(true);
            // Save any edits first
            if (draftBody !== draft.draft_body) {
                await api.put(`/drafts/${draft._id}/edit`, { body: draftBody });
            }
            await api.post(`/drafts/${draft._id}/approve`);
            onClose();
        } catch (err) {
            console.error("Failed to send draft", err);
            alert("Failed to send draft.");
        } finally {
            setSending(false);
        }
    };

    const handleGenerateDraft = async () => {
        if (!emailId) return;
        try {
            setGenerating(true);
            // Delete existing pending draft so regenerate works
            if (draft?._id) {
                try { await api.post(`/drafts/${draft._id}/reject`); } catch { /* ignore */ }
                setDraft(null);
                setDraftBody('');
            }
            const res = await api.post(`/drafts/generate/${emailId}`);
            setDraft(res.data);
            setDraftBody(res.data.draft_body || '');
        } catch (err: any) {
            console.error("Failed to generate draft", err);
            const detail = err?.response?.data?.detail || "Failed to generate draft. Please try again.";
            alert(detail);
        } finally {
            setGenerating(false);
        }
    };

    const handleRefine = async (style: string) => {
        if (!draft?._id) return;
        try {
            setRefining(style);
            const res = await api.post(`/drafts/${draft._id}/refine`, { style });
            setDraft(res.data);
            setDraftBody(res.data.draft_body || '');
        } catch (err) {
            console.error(`Refine (${style}) failed`, err);
            alert(`Failed to ${style} the draft.`);
        } finally {
            setRefining(null);
        }
    };

    const handleReclassify = async (newCategory: string) => {
        if (!emailId) return;
        try {
            setReclassifying(true);
            await api.put(`/gmail/emails/${emailId}/category`, { category: newCategory });
            setEmail((prev: any) => prev ? { ...prev, category: newCategory } : prev);
            setShowReclassify(false);
        } catch (err) {
            console.error("Failed to reclassify", err);
        } finally {
            setReclassifying(false);
        }
    };

    // Get the summary — check both field names for backward compatibility
    const summaryText = email?.ai_summary || email?.summary || null;

    // Hide "Draft a Reply" ONLY for spam and promotional categories.
    const NO_DRAFT_CATEGORIES = ['spam', 'promotional', 'newsletter'];
    const emailCategory = (email?.category || '').toLowerCase().trim();
    const showDraftButton = !NO_DRAFT_CATEGORIES.includes(emailCategory);

    // ── Contextual Action Button config ────────────────────────────────────
    const ACTION_CONFIG: Record<string, { label: string; icon: React.ElementType; color: string; bg: string; border: string }> = {
        'ACTION REQUIRED': { label: 'Action Required', icon: ClipboardCheck, color: 'text-rose-300', bg: 'bg-rose-500/10', border: 'border-rose-500/30' },
        'REVIEW ONLY':     { label: 'Review Only',     icon: FileCheck,       color: 'text-blue-300',  bg: 'bg-blue-500/10',  border: 'border-blue-500/30'  },
        'LOW RELEVANCE':   { label: 'Low Relevance',   icon: Bell,            color: 'text-slate-400', bg: 'bg-slate-500/10', border: 'border-slate-500/30' },
        'AUTO-ARCHIVE':    { label: 'Auto-Archive',    icon: Archive,         color: 'text-purple-400', bg: 'bg-purple-500/10', border: 'border-purple-500/30' },
    };
    const CATEGORY_ACTIONS: Record<string, { label: string; icon: React.ElementType; color: string }> = {
        'contract':           { label: 'Sign Contract',      icon: FileSignature, color: 'text-amber-300'  },
        'invoice_payment':    { label: 'Verify Payment',     icon: Banknote,      color: 'text-emerald-300' },
        'brand_deal':         { label: 'Verify Payment',     icon: Banknote,      color: 'text-emerald-300' },
        'payment':            { label: 'Verify Payment',     icon: Banknote,      color: 'text-emerald-300' },
        'case_update':        { label: 'Review Deadline',    icon: Calendar,      color: 'text-rose-300'   },
        'court_notice':       { label: 'Review Deadline',    icon: Calendar,      color: 'text-rose-300'   },
        'exam_notice':        { label: 'Review Deadline',    icon: Calendar,      color: 'text-amber-300'  },
        'deadline_reminder':  { label: 'Review Deadline',    icon: Calendar,      color: 'text-amber-300'  },
        'work_order':         { label: 'Flag Urgent',        icon: AlertTriangle, color: 'text-red-400'    },
        'compliance_safety':  { label: 'Flag Urgent',        icon: AlertTriangle, color: 'text-red-400'    },
        'lab_results':        { label: 'Review Urgent',      icon: ClipboardCheck,color: 'text-rose-300'   },
        'escrow_legal':       { label: 'Flag Closing',       icon: FileCheck,     color: 'text-rose-400'   },
        'investor_communication': { label: 'Reply Required', icon: CornerUpLeft,  color: 'text-blue-300'   },
        'grant_application':  { label: 'Review Deadline',    icon: Calendar,      color: 'text-amber-300'  },
    };
    const suggestedActionRaw: string = (email?.suggested_action || 'REVIEW ONLY').toUpperCase();
    const actionCfg = ACTION_CONFIG[suggestedActionRaw] || ACTION_CONFIG['REVIEW ONLY'];
    const ActionIcon = actionCfg.icon;
    const catAction = CATEGORY_ACTIONS[emailCategory] || null;

    return (
        <AnimatePresence>
            {isOpen && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6 bg-black/60 backdrop-blur-md">

                    {/* Background click to close */}
                    <div className="absolute inset-0" onClick={onClose} />

                    {/* Modal Container */}
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: 20 }}
                        transition={{ type: "spring", damping: 25, stiffness: 300 }}
                        className="relative w-full max-w-4xl h-[85vh] flex flex-col glass-panel overflow-hidden shadow-[0_0_50px_rgba(177,158,239,0.15)] bg-nexus-bg"
                    >
                        {loading || !email ? (
                            <div className="flex-1 flex flex-col items-center justify-center text-nexus-textMuted">
                                <Loader2 className="w-8 h-8 animate-spin text-nexus-primary mb-4" />
                                <p>Loading Intelligence Data...</p>
                            </div>
                        ) : (
                            <>
                                {/* Header */}
                                <div className="flex items-start justify-between p-6 border-b border-nexus-border backdrop-blur-3xl bg-white/5">
                                    <div className="flex gap-4">
                                        <div className="w-12 h-12 rounded-full bg-gradient-to-tr from-nexus-primary to-blue-500 flex items-center justify-center shadow-lg text-lg font-bold text-white uppercase">
                                            {email.sender_name?.charAt(0) || email.sender_email?.charAt(0) || 'U'}
                                        </div>
                                        <div>
                                            <h2 className="text-xl font-semibold text-nexus-text">{email.subject || "No Subject"}</h2>
                                            <p className="text-nexus-textMuted text-sm flex items-center gap-2 mt-1">
                                                <User className="w-4 h-4" /> {email.sender_name || email.sender_email || 'Unknown'}
                                                <span className="opacity-50">•</span>
                                                <span className="opacity-70 font-mono text-xs">{new Date(email.received_at).toLocaleString()}</span>
                                                {threadMessages.length > 1 && (
                                                    <>
                                                        <span className="opacity-50">•</span>
                                                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-nexus-primary/15 text-nexus-primary font-mono">
                                                            {threadMessages.length} in thread
                                                        </span>
                                                    </>
                                                )}
                                            </p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <button className="glass-button !py-2 !px-3 !rounded-lg text-nexus-textMuted hover:text-nexus-text">
                                            <Archive className="w-4 h-4" />
                                        </button>
                                        <button onClick={onClose} className="glass-button !py-2 !px-3 !rounded-lg text-nexus-textMuted hover:text-nexus-text border-red-500/20 hover:bg-red-500/10 hover:text-red-400">
                                            <X className="w-4 h-4" />
                                        </button>
                                    </div>
                                </div>

                                {/* Scrollable Body */}
                                <div className="flex-1 overflow-y-auto custom-scrollbar p-6 flex flex-col lg:flex-row gap-6">

                                    {/* Left Column: Email Content */}
                                    <div className="flex-1 flex flex-col gap-6">
                                        <div className="prose prose-invert max-w-none text-nexus-textMuted leading-relaxed whitespace-pre-wrap font-sans text-sm">
                                            {email.body_text || email.snippet || "No textual content extracted."}
                                        </div>

                                        {/* Thread / Conversation History */}
                                        {threadMessages.length > 1 && (
                                            <>
                                                <div className="h-px bg-nexus-border w-full"></div>
                                                <button
                                                    onClick={() => setShowThread(!showThread)}
                                                    className="flex items-center gap-2 text-xs text-nexus-primary hover:text-nexus-primary/80 transition-colors font-mono uppercase tracking-wider"
                                                >
                                                    <MessageSquare className="w-3.5 h-3.5" />
                                                    {showThread ? 'Hide' : 'Show'} Conversation ({threadMessages.length} messages)
                                                </button>
                                                {showThread && (
                                                    <div className="flex flex-col gap-3">
                                                        {threadMessages.map((msg: any, idx: number) => (
                                                            <div
                                                                key={idx}
                                                                className={`glass-panel p-3 border text-sm ${
                                                                    msg.gmail_id === email.gmail_id
                                                                        ? 'border-nexus-primary/30 bg-nexus-primary/5'
                                                                        : 'border-white/5 bg-white/[0.02]'
                                                                }`}
                                                            >
                                                                <div className="flex items-center gap-2 mb-2 text-xs text-nexus-textMuted">
                                                                    <span className="font-semibold text-nexus-text">
                                                                        {msg.sender_name || msg.sender_email}
                                                                    </span>
                                                                    <span className="opacity-50">•</span>
                                                                    <span className="font-mono opacity-70">
                                                                        {msg.received_at ? new Date(msg.received_at).toLocaleString() : ''}
                                                                    </span>
                                                                    {msg.gmail_id === email.gmail_id && (
                                                                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-nexus-primary/20 text-nexus-primary uppercase tracking-wider">
                                                                            Current
                                                                        </span>
                                                                    )}
                                                                </div>
                                                                <p className="text-nexus-textMuted whitespace-pre-wrap leading-relaxed">
                                                                    {msg.body_text || msg.snippet || ''}
                                                                </p>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                            </>
                                        )}
                                    </div>

                                    {/* Right Column: AI Intelligence Sidebar */}
                                    <div className="w-full lg:w-80 flex flex-col gap-4">

                                        {/* Contextual Action Banner */}
                                        <div className={`flex items-center justify-between px-3 py-2 rounded-lg border ${actionCfg.bg} ${actionCfg.border}`}>
                                            <div className="flex items-center gap-2">
                                                <ActionIcon className={`w-3.5 h-3.5 ${actionCfg.color}`} />
                                                <span className={`text-xs font-semibold uppercase tracking-wider ${actionCfg.color}`}>
                                                    {actionCfg.label}
                                                </span>
                                            </div>
                                            {catAction && (
                                                <span className={`text-[10px] px-2 py-0.5 rounded-full bg-white/10 border border-white/10 font-medium flex items-center gap-1 ${catAction.color}`}>
                                                    <catAction.icon className="w-3 h-3" />
                                                    {catAction.label}
                                                </span>
                                            )}
                                        </div>

                                        {/* AI Summary Card */}
                                        <div className="glass-panel p-4 bg-nexus-primary/5 border border-nexus-primary/20">
                                            <h4 className="text-xs font-mono font-bold text-nexus-primary uppercase tracking-wider mb-3 flex items-center gap-2">
                                                <span className="w-2 h-2 rounded-full bg-nexus-primary animate-pulse"></span>
                                                AI Summary
                                            </h4>
                                            <p className="text-sm text-nexus-text flex-1 font-medium leading-relaxed">
                                                {summaryText || "Summary will be generated when the email is processed."}
                                            </p>
                                            <div className="mt-4 flex items-center gap-2">
                                                <span className={`text-[10px] px-2 py-1 rounded uppercase tracking-wider font-semibold ${email.priority_score >= 80 ? 'bg-nexus-primary/20 text-nexus-primary' :
                                                    email.priority_score >= 50 ? 'bg-blue-500/20 text-blue-400' : 'bg-white/10 text-white/70'
                                                    }`}>
                                                    Priority: {email.priority_score}/100
                                                </span>
                                                {email.category && (
                                                    <span className="text-[10px] px-2 py-1 rounded bg-white/10 text-nexus-textMuted uppercase tracking-wider font-semibold">
                                                        {email.category}
                                                    </span>
                                                )}
                                                <button
                                                    onClick={() => setShowReclassify(!showReclassify)}
                                                    className="text-[10px] px-2 py-1 rounded bg-white/5 hover:bg-white/10 text-nexus-textMuted hover:text-nexus-text transition-colors flex items-center gap-1 border border-white/10"
                                                    title="Wrong category? Reclassify this email"
                                                >
                                                    <RefreshCw className="w-3 h-3" /> Not {email.category}?
                                                </button>
                                            </div>

                                            {/* Reclassify dropdown */}
                                            {showReclassify && (
                                                <div className="mt-3 flex flex-wrap gap-1.5">
                                                    {['important', 'requires_response', 'meeting_invitation', 'newsletter', 'promotional', 'social', 'transactional', 'spam']
                                                        .filter(c => c !== email.category)
                                                        .map(cat => (
                                                            <button
                                                                key={cat}
                                                                disabled={reclassifying}
                                                                onClick={() => handleReclassify(cat)}
                                                                className="text-[10px] px-2 py-1 rounded bg-white/5 hover:bg-nexus-primary/20 hover:text-nexus-primary text-nexus-textMuted border border-white/10 hover:border-nexus-primary/30 transition-colors capitalize"
                                                            >
                                                                {cat.replace('_', ' ')}
                                                            </button>
                                                        ))
                                                    }
                                                </div>
                                            )}
                                        </div>

                                        {/* Security & Safety Alerts */}
                                        {email.risk_flags && email.risk_flags.length > 0 && (
                                            <div className="glass-panel p-4 bg-red-500/10 border border-red-500/30 shadow-[0_0_15px_rgba(239,68,68,0.1)]">
                                                <h4 className="text-xs font-mono font-bold text-red-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                                                    <ShieldAlert className="w-4 h-4" />
                                                    Security & Risk Warning
                                                </h4>
                                                <ul className="flex flex-col gap-2">
                                                    {email.risk_flags.map((risk: any, i: number) => (
                                                        <li key={i} className="text-xs text-red-200/90 flex items-start gap-2 leading-relaxed">
                                                            <span className="w-1.5 h-1.5 rounded-full bg-red-400 mt-1.5 shrink-0"></span>
                                                            {typeof risk === 'string' ? risk : risk.description || Object.values(risk)[0]}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}

                                        {/* Action Items Card */}
                                        {email.action_items && email.action_items.length > 0 && (
                                            <div className="glass-panel p-4 outline outline-amber-500/20 shadow-[0_0_15px_rgba(245,166,35,0.05)]">
                                                <h4 className="text-xs font-mono font-bold text-amber-400 uppercase tracking-wider mb-3">
                                                    Identified Actions ({email.action_items.length})
                                                </h4>
                                                <div className="flex flex-col gap-2">
                                                    {email.action_items.map((action: any, idx: number) => {
                                                        // Support both flat strings and object format
                                                        const taskText = typeof action === 'string' ? action : action.task || action.action || '';
                                                        const dueDate = typeof action === 'object' ? action.due_date || action.deadline : null;
                                                        const assignee = typeof action === 'object' ? action.assignee : null;
                                                        return (
                                                            <div key={idx} className="flex items-start gap-3 bg-white/5 p-3 rounded-lg border border-white/5">
                                                                <input type="checkbox" className="mt-1 accent-amber-500 rounded cursor-pointer" />
                                                                <div>
                                                                    <p className="text-sm text-nexus-text">{taskText}</p>
                                                                    {(dueDate || assignee) && (
                                                                        <p className="text-xs text-amber-400 mt-1 flex items-center gap-1">
                                                                            <Calendar className="w-3 h-3" />
                                                                            {dueDate ? `Due: ${dueDate}` : ""} {assignee ? `| Assigned: ${assignee}` : ""}
                                                                        </p>
                                                                    )}
                                                                </div>
                                                            </div>
                                                        );
                                                    })}
                                                </div>
                                            </div>
                                        )}
                                    </div>

                                </div>

                                {/* Footer: Draft & Compose Area — hidden for donotreply, otps, promotions, meetings */}
                                {!showDraftButton ? null : !draft ? (
                                    <div className="p-4 border-t border-nexus-border bg-white/5 backdrop-blur-xl flex justify-center items-center">
                                        <button
                                            onClick={handleGenerateDraft}
                                            disabled={generating}
                                            className={`glass-button flex items-center gap-2 px-6 py-3 ${generating ? 'opacity-50' : 'hover:bg-nexus-primary/20 hover:text-nexus-primary hover:border-nexus-primary/50'}`}
                                        >
                                            {generating ? <Loader2 className="w-5 h-5 animate-spin" /> : <Brain className="w-5 h-5" />}
                                            <span className="font-semibold">
                                                {generating ? 'Generating Contextual Reply...' : 'Draft a Reply'}
                                            </span>
                                        </button>
                                    </div>
                                ) : (
                                    <div className="p-4 border-t border-nexus-border bg-white/5 backdrop-blur-xl">
                                        <div className="glass-panel p-4 border border-nexus-primary/30 shadow-[0_0_20px_rgba(177,158,239,0.1)] focus-within:border-nexus-primary transition-all">
                                            <h4 className="text-xs font-mono font-bold text-nexus-primary uppercase tracking-wider mb-3 flex items-center gap-2">
                                                <CornerUpLeft className="w-3 h-3" /> AI Generated Draft
                                            </h4>
                                            <textarea
                                                className="w-full bg-transparent border-none outline-none text-nexus-text resize-none text-sm placeholder:text-nexus-textMuted custom-scrollbar"
                                                rows={4}
                                                value={draftBody}
                                                onChange={(e) => setDraftBody(e.target.value)}
                                            ></textarea>
                                            <div className="flex justify-between items-center mt-3 flex-wrap gap-4">
                                                <div className="flex gap-2">
                                                    <button
                                                        onClick={() => handleRefine('polish')}
                                                        disabled={!!refining}
                                                        className={`text-xs px-2.5 py-1.5 rounded bg-white/5 border border-white/10 hover:bg-nexus-primary/20 hover:border-nexus-primary/30 text-white/70 hover:text-nexus-primary transition-colors flex items-center gap-1.5 ${refining === 'polish' ? 'opacity-50' : ''}`}
                                                    >
                                                        {refining === 'polish' ? <Loader2 className="w-3 h-3 animate-spin" /> : <>✨</>} Polish
                                                    </button>
                                                    <button
                                                        onClick={() => handleRefine('formal')}
                                                        disabled={!!refining}
                                                        className={`text-xs px-2.5 py-1.5 rounded bg-white/5 border border-white/10 hover:bg-nexus-primary/20 hover:border-nexus-primary/30 text-white/70 hover:text-nexus-primary transition-colors flex items-center gap-1.5 ${refining === 'formal' ? 'opacity-50' : ''}`}
                                                    >
                                                        {refining === 'formal' ? <Loader2 className="w-3 h-3 animate-spin" /> : <>👔</>} Formal
                                                    </button>
                                                    <button
                                                        onClick={() => handleRefine('shorter')}
                                                        disabled={!!refining}
                                                        className={`text-xs px-2.5 py-1.5 rounded bg-white/5 border border-white/10 hover:bg-nexus-primary/20 hover:border-nexus-primary/30 text-white/70 hover:text-nexus-primary transition-colors flex items-center gap-1.5 ${refining === 'shorter' ? 'opacity-50' : ''}`}
                                                    >
                                                        {refining === 'shorter' ? <Loader2 className="w-3 h-3 animate-spin" /> : <>📝</>} Shorter
                                                    </button>
                                                    <button
                                                        onClick={() => handleRefine('casual')}
                                                        disabled={!!refining}
                                                        className={`text-xs px-2.5 py-1.5 rounded bg-white/5 border border-white/10 hover:bg-nexus-primary/20 hover:border-nexus-primary/30 text-white/70 hover:text-nexus-primary transition-colors flex items-center gap-1.5 ${refining === 'casual' ? 'opacity-50' : ''}`}
                                                    >
                                                        {refining === 'casual' ? <Loader2 className="w-3 h-3 animate-spin" /> : <>💬</>} Casual
                                                    </button>
                                                    <button
                                                        onClick={handleGenerateDraft}
                                                        disabled={generating}
                                                        className={`text-xs px-2.5 py-1.5 rounded bg-white/5 border border-white/10 hover:bg-red-500/20 hover:border-red-500/30 text-white/70 hover:text-red-400 transition-colors flex items-center gap-1.5`}
                                                        title="Regenerate from scratch"
                                                    >
                                                        {generating ? <Loader2 className="w-3 h-3 animate-spin" /> : <>🔄</>} Regenerate
                                                    </button>
                                                </div>
                                                <div className="flex items-center gap-4">
                                                    <span className="text-xs text-nexus-textMuted flex items-center gap-2" title="AI Confidence matching your writing style">
                                                        <span className={`w-2 h-2 rounded-full ${draft.ai_confidence >= 0.8 ? 'bg-green-500' : draft.ai_confidence >= 0.5 ? 'bg-amber-500' : 'bg-red-500'}`}></span>
                                                        {Math.round((draft.ai_confidence || 0) * 100)}% Match
                                                    </span>
                                                    <button
                                                        onClick={handleSendDraft}
                                                        disabled={sending || !draftBody.trim()}
                                                        className={`glass-button glass-button-primary !py-2 !px-4 !text-sm flex items-center gap-2 ${sending ? 'opacity-50' : ''}`}
                                                    >
                                                        {sending ? <Loader2 className="w-4 h-4 animate-spin flex-shrink-0" /> : <Send className="w-4 h-4 flex-shrink-0" />}
                                                        {sending ? 'Sending...' : 'Send Reply'}
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </>
                        )}
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    );
}
