import { useState, useEffect, useCallback, useRef } from 'react';
import { Calendar, Check, X, Clock, Loader2, AlertTriangle, RefreshCw, Send } from 'lucide-react';
import api from '../api';

export interface MeetingAlert {
    id: string;
    email_id: string;
    sender_name: string;
    sender_email: string;
    email_subject: string;
    proposed_time: string;
    duration_min: number;
    availability: 'free' | 'busy' | 'tentative';
    meeting_link?: string;
    meeting_platform?: string;
    conflicts: { title: string; start: string; end: string }[];
    status: 'pending' | 'accepted' | 'declined' | 'suggested_new_time' | 'dismissed';
}

// ─── Notification sound ───
function playNotificationSound() {
    try {
        const ctx = new AudioContext();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.frequency.value = 880;
        osc.type = 'sine';
        gain.gain.value = 0.15;
        osc.start();
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.5);
        osc.stop(ctx.currentTime + 0.5);
    } catch { /* audio not available */ }
}

type DeclineReason = 'not_interested' | 'change_timing' | 'wrong_person' | 'custom';

export function MeetingAlerts() {
    const [alerts, setAlerts] = useState<MeetingAlert[]>([]);
    const [loading, setLoading] = useState(true);
    const [actionLoading, setActionLoading] = useState<string | null>(null);
    const prevCountRef = useRef(0);

    // Conflict popup state (when user is busy and approves)
    const [conflictPopup, setConflictPopup] = useState<{
        alertId: string;
        conflict: { title: string; start: string; end: string };
    } | null>(null);

    // Decline flow state
    const [declinePopup, setDeclinePopup] = useState<{
        alertId: string;
        senderName: string;
    } | null>(null);
    const [declineReason, setDeclineReason] = useState<DeclineReason>('not_interested');
    const [customReason, setCustomReason] = useState('');
    const [declineDraft, setDeclineDraft] = useState<string | null>(null);
    const [draftCountdown, setDraftCountdown] = useState(0);
    const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

    const fetchAlerts = useCallback(async () => {
        try {
            setLoading(true);
            const res = await api.get('/meetings/pending');
            const data: MeetingAlert[] = res.data.alerts.map((a: any) => ({
                id: a.id || a._id,
                email_id: a.email_id,
                sender_name: a.sender_name || a.sender_email || 'Unknown',
                sender_email: a.sender_email || '',
                email_subject: a.email_subject || '',
                proposed_time: a.proposed_time,
                duration_min: a.duration_min || 60,
                availability: a.availability || 'free',
                meeting_link: a.meeting_link,
                meeting_platform: a.meeting_platform || '',
                conflicts: a.conflicts || [],
                status: a.status,
            }));

            // Play notification if new alerts appeared
            if (data.length > prevCountRef.current && prevCountRef.current > 0) {
                playNotificationSound();
            }
            prevCountRef.current = data.length;

            setAlerts(data);
        } catch (error) {
            console.error("Failed to fetch meetings", error);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchAlerts();
        const interval = setInterval(fetchAlerts, 60000);
        return () => clearInterval(interval);
    }, [fetchAlerts]);

    const handleAccept = async (alert: MeetingAlert) => {
        // If user is busy, show conflict popup first
        if (alert.availability === 'busy' && alert.conflicts.length > 0) {
            setConflictPopup({ alertId: alert.id, conflict: alert.conflicts[0] });
            return;
        }
        await doAccept(alert.id);
    };

    const doAccept = async (alertId: string) => {
        try {
            setActionLoading(alertId);
            setConflictPopup(null);
            await api.post(`/meetings/${alertId}/accept`);
            setAlerts(prev => prev.filter(a => a.id !== alertId));
        } catch (error) {
            console.error("Failed to accept meeting", error);
        } finally {
            setActionLoading(null);
        }
    };

    const handleDeclineClick = (alert: MeetingAlert) => {
        setDeclinePopup({ alertId: alert.id, senderName: alert.sender_name });
        setDeclineReason('not_interested');
        setCustomReason('');
        setDeclineDraft(null);
    };

    const generateDeclineDraft = async () => {
        if (!declinePopup) return;
        const reasonText = declineReason === 'not_interested' ? "I'm not interested in this meeting"
            : declineReason === 'change_timing' ? "I'd like to change the timing"
            : declineReason === 'wrong_person' ? "I'm not the right person for this"
            : customReason || "I need to decline";

        // Generate a quick draft
        setDeclineDraft(`Hi ${declinePopup.senderName},\n\nThank you for the invitation. Unfortunately, ${reasonText.toLowerCase()}.\n\nBest regards`);

        // Start 15s countdown
        setDraftCountdown(15);
        if (countdownRef.current) clearInterval(countdownRef.current);
        countdownRef.current = setInterval(() => {
            setDraftCountdown(prev => {
                if (prev <= 1) {
                    if (countdownRef.current) clearInterval(countdownRef.current);
                    return 0;
                }
                return prev - 1;
            });
        }, 1000);
    };

    const sendDecline = async () => {
        if (!declinePopup) return;
        if (countdownRef.current) clearInterval(countdownRef.current);
        try {
            setActionLoading(declinePopup.alertId);
            const reasonText = declineReason === 'not_interested' ? "Not interested"
                : declineReason === 'change_timing' ? "Timing doesn't work"
                : declineReason === 'wrong_person' ? "Not the right person"
                : customReason || "Declined";
            await api.post(`/meetings/${declinePopup.alertId}/decline`, { reason: reasonText });
            setAlerts(prev => prev.filter(a => a.id !== declinePopup.alertId));
            setDeclinePopup(null);
            setDeclineDraft(null);
        } catch (error) {
            console.error("Failed to decline meeting", error);
        } finally {
            setActionLoading(null);
        }
    };

    // Auto-send when countdown reaches 0
    const sendDeclineRef = useRef(sendDecline);
    sendDeclineRef.current = sendDecline;

    useEffect(() => {
        if (draftCountdown === 0 && declineDraft && declinePopup) {
            sendDeclineRef.current();
        }
    }, [draftCountdown, declineDraft, declinePopup]);

    const cancelDecline = () => {
        if (countdownRef.current) clearInterval(countdownRef.current);
        setDeclinePopup(null);
        setDeclineDraft(null);
        setDraftCountdown(0);
    };

    const handleRescheduleConflict = () => {
        // For now dismiss the conflict popup — the user can use "Suggest Time" from the meeting detail
        setConflictPopup(null);
    };

    if (loading && alerts.length === 0) {
        return null; // silent loading
    }

    if (alerts.length === 0) {
        return null;
    }

    // Greeting
    const hour = new Date().getHours();
    const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';

    return (
        <div className="flex flex-col gap-4">
            <p className="text-sm text-nexus-textMuted">{greeting}! You have pending meeting approvals.</p>

            <h3 className="text-xl font-semibold text-white/90 flex items-center gap-2">
                <Calendar className="w-5 h-5 text-nexus-primary" />
                Pending Meeting Approvals
                <span className="text-xs font-mono bg-nexus-primary/20 text-nexus-primary px-2 py-0.5 rounded-full">{alerts.length}</span>
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {alerts.map(alert => {
                    const proposedDate = new Date(alert.proposed_time);
                    const senderDisplay = alert.sender_name || alert.sender_email.split('@')[0];
                    const isBusy = alert.availability === 'busy';

                    // One-line summary: "Meeting with [sender] on [date] — [subject snippet]"
                    const summaryLine = `${proposedDate.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })} at ${proposedDate.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })}${alert.email_subject ? ` — ${alert.email_subject.slice(0, 50)}` : ''}`;

                    return (
                        <div key={alert.id} className="glass-panel p-4 flex flex-col justify-between border-blue-400/20 shadow-[0_0_15px_rgba(96,165,250,0.05)] relative overflow-hidden">
                            <div className="absolute top-0 right-0 w-24 h-24 bg-blue-400/10 blur-2xl rounded-full pointer-events-none"></div>

                            <div>
                                <div className="flex items-start justify-between mb-2">
                                    <h4 className="font-medium text-white max-w-[80%] truncate">{senderDisplay}</h4>
                                    <div className="flex items-center gap-1.5">
                                        {isBusy && (
                                            <span className="text-[10px] font-semibold bg-red-500/20 text-red-400 px-1.5 py-0.5 rounded flex items-center gap-1">
                                                <AlertTriangle className="w-3 h-3" /> Busy
                                            </span>
                                        )}
                                        <span className="text-xs font-mono bg-blue-500/20 text-blue-400 px-2 py-1 rounded">Proposal</span>
                                    </div>
                                </div>

                                {/* One-line meeting summary */}
                                <p className="text-sm text-white/80 mb-1 line-clamp-1">{summaryLine}</p>

                                <p className="text-xs text-white/50 mb-3 flex items-center gap-2">
                                    <Clock className="w-3.5 h-3.5 opacity-50" />
                                    {alert.duration_min} min
                                    {alert.meeting_platform && <span className="opacity-60">• {alert.meeting_platform}</span>}
                                </p>

                                {/* Conflict warning */}
                                {isBusy && alert.conflicts.length > 0 && (
                                    <div className="mb-3 p-2 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-300">
                                        <span className="font-semibold">Conflict:</span> {alert.conflicts[0].title} ({new Date(alert.conflicts[0].start).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })} - {new Date(alert.conflicts[0].end).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })})
                                    </div>
                                )}
                            </div>

                            <div className="flex items-center gap-2 mt-2">
                                <button
                                    disabled={actionLoading === alert.id}
                                    onClick={() => handleAccept(alert)}
                                    className="flex-1 py-2 px-3 bg-nexus-primary/20 hover:bg-nexus-primary/30 text-nexus-primary text-sm font-medium rounded-lg transition-colors flex items-center justify-center gap-1"
                                >
                                    {actionLoading === alert.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />} Accept
                                </button>
                                <button
                                    disabled={actionLoading === alert.id}
                                    onClick={() => handleDeclineClick(alert)}
                                    className="flex-1 py-2 px-3 bg-red-500/10 hover:bg-red-500/20 text-red-400 text-sm font-medium rounded-lg transition-colors flex items-center justify-center gap-1"
                                >
                                    <X className="w-4 h-4" /> Decline
                                </button>
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* ─── Conflict Popup (busy user approves new meeting) ─── */}
            {conflictPopup && (
                <div className="fixed inset-0 z-[110] flex items-center justify-center p-4 bg-black/60 backdrop-blur-md">
                    <div className="absolute inset-0" onClick={() => setConflictPopup(null)} />
                    <div className="relative glass-panel p-6 max-w-md w-full border-amber-500/30 shadow-[0_0_30px_rgba(245,166,35,0.1)]">
                        <h3 className="text-lg font-semibold text-amber-400 flex items-center gap-2 mb-4">
                            <AlertTriangle className="w-5 h-5" /> Schedule Conflict
                        </h3>
                        <p className="text-sm text-white/80 mb-3">
                            You have a conflicting event:
                        </p>
                        <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 mb-4">
                            <p className="text-sm font-medium text-white">{conflictPopup.conflict.title}</p>
                            <p className="text-xs text-white/60 mt-1">
                                {new Date(conflictPopup.conflict.start).toLocaleString(undefined, { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })} — {new Date(conflictPopup.conflict.end).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })}
                            </p>
                        </div>
                        <p className="text-xs text-white/60 mb-4">Accept the new meeting anyway? You can reschedule the conflicting event.</p>
                        <div className="flex items-center gap-2">
                            <button
                                onClick={() => doAccept(conflictPopup.alertId)}
                                className="flex-1 py-2 px-3 bg-nexus-primary/20 hover:bg-nexus-primary/30 text-nexus-primary text-sm font-medium rounded-lg transition-colors flex items-center justify-center gap-1"
                            >
                                <Check className="w-4 h-4" /> Accept Anyway
                            </button>
                            <button
                                onClick={handleRescheduleConflict}
                                className="flex-1 py-2 px-3 bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 text-sm font-medium rounded-lg transition-colors flex items-center justify-center gap-1"
                            >
                                <RefreshCw className="w-4 h-4" /> Reschedule Old
                            </button>
                            <button
                                onClick={() => setConflictPopup(null)}
                                className="py-2 px-3 bg-white/5 hover:bg-white/10 text-white/60 text-sm rounded-lg transition-colors"
                            >
                                Cancel
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* ─── Decline Popup (reason selection + draft preview) ─── */}
            {declinePopup && (
                <div className="fixed inset-0 z-[110] flex items-center justify-center p-4 bg-black/60 backdrop-blur-md">
                    <div className="absolute inset-0" onClick={cancelDecline} />
                    <div className="relative glass-panel p-6 max-w-md w-full border-red-500/30 shadow-[0_0_30px_rgba(239,68,68,0.1)]">
                        <h3 className="text-lg font-semibold text-red-400 flex items-center gap-2 mb-4">
                            <X className="w-5 h-5" /> Decline Meeting
                        </h3>

                        {!declineDraft ? (
                            <>
                                <p className="text-sm text-white/70 mb-4">Why are you declining?</p>
                                <div className="flex flex-col gap-2 mb-4">
                                    {[
                                        { key: 'not_interested' as DeclineReason, label: 'Not interested' },
                                        { key: 'change_timing' as DeclineReason, label: 'Change timing' },
                                        { key: 'wrong_person' as DeclineReason, label: "I'm not the right person" },
                                        { key: 'custom' as DeclineReason, label: 'Custom reason' },
                                    ].map(opt => (
                                        <button
                                            key={opt.key}
                                            onClick={() => setDeclineReason(opt.key)}
                                            className={`text-left px-3 py-2 rounded-lg border text-sm transition-colors ${
                                                declineReason === opt.key
                                                    ? 'border-red-500/50 bg-red-500/10 text-red-300'
                                                    : 'border-white/10 bg-white/5 text-white/70 hover:bg-white/10'
                                            }`}
                                        >
                                            {opt.label}
                                        </button>
                                    ))}
                                </div>
                                {declineReason === 'custom' && (
                                    <input
                                        type="text"
                                        value={customReason}
                                        onChange={(e) => setCustomReason(e.target.value)}
                                        placeholder="Enter your reason..."
                                        className="w-full bg-white/5 border border-nexus-border rounded-lg px-3 py-2 text-sm text-nexus-text placeholder:text-nexus-textMuted/50 outline-none focus:border-red-500/50 transition-colors mb-4"
                                    />
                                )}
                                <div className="flex items-center gap-2">
                                    <button
                                        onClick={generateDeclineDraft}
                                        className="flex-1 py-2 px-3 bg-red-500/15 hover:bg-red-500/25 text-red-400 text-sm font-medium rounded-lg transition-colors flex items-center justify-center gap-1"
                                    >
                                        Preview Draft
                                    </button>
                                    <button onClick={cancelDecline} className="py-2 px-3 bg-white/5 hover:bg-white/10 text-white/60 text-sm rounded-lg transition-colors">
                                        Cancel
                                    </button>
                                </div>
                            </>
                        ) : (
                            <>
                                <p className="text-xs text-white/50 mb-2">Draft reply — auto-sends in {draftCountdown}s</p>
                                <textarea
                                    value={declineDraft}
                                    onChange={(e) => setDeclineDraft(e.target.value)}
                                    rows={5}
                                    className="w-full bg-white/5 border border-red-500/30 rounded-lg px-3 py-2 text-sm text-nexus-text outline-none focus:border-red-500/50 transition-colors resize-none mb-4"
                                />
                                <div className="flex items-center gap-2">
                                    <button
                                        onClick={sendDecline}
                                        disabled={actionLoading === declinePopup.alertId}
                                        className="flex-1 py-2 px-3 bg-red-500/20 hover:bg-red-500/30 text-red-400 text-sm font-medium rounded-lg transition-colors flex items-center justify-center gap-1"
                                    >
                                        {actionLoading === declinePopup.alertId ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                                        Send Decline
                                    </button>
                                    <button onClick={cancelDecline} className="py-2 px-3 bg-white/5 hover:bg-white/10 text-white/60 text-sm rounded-lg transition-colors">
                                        Don't Send
                                    </button>
                                </div>
                                {/* Auto-send countdown progress bar */}
                                {draftCountdown > 0 && (
                                    <div className="mt-3 h-1 bg-white/10 rounded-full overflow-hidden">
                                        <div
                                            className="h-full bg-red-400 transition-all duration-1000 ease-linear"
                                            style={{ width: `${(draftCountdown / 15) * 100}%` }}
                                        />
                                    </div>
                                )}
                            </>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
