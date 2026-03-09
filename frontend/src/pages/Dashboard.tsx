import { useEffect, useState } from 'react';
import { Mail, CheckCircle2, TrendingUp } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { SplitInbox } from '../components/SplitInbox';
import { AnalyticsDashboard } from '../components/AnalyticsDashboard';
import { MeetingAlerts } from '../components/MeetingAlerts';
import { MailSpecialistTimeline } from '../components/MailSpecialistTimeline';
import type { EmailThread } from '../components/MailThreadCard';

export default function Dashboard() {
    const navigate = useNavigate();
    const [profile, setProfile] = useState<{ unread: number, pendingDrafts: number, avgScore: number } | null>(null);
    const [loading, setLoading] = useState(true);
    const [syncing, setSyncing] = useState(false);
    const [inbox, setInbox] = useState<EmailThread[]>([]);

    async function fetchDashboardData() {
        try {
            const token = localStorage.getItem('nexus_token');
            if (!token) {
                navigate('/');
                return;
            }

            // Verify Auth
            await api.get('/auth/consent-status');

            // Fire concurrent calls for speed
            const [emailsRes, draftsRes] = await Promise.all([
                api.get('/gmail/emails'),
                api.get('/drafts')
            ]);

            const drafts = draftsRes.data.drafts || [];
            const draftMap = new Map();
            drafts.forEach((d: { email_id: string, ai_confidence: number }) => draftMap.set(d.email_id, d));

            const mappedEmails: EmailThread[] = (emailsRes.data.emails || []).map((e: { _id: string, sender_name?: string, sender_email?: string, subject?: string, snippet?: string, is_read?: boolean, priority_score?: number, category?: string }) => ({
                id: e._id,
                sender: e.sender_name || e.sender_email || "Unknown Sender",
                subject: e.subject || "No Subject",
                snippet: e.snippet || "",
                isUnread: e.is_read === false,
                priorityScore: e.priority_score ?? 50,
                category: e.category || "General",
                hasAiDraft: !!draftMap.has(e._id),
                aiConfidence: draftMap.has(e._id) ? Math.round(draftMap.get(e._id).ai_confidence * 100) : undefined
            }));

            setInbox(mappedEmails);

            const avgScore = mappedEmails.length ? Math.round(mappedEmails.reduce((acc, i) => acc + i.priorityScore, 0) / mappedEmails.length) : 0;

            setProfile({
                unread: mappedEmails.filter(m => m.isUnread).length,
                pendingDrafts: drafts.length,
                avgScore: avgScore
            });

        } catch (err) {
            console.error(err);
            localStorage.removeItem('nexus_token');
            navigate('/');
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        fetchDashboardData();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [navigate]);

    const handleSync = async () => {
        try {
            setSyncing(true);
            await api.post('/gmail/sync');
            // Trigger the AI processing pipeline for the newly synced emails
            await api.post('/gmail/process');
            setTimeout(fetchDashboardData, 1500);
        } catch (err) {
            console.error("Sync failed", err);
            alert("Sync failed. You might need to reconnect your Google account.");
        } finally {
            setSyncing(false);
        }
    };

    if (loading) {
        return <div className="min-h-screen bg-nexus-bg flex items-center justify-center text-white">Loading Dashboard...</div>
    }

    return (
        <div className="min-h-screen bg-nexus-bg text-white p-8 flex flex-col font-sans">

            <header className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-3xl font-bold bg-gradient-to-r from-nexus-primary to-blue-400 bg-clip-text text-transparent">Nexus Dashboard</h1>
                    <p className="text-gray-400 text-sm mt-1">Backend Connection Established</p>
                </div>

                <div className="flex items-center gap-4">
                    <button
                        onClick={handleSync}
                        disabled={syncing}
                        className={`glass-button text-xs py-2 px-4 flex items-center gap-2 ${syncing ? 'opacity-50' : 'hover:bg-white/10'}`}
                    >
                        {syncing ? 'Syncing...' : 'Force Sync'}
                    </button>
                    <div className="glass-panel px-4 py-2 flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                        <span className="text-sm font-medium">System Online</span>
                    </div>
                    <button
                        className="glass-button text-xs py-2 px-4"
                        onClick={() => {
                            localStorage.removeItem('nexus_token');
                            navigate('/');
                        }}
                    >
                        Logout
                    </button>
                </div>
            </header>

            {/* Top Stat Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div className="glass-panel p-6">
                    <div className="flex items-center justify-between mb-2">
                        <h3 className="text-gray-400 font-medium">Total Unread</h3>
                        <Mail className="text-nexus-primary w-5 h-5" />
                    </div>
                    <p className="text-4xl font-bold">{profile?.unread || 0}</p>
                </div>
                <div className="glass-panel p-6 border-nexus-primary/30 relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-16 h-16 bg-nexus-primary/10 blur-xl rounded-full"></div>
                    <div className="flex items-center justify-between mb-2 relative">
                        <h3 className="text-nexus-primary font-medium">Pending AI Drafts</h3>
                        <CheckCircle2 className="text-nexus-primary w-5 h-5" />
                    </div>
                    <p className="text-4xl font-bold relative">{profile?.pendingDrafts || 0}</p>
                </div>
                <div className="glass-panel p-6">
                    <div className="flex items-center justify-between mb-2">
                        <h3 className="text-gray-400 font-medium">Priority Score Avg</h3>
                        <TrendingUp className="text-blue-400 w-5 h-5" />
                    </div>
                    <p className="text-4xl font-bold">{profile?.avgScore || 0}<span className="text-xl text-gray-500 font-medium"> / 100</span></p>
                </div>
            </div>

            {/* Main UI Area */}
            <div className="w-full flex flex-col gap-8 mb-12">

                {/* Pending Calendar Approvals */}
                <MeetingAlerts />

                <div className="w-full h-[600px] xl:h-[750px] flex flex-col xl:flex-row gap-6">
                    {inbox.length === 0 ? (
                        <div className="glass-panel h-full flex-1 flex flex-col items-center justify-center text-gray-400">
                            <Mail className="w-12 h-12 mb-4 opacity-20" />
                            <p>No emails found in the database.</p>
                            <p className="text-sm opacity-60 mt-2">Click "Force Sync" to fetch your recent emails.</p>
                        </div>
                    ) : (
                        <SplitInbox inbox={inbox} />
                    )}

                    {/* The Mail Specialist Timeline Widget */}
                    <MailSpecialistTimeline />
                </div>

                {/* Analytics */}
                <AnalyticsDashboard />
            </div>

        </div>
    );
}
