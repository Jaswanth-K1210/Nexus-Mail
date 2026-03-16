import { useState, useEffect } from 'react';
import { Zap, Clock, Mail, ChevronDown, ChevronUp, Loader2, AlertCircle, Send } from 'lucide-react';
import api from '../api';

interface AutoReply {
    id: string;
    email_id: string;
    sender_name: string;
    sender_email: string;
    subject: string;
    category: string;
    priority_score: number;
    reply_text: string;
    confidence: number;
    status: string;
    sent_at: string | null;
}

const CATEGORY_COLORS: Record<string, string> = {
    newsletter: 'text-blue-400 bg-blue-500/10',
    transactional: 'text-emerald-400 bg-emerald-500/10',
    social: 'text-pink-400 bg-pink-500/10',
    promotional: 'text-amber-400 bg-amber-500/10',
    requires_response: 'text-purple-400 bg-purple-500/10',
};

export function AutoReplyLog() {
    const [replies, setReplies] = useState<AutoReply[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);
    const [expandedId, setExpandedId] = useState<string | null>(null);
    const [stats, setStats] = useState<{ total_auto_replies: number } | null>(null);

    const fetchData = async () => {
        try {
            setLoading(true);
            setError(false);
            const [logRes, statsRes] = await Promise.all([
                api.get('/auto-reply/log'),
                api.get('/auto-reply/stats'),
            ]);
            setReplies(logRes.data.replies || []);
            setStats(statsRes.data || null);
        } catch {
            setError(true);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    if (loading) {
        return (
            <div className="glass-panel p-6 flex items-center justify-center">
                <Loader2 className="w-5 h-5 animate-spin text-nexus-primary" />
            </div>
        );
    }

    if (error) {
        return (
            <div className="glass-panel p-6 flex flex-col items-center gap-2">
                <AlertCircle className="w-5 h-5 text-nexus-textMuted" />
                <p className="text-sm text-nexus-textMuted">Could not load auto-reply log</p>
                <button onClick={fetchData} className="text-xs text-nexus-primary hover:underline">Retry</button>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {/* Header with stats */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Zap className="w-5 h-5 text-nexus-primary" />
                    <h3 className="text-lg font-semibold text-nexus-text">Auto-Reply Log</h3>
                </div>
                {stats && (
                    <span className="text-xs font-mono px-2 py-1 rounded-full bg-nexus-primary/15 text-nexus-primary">
                        {stats.total_auto_replies} sent
                    </span>
                )}
            </div>

            {replies.length === 0 ? (
                <div className="glass-panel p-8 flex flex-col items-center gap-3">
                    <Send className="w-8 h-8 text-nexus-textMuted/40" />
                    <p className="text-sm text-nexus-textMuted">No auto-replies sent yet</p>
                    <p className="text-xs text-nexus-textMuted/60">
                        When enabled, Nexus will automatically reply to low-priority emails that just need a quick acknowledgement.
                    </p>
                </div>
            ) : (
                <div className="flex flex-col gap-2">
                    {replies.map(reply => {
                        const isExpanded = expandedId === reply.id;
                        const sentDate = reply.sent_at ? new Date(reply.sent_at) : null;
                        const catColor = CATEGORY_COLORS[reply.category] || 'text-white/50 bg-white/5';

                        return (
                            <div
                                key={reply.id}
                                className="glass-panel border border-nexus-border/50 overflow-hidden transition-all hover:border-nexus-primary/20"
                            >
                                <div
                                    className="p-4 cursor-pointer flex items-start justify-between gap-3"
                                    onClick={() => setExpandedId(isExpanded ? null : reply.id)}
                                >
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <Mail className="w-3.5 h-3.5 text-nexus-primary shrink-0" />
                                            <span className="text-sm font-medium text-nexus-text truncate">
                                                {reply.sender_name || reply.sender_email.split('@')[0]}
                                            </span>
                                            <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium uppercase ${catColor}`}>
                                                {reply.category}
                                            </span>
                                        </div>
                                        <p className="text-xs text-nexus-textMuted truncate">{reply.subject}</p>
                                        {sentDate && (
                                            <p className="text-[10px] text-nexus-textMuted/50 mt-1 flex items-center gap-1">
                                                <Clock className="w-3 h-3" />
                                                {sentDate.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })} at {sentDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                            </p>
                                        )}
                                    </div>
                                    <div className="flex items-center gap-2 shrink-0">
                                        <span className="text-[10px] text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded font-semibold">
                                            Sent
                                        </span>
                                        {isExpanded
                                            ? <ChevronUp className="w-4 h-4 text-nexus-textMuted" />
                                            : <ChevronDown className="w-4 h-4 text-nexus-textMuted" />
                                        }
                                    </div>
                                </div>

                                {isExpanded && (
                                    <div className="border-t border-nexus-border/50 p-4 bg-black/20">
                                        <p className="text-[10px] text-nexus-textMuted uppercase tracking-wide font-medium mb-2">Reply Sent</p>
                                        <div className="bg-nexus-primary/5 border border-nexus-primary/15 rounded-lg p-3">
                                            <p className="text-sm text-nexus-text leading-relaxed whitespace-pre-wrap">
                                                {reply.reply_text}
                                            </p>
                                        </div>
                                        <div className="flex items-center gap-4 mt-3 text-[10px] text-nexus-textMuted/60">
                                            <span>To: {reply.sender_email}</span>
                                            <span>Confidence: {Math.round(reply.confidence * 100)}%</span>
                                            <span>Priority: {reply.priority_score}/100</span>
                                        </div>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
