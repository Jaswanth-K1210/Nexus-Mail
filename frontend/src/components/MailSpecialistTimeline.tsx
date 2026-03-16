import { useState, useEffect, useRef } from 'react';
import { Calendar as CalendarIcon, Clock, MapPin, Video, Loader2, Target, ChevronRight, Briefcase, AlertCircle, Check, X, RefreshCw } from 'lucide-react';
import api from '../api';

export interface CalendarEvent {
    id: string;
    summary: string;
    start: string;
    end: string;
    location?: string;
    link?: string;
    local_status?: string;
}

export interface ActionItem {
    id: string;
    type: string;
    text: string;
    status: string;
    source_sender: string;
    source_subject: string;
    received_at: string;
    source_quote?: string;
}

export interface KeyConversation {
    _id: string; // sender email
    count: number;
}

export interface ReplyStats {
    needs_reply: number;
    awaiting_reply: number;
    overdue: number;
}

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
    done: { label: 'Done', color: 'text-emerald-400', bg: 'bg-emerald-500/15' },
    cancelled: { label: 'Cancelled', color: 'text-red-400', bg: 'bg-red-500/15' },
    rescheduled: { label: 'Rescheduled', color: 'text-amber-400', bg: 'bg-amber-500/15' },
    resolved: { label: 'Resolved', color: 'text-blue-400', bg: 'bg-blue-500/15' },
};

