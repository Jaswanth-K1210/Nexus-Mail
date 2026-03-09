import { useState, useEffect } from 'react';
import { Calendar, Check, X, Clock, Loader2 } from 'lucide-react';
import api from '../api';

export interface MeetingAlert {
    id: string; // the database _id or alert_id
    email_id: string;
    sender: string;
    proposed_time: string; // ISO datetime string
    status: 'pending' | 'accepted' | 'declined' | 'suggested_new_time' | 'dismissed';
}

export function MeetingAlerts() {
    const [alerts, setAlerts] = useState<MeetingAlert[]>([]);
    const [loading, setLoading] = useState(true);
    const [actionLoading, setActionLoading] = useState<string | null>(null);

    const fetchAlerts = async () => {
        try {
            setLoading(true);
            const res = await api.get('/meetings/pending');
            const data = res.data.alerts.map((a: any) => ({
                id: a.id || a._id,
                email_id: a.email_id,
                sender: a.sender || 'Unknown Sender',
                proposed_time: a.proposed_time,
                status: a.status
            }));
            setAlerts(data);
        } catch (error) {
            console.error("Failed to fetch meetings", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAlerts();

        // Listen for generic sync events to refetch
        const interval = setInterval(fetchAlerts, 60000);
        return () => clearInterval(interval);
    }, []);

    const handleAction = async (alertId: string, action: 'accept' | 'decline' | 'dismiss') => {
        try {
            setActionLoading(alertId);
            await api.post(`/meetings/${alertId}/${action}`);

            // Remove from list optimistically or refetch
            setAlerts(prev => prev.filter(a => a.id !== alertId));
        } catch (error) {
            console.error(`Failed to ${action} meeting`, error);
        } finally {
            setActionLoading(null);
        }
    };

    if (loading && alerts.length === 0) {
        return (
            <div className="glass-panel p-6 flex flex-col items-center justify-center min-h-[150px]">
                <Loader2 className="w-6 h-6 animate-spin text-nexus-primary" />
            </div>
        );
    }

    if (alerts.length === 0) {
        return null; // hide if no pending meetings
    }

    return (
        <div className="flex flex-col gap-4">
            <h3 className="text-xl font-semibold text-white/90 flex items-center gap-2">
                <Calendar className="w-5 h-5 text-nexus-primary" />
                Pending Meeting Approvals
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {alerts.map(alert => (
                    <div key={alert.id} className="glass-panel p-4 flex flex-col justify-between border-blue-400/20 shadow-[0_0_15px_rgba(96,165,250,0.05)] relative overflow-hidden">
                        <div className="absolute top-0 right-0 w-24 h-24 bg-blue-400/10 blur-2xl rounded-full pointer-events-none"></div>

                        <div>
                            <div className="flex items-start justify-between mb-2">
                                <h4 className="font-medium text-white max-w-[80%] truncate">{alert.sender}</h4>
                                <span className="text-xs font-mono bg-blue-500/20 text-blue-400 px-2 py-1 rounded">Proposal</span>
                            </div>

                            <p className="text-sm text-white/60 mb-4 flex items-center gap-2">
                                <Clock className="w-4 h-4 opacity-50" />
                                {new Date(alert.proposed_time).toLocaleString(undefined, {
                                    weekday: 'short', month: 'short', day: 'numeric',
                                    hour: 'numeric', minute: '2-digit'
                                })}
                            </p>
                        </div>

                        <div className="flex items-center gap-2 mt-2">
                            <button
                                disabled={actionLoading === alert.id}
                                onClick={() => handleAction(alert.id, 'accept')}
                                className="flex-1 py-2 px-3 bg-nexus-primary/20 hover:bg-nexus-primary/30 text-nexus-primary text-sm font-medium rounded-lg transition-colors flex items-center justify-center gap-1"
                            >
                                <Check className="w-4 h-4" /> Accept
                            </button>
                            <button
                                disabled={actionLoading === alert.id}
                                onClick={() => handleAction(alert.id, 'decline')}
                                className="flex-1 py-2 px-3 bg-red-500/10 hover:bg-red-500/20 text-red-400 text-sm font-medium rounded-lg transition-colors flex items-center justify-center gap-1"
                            >
                                <X className="w-4 h-4" /> Decline
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
