import { useState, useEffect } from 'react';
import { Calendar as CalendarIcon, Clock, MapPin, Video, Loader2 } from 'lucide-react';
import api from '../api';

export interface CalendarEvent {
    id: string;
    summary: string;
    start: string;
    end: string;
    location?: string;
    link?: string;
}

export function UpcomingMeetings() {
    const [events, setEvents] = useState<CalendarEvent[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchEvents = async () => {
        try {
            setLoading(true);
            const res = await api.get('/meetings/upcoming');
            setEvents(res.data.events);
        } catch (error) {
            console.error("Failed to fetch upcoming meetings", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchEvents();
        const interval = setInterval(fetchEvents, 5 * 60000); // 5 mins refresh calendar
        return () => clearInterval(interval);
    }, []);

    if (loading && events.length === 0) {
        return (
            <div className="glass-panel p-6 flex flex-col items-center justify-center h-full w-full xl:w-[350px]">
                <Loader2 className="w-6 h-6 animate-spin text-nexus-primary" />
            </div>
        );
    }

    return (
        <div className="glass-panel w-full xl:w-[350px] h-full flex flex-col overflow-hidden relative shadow-[0_0_15px_rgba(177,158,239,0.05)] border-nexus-primary/10">
            <div className="p-4 border-b border-white/10 flex items-center justify-between sticky top-0 bg-black/40 backdrop-blur-xl z-10">
                <h3 className="font-semibold text-white/90 flex items-center gap-2">
                    <CalendarIcon className="w-4 h-4 text-nexus-primary" />
                    Today's Schedule
                </h3>
            </div>

            <div className="p-4 overflow-y-auto custom-scrollbar flex flex-col gap-3 flex-1 pb-20">
                {events.length === 0 ? (
                    <div className="text-gray-400 text-sm text-center mt-10">No upcoming events found.</div>
                ) : (
                    events.map((event) => {
                        const startDate = new Date(event.start);
                        const endDate = new Date(event.end);
                        const isPast = endDate < new Date();
                        const isNow = startDate <= new Date() && endDate >= new Date();

                        return (
                            <div key={event.id} className={`p-4 rounded-xl border transition-all ${isPast ? 'bg-white/5 border-white/5 opacity-50' :
                                    isNow ? 'bg-nexus-primary/20 border-nexus-primary/50 shadow-[0_0_15px_rgba(177,158,239,0.1)]' :
                                        'bg-nexus-primary/5 border-nexus-primary/20 hover:border-nexus-primary/40'
                                }`}>
                                <h4 className={`font-medium mb-2 ${isNow ? 'text-nexus-primary' : 'text-white/90'} line-clamp-2`}>{event.summary}</h4>
                                <div className="flex items-center gap-2 text-xs text-white/60 mb-2">
                                    <Clock className="w-3.5 h-3.5" />
                                    {startDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} - {endDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                </div>
                                {event.location && (
                                    <div className="flex items-center gap-2 text-xs text-white/50 truncate">
                                        <MapPin className="w-3.5 h-3.5" />
                                        {event.location}
                                    </div>
                                )}
                                {event.link && !isPast && (
                                    <a href={event.link} target="_blank" rel="noreferrer" className="mt-3 w-max px-3 py-1.5 bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 text-xs font-medium rounded transition-colors flex items-center justify-center gap-1">
                                        <Video className="w-3.5 h-3.5" /> Join
                                    </a>
                                )}
                            </div>
                        );
                    })
                )}
            </div>
            <div className="absolute bottom-0 w-full h-12 bg-gradient-to-t from-black/80 to-transparent pointer-events-none"></div>
        </div>
    );
}
