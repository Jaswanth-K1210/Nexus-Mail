import { useState, useEffect, useRef } from 'react';
import {
    Calendar as CalendarIcon, Clock, MapPin, Video, Loader2,
    Users, ChevronDown, ChevronUp, AlertCircle, Check, X, RefreshCw,
} from 'lucide-react';
import api from '../api';

interface Attendee {
    email: string;
    name: string;
    status: string;
    organizer: boolean;
}

export interface CalendarEvent {
    id: string;
    summary: string;
    start: string;
    end: string;
    location?: string;
    link?: string;
    description?: string;
    attendees?: Attendee[];
    organizer_email?: string;
    status?: string;
    local_status?: string;
}

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string; border: string }> = {
    done: { label: 'Done', color: 'text-emerald-400', bg: 'bg-emerald-500/15', border: 'border-emerald-500/20' },
    cancelled: { label: 'Cancelled', color: 'text-red-400', bg: 'bg-red-500/15', border: 'border-red-500/20' },
    rescheduled: { label: 'Rescheduled', color: 'text-amber-400', bg: 'bg-amber-500/15', border: 'border-amber-500/20' },
};

export function UpcomingMeetings({ embedded = false }: { embedded?: boolean } = {}) {
    const [events, setEvents] = useState<CalendarEvent[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);
    const [expandedId, setExpandedId] = useState<string | null>(null);
    const [localStatuses, setLocalStatuses] = useState<Record<string, string>>({});
    const nowRef = useRef(new Date());

    // Update "now" every 60s so NOW badges stay accurate
    useEffect(() => {
        const interval = setInterval(() => { nowRef.current = new Date(); }, 60000);
        return () => clearInterval(interval);
    }, []);

    const fetchEvents = async () => {
        try {
            setLoading(true);
            setError(false);
            const res = await api.get('/meetings/upcoming');
            setEvents(res.data.events || []);
            setLocalStatuses({});
        } catch (err) {
            console.error("Failed to fetch upcoming meetings", err);
            setError(true);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchEvents();
        const interval = setInterval(fetchEvents, 5 * 60000);
        return () => clearInterval(interval);
    }, []);

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

    const now = nowRef.current;
    const upcomingEvents = events.filter(e => new Date(e.end) >= now);

    const getStatusBadge = (status: string) => {
        switch (status) {
            case 'accepted': return 'bg-green-500/20 text-green-400';
            case 'declined': return 'bg-red-500/20 text-red-400';
            case 'tentative': return 'bg-amber-500/20 text-amber-400';
            default: return 'bg-white/10 text-white/60';
        }
    };

    // ─── Error state ───
    if (error && events.length === 0) {
        if (embedded) {
            return (
                <div className="flex flex-col items-center justify-center py-6 gap-2 opacity-50">
                    <AlertCircle className="w-5 h-5 text-nexus-textMuted" />
                    <p className="text-xs text-nexus-textMuted">Could not load calendar</p>
                </div>
            );
        }
        return (
            <div className="glass-panel p-6 flex flex-col items-center justify-center h-full w-full">
                <AlertCircle className="w-6 h-6 text-nexus-textMuted mb-3" />
                <p className="text-sm text-nexus-textMuted mb-1">Could not load calendar</p>
                <p className="text-xs text-nexus-textMuted/60 mb-4">Make sure Google Calendar is connected</p>
                <button onClick={fetchEvents} className="text-xs text-nexus-primary hover:underline">Retry</button>
            </div>
        );
    }

    // ─── Loading state ───
    if (loading && events.length === 0) {
        if (embedded) {
            return <div className="flex items-center justify-center py-6"><Loader2 className="w-5 h-5 animate-spin text-nexus-primary" /></div>;
        }
        return (
            <div className="glass-panel p-6 flex flex-col items-center justify-center h-full w-full">
                <Loader2 className="w-6 h-6 animate-spin text-nexus-primary" />
            </div>
        );
    }

    // ─── Embedded mode ───
    if (embedded) {
        return (
            <div className="flex flex-col gap-3">
                {upcomingEvents.length === 0 ? (
                    <div className="text-gray-400 text-sm text-center py-4">No upcoming events.</div>
                ) : (
                    <>
                        <h4 className="text-[10px] font-mono font-bold text-nexus-primary uppercase tracking-wider flex items-center gap-1.5">
                            <CalendarIcon className="w-3 h-3" /> Meetings ({upcomingEvents.length})
                        </h4>
                        {upcomingEvents.slice(0, 6).map(event => {
                            const startDate = new Date(event.start);
                            const endDate = new Date(event.end);
                            const isNow = startDate <= now && endDate >= now;
                            const eventStatus = getEventStatus(event);
                            const isActioned = eventStatus !== 'pending';
                            const statusCfg = STATUS_CONFIG[eventStatus];

                            return (
                                <div key={event.id} className={`p-3 rounded-lg border text-xs ${
                                    isActioned
                                        ? `${statusCfg?.bg || 'bg-white/5'} ${statusCfg?.border || 'border-white/10'} opacity-60`
                                        : isNow ? 'bg-nexus-primary/15 border-nexus-primary/40' : 'bg-nexus-primary/5 border-nexus-primary/15'
                                }`}>
                                    <div className="flex items-start justify-between gap-1">
                                        <p className={`font-medium line-clamp-1 ${
                                            isActioned
                                                ? eventStatus === 'cancelled' ? 'text-white/40 line-through' : 'text-white/60'
                                                : isNow ? 'text-nexus-primary' : 'text-white/90'
                                        }`}>{event.summary}</p>
                                        {isActioned && statusCfg && (
                                            <span className={`shrink-0 px-1.5 py-0.5 rounded text-[9px] font-semibold uppercase tracking-wide ${statusCfg.color} ${statusCfg.bg}`}>
                                                {statusCfg.label}
                                            </span>
                                        )}
                                    </div>
                                    <p className="text-white/50 mt-1 flex items-center gap-1">
                                        <Clock className="w-3 h-3" />
                                        {startDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} - {endDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                        {isNow && !isActioned && <span className="ml-1 text-[9px] px-1 py-0.5 rounded bg-nexus-primary/30 text-nexus-primary font-semibold animate-pulse">NOW</span>}
                                    </p>
                                    {event.link && !isActioned && (
                                        <a href={event.link} target="_blank" rel="noreferrer" className="mt-1.5 text-blue-400 hover:underline flex items-center gap-1"><Video className="w-3 h-3" /> Join</a>
                                    )}
                                    {!isActioned && (
                                        <div className="flex items-center gap-1 mt-2 pt-2 border-t border-white/5">
                                            <button onClick={() => handleEventStatusUpdate(event.id, 'done')} className="flex items-center gap-0.5 text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 px-1.5 py-0.5 rounded text-[10px] transition-colors">
                                                <Check className="w-2.5 h-2.5" /> Done
                                            </button>
                                            <button onClick={() => handleEventStatusUpdate(event.id, 'rescheduled')} className="flex items-center gap-0.5 text-amber-400 bg-amber-500/10 hover:bg-amber-500/20 px-1.5 py-0.5 rounded text-[10px] transition-colors">
                                                <RefreshCw className="w-2.5 h-2.5" /> Reschedule
                                            </button>
                                            <button onClick={() => handleEventStatusUpdate(event.id, 'cancelled')} className="flex items-center gap-0.5 text-red-400 bg-red-500/10 hover:bg-red-500/20 px-1.5 py-0.5 rounded text-[10px] transition-colors">
                                                <X className="w-2.5 h-2.5" /> Cancel
                                            </button>
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </>
                )}
            </div>
        );
    }

    // ─── Full standalone view ───
    return (
        <div className="glass-panel w-full h-full flex flex-col overflow-hidden relative shadow-[0_0_15px_rgba(177,158,239,0.05)] border-nexus-primary/10">
            <div className="p-4 border-b border-white/10 flex items-center justify-between sticky top-0 bg-black/40 backdrop-blur-xl z-10">
                <h3 className="font-semibold text-white/90 flex items-center gap-2">
                    <CalendarIcon className="w-4 h-4 text-nexus-primary" />
                    Today's Schedule
                </h3>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-nexus-primary/15 text-nexus-primary">
                    {upcomingEvents.length}
                </span>
            </div>

            <div className="p-4 overflow-y-auto custom-scrollbar flex flex-col gap-3 flex-1 pb-20">
                {upcomingEvents.length === 0 ? (
                    <div className="flex flex-col items-center justify-center flex-1 gap-2 opacity-40 py-10">
                        <CalendarIcon className="w-8 h-8 text-nexus-primary" />
                        <p className="text-sm text-nexus-textMuted">No upcoming events</p>
                    </div>
                ) : (
                    upcomingEvents.map((event) => {
                        const startDate = new Date(event.start);
                        const endDate = new Date(event.end);
                        const isNow = startDate <= now && endDate >= now;
                        const isExpanded = expandedId === event.id;
                        const attendees = event.attendees || [];
                        const eventStatus = getEventStatus(event);
                        const isActioned = eventStatus !== 'pending';
                        const statusCfg = STATUS_CONFIG[eventStatus];

                        return (
                            <div
                                key={event.id}
                                className={`rounded-xl border transition-all ${
                                    isActioned
                                        ? eventStatus === 'done'
                                            ? 'bg-emerald-500/5 border-emerald-500/20 opacity-60'
                                            : eventStatus === 'cancelled'
                                                ? 'bg-red-500/5 border-red-500/20 opacity-50'
                                                : 'bg-amber-500/5 border-amber-500/20 opacity-60'
                                        : isNow
                                            ? 'bg-nexus-primary/20 border-nexus-primary/50 shadow-[0_0_15px_rgba(177,158,239,0.1)]'
                                            : 'bg-nexus-primary/5 border-nexus-primary/20 hover:border-nexus-primary/40'
                                }`}
                            >
                                {/* Main event row */}
                                <div
                                    className="p-4 cursor-pointer"
                                    onClick={() => setExpandedId(isExpanded ? null : event.id)}
                                >
                                    <div className="flex items-start justify-between gap-2">
                                        <h4 className={`font-medium ${
                                            isActioned
                                                ? eventStatus === 'cancelled' ? 'text-white/40 line-through' : 'text-white/60'
                                                : isNow ? 'text-nexus-primary' : 'text-white/90'
                                        } line-clamp-2 text-sm`}>
                                            {event.summary}
                                        </h4>
                                        <div className="flex items-center gap-1.5 shrink-0">
                                            {isActioned && statusCfg && (
                                                <span className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide ${statusCfg.color} ${statusCfg.bg}`}>
                                                    {statusCfg.label}
                                                </span>
                                            )}
                                            {isExpanded
                                                ? <ChevronUp className="w-4 h-4 text-nexus-textMuted mt-0.5" />
                                                : <ChevronDown className="w-4 h-4 text-nexus-textMuted mt-0.5" />
                                            }
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2 text-xs text-white/60 mt-2">
                                        <Clock className="w-3.5 h-3.5" />
                                        {startDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} - {endDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                        {isNow && !isActioned && (
                                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-nexus-primary/30 text-nexus-primary font-semibold uppercase tracking-wider animate-pulse">
                                                Now
                                            </span>
                                        )}
                                    </div>
                                    {event.location && (
                                        <div className="flex items-center gap-2 text-xs text-white/50 mt-1.5 truncate">
                                            <MapPin className="w-3.5 h-3.5 flex-shrink-0" />
                                            {event.location}
                                        </div>
                                    )}

                                    {/* Action Buttons — inline in main row */}
                                    {!isActioned && (
                                        <div className="flex items-center gap-1.5 mt-3 pt-3 border-t border-white/5">
                                            <button
                                                onClick={(e) => { e.stopPropagation(); handleEventStatusUpdate(event.id, 'done'); }}
                                                className="flex items-center gap-1 text-emerald-400 hover:text-white transition-colors bg-emerald-500/10 hover:bg-emerald-500/20 px-2.5 py-1 rounded text-xs"
                                            >
                                                <Check className="w-3 h-3" /> Done
                                            </button>
                                            <button
                                                onClick={(e) => { e.stopPropagation(); handleEventStatusUpdate(event.id, 'rescheduled'); }}
                                                className="flex items-center gap-1 text-amber-400 hover:text-white transition-colors bg-amber-500/10 hover:bg-amber-500/20 px-2.5 py-1 rounded text-xs"
                                            >
                                                <RefreshCw className="w-3 h-3" /> Reschedule
                                            </button>
                                            <button
                                                onClick={(e) => { e.stopPropagation(); handleEventStatusUpdate(event.id, 'cancelled'); }}
                                                className="flex items-center gap-1 text-red-400 hover:text-white transition-colors bg-red-500/10 hover:bg-red-500/20 px-2.5 py-1 rounded text-xs"
                                            >
                                                <X className="w-3 h-3" /> Cancel
                                            </button>
                                        </div>
                                    )}
                                </div>

                                {/* Expanded detail view */}
                                {isExpanded && (
                                    <div className="border-t border-white/10 p-4 flex flex-col gap-3">
                                        {/* Description */}
                                        {event.description && (
                                            <div className="text-xs text-white/60 leading-relaxed whitespace-pre-wrap line-clamp-4">
                                                {event.description.replace(/<[^>]*>/g, '').slice(0, 300)}
                                            </div>
                                        )}

                                        {/* Participants */}
                                        {attendees.length > 0 && (
                                            <div>
                                                <h5 className="text-[10px] font-mono font-bold text-nexus-textMuted uppercase tracking-wider mb-2 flex items-center gap-1.5">
                                                    <Users className="w-3 h-3" />
                                                    Participants ({attendees.length})
                                                </h5>
                                                <div className="flex flex-col gap-1.5 max-h-28 overflow-y-auto custom-scrollbar">
                                                    {attendees.map((a, i) => (
                                                        <div key={i} className="flex items-center justify-between text-xs">
                                                            <span className="text-white/80 truncate flex-1">
                                                                {a.name || a.email}
                                                                {a.organizer && (
                                                                    <span className="ml-1.5 text-[9px] px-1 py-0.5 rounded bg-nexus-primary/20 text-nexus-primary">
                                                                        Organizer
                                                                    </span>
                                                                )}
                                                            </span>
                                                            <span className={`text-[9px] px-1.5 py-0.5 rounded font-semibold capitalize ${getStatusBadge(a.status)}`}>
                                                                {a.status === 'needsAction' ? 'Pending' : a.status}
                                                            </span>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        {/* Join link */}
                                        {event.link && !isActioned && (
                                            <a
                                                href={event.link}
                                                target="_blank"
                                                rel="noreferrer"
                                                className="w-full px-3 py-2 bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 text-xs font-medium rounded-lg transition-colors flex items-center justify-center gap-1.5"
                                            >
                                                <Video className="w-3.5 h-3.5" /> Join Meeting
                                            </a>
                                        )}
                                    </div>
                                )}
                            </div>
                        );
                    })
                )}
            </div>
            <div className="absolute bottom-0 w-full h-12 bg-gradient-to-t from-black/80 to-transparent pointer-events-none" />
        </div>
    );
}
