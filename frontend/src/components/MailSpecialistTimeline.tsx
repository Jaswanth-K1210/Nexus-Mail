import { useState, useEffect } from 'react';
import { Calendar as CalendarIcon, Clock, MapPin, Video, Loader2, Target, ChevronRight, Briefcase } from 'lucide-react';
import api from '../api';

export interface CalendarEvent {
    id: string;
    summary: string;
    start: string;
    end: string;
    location?: string;
    link?: string;
}

export interface ActionItem {
    id: string;
    type: string;
    text: string;
    source_sender: string;
    source_subject: string;
    received_at: string;
    source_quote?: string;
}

export function MailSpecialistTimeline() {
    const [events, setEvents] = useState<CalendarEvent[]>([]);
    const [actions, setActions] = useState<ActionItem[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchData = async () => {
        try {
            setLoading(true);
            const res = await api.get('/assistant/timeline');
            setEvents(res.data.calendar_events || []);
            setActions(res.data.action_items || []);
        } catch (error) {
            console.error("Failed to fetch specialist timeline", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 5 * 60000);
        return () => clearInterval(interval);
    }, []);

    if (loading && events.length === 0 && actions.length === 0) {
        return (
            <div className="glass-panel p-6 flex flex-col items-center justify-center h-full w-full xl:w-[400px]">
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

    return (
        <div className="glass-panel w-full xl:w-[450px] h-full flex flex-col overflow-hidden relative shadow-[0_0_15px_rgba(177,158,239,0.05)] border-nexus-primary/10">
            <div className="p-4 border-b border-white/10 flex items-center justify-between sticky top-0 bg-black/40 backdrop-blur-xl z-10">
                <h3 className="font-semibold text-white/90 flex items-center gap-2">
                    <Briefcase className="w-4 h-4 text-nexus-primary" />
                    Mail Specialist Timeline
                </h3>
            </div>

            <div className="p-4 overflow-y-auto custom-scrollbar flex flex-col gap-6 flex-1 pb-20">

                {/* Section 1: Deadlines and Action Items */}
                {actions.length > 0 && (
                    <div className="mb-2">
                        <div className="flex items-center gap-2 mb-3 px-1">
                            <Target className="w-4 h-4 text-rose-400" />
                            <h4 className="font-medium text-white/80 text-sm tracking-wide uppercase">Extracted Action Items</h4>
                        </div>
                        <div className="flex flex-col gap-2">
                            {actions.slice(0, 5).map((action, i) => (
                                <div key={i} className="bg-gradient-to-r from-red-500/5 to-transparent border-l-2 border-rose-500/50 p-3 rounded-r-lg group relative">
                                    <p className="text-sm text-white/90 leading-relaxed mb-2">{action.text}</p>

                                    {/* Institutional Citation Engine (RAG) */}
                                    {action.source_quote && (
                                        <div className="mb-3 px-3 py-2 bg-black/40 border border-white/5 shadow-inner rounded text-xs text-white/50 italic italic relative overflow-hidden">
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
                                        <button className="text-rose-400 hover:text-white transition-colors bg-rose-500/10 hover:bg-rose-500/20 px-2 py-0.5 rounded text-xs">
                                            Resolve
                                        </button>
                                    </div>
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
                                    const isPast = endDate < new Date();
                                    const isNow = startDate <= new Date() && endDate >= new Date();

                                    return (
                                        <div key={event.id} className={`p-4 rounded-xl border transition-all relative group ${isPast ? 'bg-white/5 border-white/5 opacity-50' :
                                            isNow ? 'bg-nexus-primary/20 border-nexus-primary/50 shadow-[0_0_15px_rgba(177,158,239,0.1)]' :
                                                'bg-nexus-primary/5 border-nexus-primary/20 hover:border-nexus-primary/40'
                                            }`}>
                                            {/* Timeline Node */}
                                            <div className={`absolute -left-[21px] top-5 w-2 h-2 rounded-full border-2 border-black ${isNow ? 'bg-nexus-primary' : 'bg-white/30 group-hover:bg-nexus-primary/70 transition-colors'
                                                }`}></div>

                                            <h4 className={`font-medium mb-2 ${isNow ? 'text-nexus-primary' : 'text-white/90'} line-clamp-2 leading-tight`}>{event.summary}</h4>

                                            <div className="flex items-center gap-3 text-xs text-white/60 mb-2">
                                                <span className="flex items-center gap-1.5 font-mono">
                                                    <Clock className="w-3.5 h-3.5 opacity-70" />
                                                    {startDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} - {endDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                                </span>
                                                {isNow && (
                                                    <span className="text-nexus-primary bg-nexus-primary/10 px-1.5 py-0.5 rounded text-[10px] font-bold tracking-widest uppercase animate-pulse">Now</span>
                                                )}
                                            </div>

                                            {event.location && (
                                                <div className="flex items-center gap-2 text-xs text-white/50 truncate mt-2 bg-black/20 p-1.5 rounded w-max max-w-full">
                                                    <MapPin className="w-3.5 h-3.5 shrink-0" />
                                                    <span className="truncate">{event.location}</span>
                                                </div>
                                            )}

                                            {event.link && !isPast && (
                                                <a href={event.link} target="_blank" rel="noreferrer" className="mt-3 w-full py-2 bg-nexus-primary/10 hover:bg-nexus-primary text-nexus-primary hover:text-black font-medium text-sm rounded transition-colors flex items-center justify-center gap-1.5">
                                                    <Video className="w-4 h-4" /> Join Virtual Meeting
                                                </a>
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