export function MailSpecialistTimeline({ fullWidth = false }: { fullWidth?: boolean }) {
    const [events, setEvents] = useState<CalendarEvent[]>([]);
    const [actions, setActions] = useState<ActionItem[]>([]);
    const [topSenders, setTopSenders] = useState<KeyConversation[]>([]);
    const [replyStats, setReplyStats] = useState<ReplyStats | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);
    const [localStatuses, setLocalStatuses] = useState<Record<string, string>>({});
    const nowRef = useRef(new Date());

    // Keep "now" fresh for NOW badges
    useEffect(() => {
        const interval = setInterval(() => { nowRef.current = new Date(); }, 60000);
        return () => clearInterval(interval);
    }, []);

    const fetchData = async () => {
        try {
            setLoading(true);
            setError(false);
            const [timelineRes, sendersRes, statsRes] = await Promise.all([
                api.get('/assistant/timeline').catch(() => ({ data: {} })),
                api.get('/analytics/top-senders').catch(() => ({ data: {} })),
                api.get('/replies/stats').catch(() => ({ data: {} })),
            ]);
            const cal = timelineRes.data.calendar_events || [];
            const act = timelineRes.data.action_items || [];
            setEvents(cal);
            setActions(act);
            setLocalStatuses({});
            setTopSenders(sendersRes.data.data?.slice(0, 4) || []);
            setReplyStats(statsRes.data || null);
            if (cal.length === 0 && act.length === 0 && !sendersRes.data.data && !statsRes.data.needs_reply) {
                setError(true);
            }
        } catch (err) {
            console.error("Failed to fetch command center data", err);
            setError(true);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 5 * 60000);
        return () => clearInterval(interval);
    }, []);

    const handleStatusUpdate = async (actionId: string, newStatus: string) => {
        setLocalStatuses(prev => ({ ...prev, [actionId]: newStatus }));
        try {
            await api.post('/assistant/timeline/resolve', { action_id: actionId, status: newStatus });
        } catch (err) {
            console.error("Failed to persist action status", err);
        }
    };

    const getEffectiveStatus = (action: ActionItem): string => {
        return localStatuses[action.id] ?? action.status ?? 'pending';
    };

    const getEventStatus = (event: CalendarEvent): string => {
        const key = `event_${event.id}`;
        return localStatuses[key] ?? event.local_status ?? 'pending';
    };

    const handleEventStatusUpdate = async (eventId: string, newStatus: string) => {
        const key = `event_${eventId}`;
        setLocalStatuses(prev => ({ ...prev, [key]: newStatus }));
        try {
            await api.post('/assistant/timeline/resolve', { action_id: key, status: newStatus });
        } catch (err) {
            console.error("Failed to persist event status", err);
        }
    };

    if (error && events.length === 0 && actions.length === 0) {
        return (
            <div className={`glass-panel p-6 flex flex-col items-center justify-center h-full ${fullWidth ? 'w-full' : 'w-full xl:w-[400px]'}`}>
                <AlertCircle className="w-6 h-6 text-nexus-textMuted mb-3" />
                <p className="text-sm text-nexus-textMuted mb-1">Could not load action center</p>
                <p className="text-xs text-nexus-textMuted/60 mb-4">Check your connection and try again</p>
                <button onClick={fetchData} className="text-xs text-nexus-primary hover:underline">Retry</button>
            </div>
        );
    }

    if (loading && events.length === 0 && actions.length === 0) {
        return (
            <div className={`glass-panel p-6 flex flex-col items-center justify-center h-full ${fullWidth ? 'w-full' : 'w-full xl:w-[400px]'}`}>
                <Loader2 className="w-6 h-6 animate-spin text-nexus-primary" />
                <p className="mt-4 text-white/50 text-sm">Reviewing your upcoming schedule & deadlines...</p>
            </div>
        );
    }

    // --- Group Events by Date ---
    const groupedEvents: Record<string, CalendarEvent[]> = {};
    const todayStr = new Date().toDateString();

    events.forEach(event => {
        const d = new Date(event.start);
        const key = d.toDateString() === todayStr ? 'Today' : d.toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' });

        if (!groupedEvents[key]) groupedEvents[key] = [];
        groupedEvents[key].push(event);
    });

    const isMeetingType = (type: string) => type === 'schedule' || type === 'meeting';

    return (
        <div className={`glass-panel h-full flex flex-col overflow-hidden relative shadow-[0_0_15px_rgba(177,158,239,0.05)] border-nexus-primary/10 ${fullWidth ? 'w-full' : 'w-full xl:w-[450px]'}`}>
            <div className="p-4 border-b border-white/10 flex items-center justify-between sticky top-0 bg-black/40 backdrop-blur-xl z-10">
                <h3 className="font-semibold text-white/90 flex items-center gap-2">
                    <Briefcase className="w-4 h-4 text-nexus-primary" />
                    Action Center & Timeline
                </h3>
            </div>

            <div className={`p-4 overflow-y-auto custom-scrollbar flex flex-col gap-6 flex-1 pb-20 ${fullWidth ? 'max-w-4xl mx-auto w-full' : ''}`}>

                {/* Section 0: Follow-Up Automation */}
                {replyStats && (replyStats.needs_reply > 0 || replyStats.awaiting_reply > 0 || replyStats.overdue > 0) && (
                    <div className="mb-2 bg-gradient-to-r from-amber-500/10 to-transparent border-l-2 border-amber-500/50 p-3 rounded-r-lg">
                        <div className="flex items-center justify-between mb-2 px-1">
                            <h4 className="font-medium text-amber-300 text-sm tracking-wide uppercase flex items-center gap-2">
                                <Clock className="w-4 h-4" /> Follow-Ups
                            </h4>
                        </div>
                        <div className="flex justify-between text-xs text-white/70 px-1">
                            {replyStats.needs_reply > 0 && <span>You need to reply: <strong className="text-white">{replyStats.needs_reply}</strong></span>}
                            {replyStats.awaiting_reply > 0 && <span>Awaiting: <strong className="text-white">{replyStats.awaiting_reply}</strong></span>}
                            {replyStats.overdue > 0 && <span className="text-rose-400 font-medium">Overdue: {replyStats.overdue}</span>}
                        </div>
                    </div>
                )}

                {/* Section 1: Deadlines and Action Items */}
                {actions.length > 0 && (() => {
                    const displayActions = actions.slice(0, 8);
                    if (displayActions.length === 0) return null;
                    return (
                        <div className="mb-2">
                            <div className="flex items-center gap-2 mb-3 px-1">
                                <Target className="w-4 h-4 text-rose-400" />
                                <h4 className="font-medium text-white/80 text-sm tracking-wide uppercase">Extracted Action Items</h4>
                            </div>
                            <div className="flex flex-col gap-2">
                                {displayActions.map((action, i) => {
                                    const effectiveStatus = getEffectiveStatus(action);
                                    const isActioned = effectiveStatus !== 'pending';
                                    const statusCfg = STATUS_CONFIG[effectiveStatus];
                                    const meetingItem = isMeetingType(action.type);

                                    return (
                                        <div
                                            key={action.id || i}
                                            className={`border-l-2 p-3 rounded-r-lg group relative transition-all ${
                                                isActioned
                                                    ? 'bg-white/[0.02] border-white/10 opacity-60'
                                                    : meetingItem
                                                        ? 'bg-gradient-to-r from-blue-500/5 to-transparent border-blue-500/50'
                                                        : 'bg-gradient-to-r from-red-500/5 to-transparent border-rose-500/50'
                                            }`}
                                        >
                                            <div className="flex items-start justify-between gap-2 mb-2">
                                                <p className={`text-sm leading-relaxed ${isActioned ? 'text-white/50 line-through' : 'text-white/90'}`}>
                                                    {action.text}
                                                </p>
                                                {isActioned && statusCfg && (
                                                    <span className={`shrink-0 px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide ${statusCfg.color} ${statusCfg.bg}`}>
                                                        {statusCfg.label}
                                                    </span>
                                                )}
                                            </div>

                                            {action.source_quote && !isActioned && (
                                                <div className="mb-3 px-3 py-2 bg-black/40 border border-white/5 shadow-inner rounded text-xs text-white/50 italic relative overflow-hidden">
                                                    <div className="absolute top-0 left-0 w-1 h-full bg-nexus-primary/50"></div>
                                                    <span className="font-semibold text-nexus-primary/70 not-italic mr-1">"</span>
                                                    {action.source_quote}
                                                    <span className="font-semibold text-nexus-primary/70 not-italic ml-1">"</span>
                                                </div>
                                            )}

                                            <div className="flex items-center justify-between">
                                                <p className="text-[10px] text-white/40 flex items-center gap-1">
                                                    <ChevronRight className="w-3 h-3" /> From: {action.source_sender}
                                                </p>

                                                {!isActioned && (
                                                    <div className="flex items-center gap-1.5">
                                                        {meetingItem ? (
                                                            <>
                                                                <button
                                                                    onClick={() => handleStatusUpdate(action.id, 'done')}
                                                                    className="flex items-center gap-1 text-emerald-400 hover:text-white transition-colors bg-emerald-500/10 hover:bg-emerald-500/20 px-2 py-0.5 rounded text-xs"
                                                                    title="Mark as done"
                                                                >
                                                                    <Check className="w-3 h-3" /> Done
                                                                </button>
                                                                <button
                                                                    onClick={() => handleStatusUpdate(action.id, 'rescheduled')}
                                                                    className="flex items-center gap-1 text-amber-400 hover:text-white transition-colors bg-amber-500/10 hover:bg-amber-500/20 px-2 py-0.5 rounded text-xs"
                                                                    title="Reschedule"
                                                                >
                                                                    <RefreshCw className="w-3 h-3" /> Reschedule
                                                                </button>
                                                                <button
                                                                    onClick={() => handleStatusUpdate(action.id, 'cancelled')}
                                                                    className="flex items-center gap-1 text-red-400 hover:text-white transition-colors bg-red-500/10 hover:bg-red-500/20 px-2 py-0.5 rounded text-xs"
                                                                    title="Cancel meeting"
                                                                >
                                                                    <X className="w-3 h-3" /> Cancel
                                                                </button>
                                                            </>
                                                        ) : (
                                                            <button
                                                                onClick={() => handleStatusUpdate(action.id, 'resolved')}
                                                                className="text-rose-400 hover:text-white transition-colors bg-rose-500/10 hover:bg-rose-500/20 px-2 py-0.5 rounded text-xs"
                                                            >
                                                                Resolve
                                                            </button>
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    );
                })()}

                {/* Key Conversations */}
                {topSenders.length > 0 && (
                    <div className="mb-2">
                        <div className="flex items-center gap-2 mb-3 px-1">
                            <svg className="w-4 h-4 text-nexus-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                            </svg>
                            <h4 className="font-medium text-nexus-text text-sm tracking-wide uppercase">Key Conversations</h4>
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                            {topSenders.map(sender => (
                                <div key={sender._id || Math.random()} className="p-2 border border-nexus-border bg-nexus-cardHover rounded-md text-xs truncate" title={sender._id || "Unknown"}>
                                    {(sender._id || "Unknown").split('@')[0]}
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Section 2: Unified Calendar Schedule */}
                {Object.keys(groupedEvents).length === 0 ? (
                    <div className="text-gray-400 text-sm text-center mt-10">Your schedule is completely clear!</div>
                ) : (
                    Object.entries(groupedEvents).map(([dateLabel, dayEvents]) => (
                        <div key={dateLabel}>
                            <div className="flex items-center gap-2 mb-3 px-1">
                                <CalendarIcon className="w-4 h-4 text-blue-400" />
                                <h4 className="font-medium text-blue-100 text-sm tracking-wide uppercase">{dateLabel}</h4>
                            </div>

                            <div className="flex flex-col gap-3 relative border-l border-white/5 ml-3 pl-4">
                                {dayEvents.map((event) => {
                                    const startDate = new Date(event.start);
                                    const endDate = new Date(event.end);
                                    const now = nowRef.current;
                                    const isPast = endDate < now;
                                    const isNow = startDate <= now && endDate >= now;
                                    const eventStatus = getEventStatus(event);
                                    const isActioned = eventStatus !== 'pending';
                                    const statusCfg = STATUS_CONFIG[eventStatus];

                                    return (
                                        <div key={event.id} className={`p-4 rounded-xl border transition-all relative group ${
                                            isActioned
                                                ? eventStatus === 'done'
                                                    ? 'bg-emerald-500/5 border-emerald-500/20 opacity-60'
                                                    : eventStatus === 'cancelled'
                                                        ? 'bg-red-500/5 border-red-500/20 opacity-50'
                                                        : 'bg-amber-500/5 border-amber-500/20 opacity-60'
                                                : isPast ? 'bg-white/5 border-white/5 opacity-50'
                                                : isNow ? 'bg-nexus-primary/20 border-nexus-primary/50 shadow-[0_0_15px_rgba(177,158,239,0.1)]'
                                                : 'bg-nexus-primary/5 border-nexus-primary/20 hover:border-nexus-primary/40'
                                        }`}>
                                            {/* Timeline Node */}
                                            <div className={`absolute -left-[21px] top-5 w-2 h-2 rounded-full border-2 border-black ${
                                                isActioned
                                                    ? eventStatus === 'done' ? 'bg-emerald-400' : eventStatus === 'cancelled' ? 'bg-red-400' : 'bg-amber-400'
                                                    : isNow ? 'bg-nexus-primary' : 'bg-white/30 group-hover:bg-nexus-primary/70 transition-colors'
                                            }`}></div>

                                            <div className="flex items-start justify-between gap-2 mb-2">
                                                <h4 className={`font-medium ${
                                                    isActioned
                                                        ? eventStatus === 'cancelled' ? 'text-white/40 line-through' : 'text-white/60'
                                                        : isNow ? 'text-nexus-primary' : 'text-white/90'
                                                } line-clamp-2 leading-tight`}>{event.summary}</h4>
                                                {isActioned && statusCfg && (
                                                    <span className={`shrink-0 px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide ${statusCfg.color} ${statusCfg.bg}`}>
                                                        {statusCfg.label}
                                                    </span>
                                                )}
                                            </div>

                                            <div className="flex items-center gap-3 text-xs text-white/60 mb-2">
                                                <span className="flex items-center gap-1.5 font-mono">
                                                    <Clock className="w-3.5 h-3.5 opacity-70" />
                                                    {startDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} - {endDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                                </span>
                                                {isNow && !isActioned && (
                                                    <span className="text-nexus-primary bg-nexus-primary/10 px-1.5 py-0.5 rounded text-[10px] font-bold tracking-widest uppercase animate-pulse">Now</span>
                                                )}
                                            </div>

                                            {event.location && (
                                                <div className="flex items-center gap-2 text-xs text-white/50 truncate mt-2 bg-black/20 p-1.5 rounded w-max max-w-full">
                                                    <MapPin className="w-3.5 h-3.5 shrink-0" />
                                                    <span className="truncate">{event.location}</span>
                                                </div>
                                            )}

                                            {event.link && !isPast && !isActioned && (
                                                <a href={event.link} target="_blank" rel="noreferrer" className="mt-3 w-full py-2 bg-nexus-primary/10 hover:bg-nexus-primary text-nexus-primary hover:text-black font-medium text-sm rounded transition-colors flex items-center justify-center gap-1.5">
                                                    <Video className="w-4 h-4" /> Join Virtual Meeting
                                                </a>
                                            )}

                                            {/* Action Buttons */}
                                            {!isActioned && !isPast && (
                                                <div className="flex items-center gap-1.5 mt-3 pt-3 border-t border-white/5">
                                                    <button
                                                        onClick={() => handleEventStatusUpdate(event.id, 'done')}
                                                        className="flex items-center gap-1 text-emerald-400 hover:text-white transition-colors bg-emerald-500/10 hover:bg-emerald-500/20 px-2.5 py-1 rounded text-xs"
                                                        title="Mark as done"
                                                    >
                                                        <Check className="w-3 h-3" /> Done
                                                    </button>
                                                    <button
                                                        onClick={() => handleEventStatusUpdate(event.id, 'rescheduled')}
                                                        className="flex items-center gap-1 text-amber-400 hover:text-white transition-colors bg-amber-500/10 hover:bg-amber-500/20 px-2.5 py-1 rounded text-xs"
                                                        title="Reschedule"
                                                    >
                                                        <RefreshCw className="w-3 h-3" /> Reschedule
                                                    </button>
                                                    <button
                                                        onClick={() => handleEventStatusUpdate(event.id, 'cancelled')}
                                                        className="flex items-center gap-1 text-red-400 hover:text-white transition-colors bg-red-500/10 hover:bg-red-500/20 px-2.5 py-1 rounded text-xs"
                                                        title="Cancel meeting"
                                                    >
                                                        <X className="w-3 h-3" /> Cancel
                                                    </button>
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    ))
                )}
            </div>
            <div className="absolute bottom-0 w-full h-12 bg-gradient-to-t from-black/80 to-transparent pointer-events-none"></div>
        </div>
    );
}
