import { useEffect, useState } from 'react';
import { Clock, Calendar, CheckSquare, Brain, Home, Inbox, Sparkles, Mail, TrendingUp, Shield } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import api from '../api';
import { SplitInbox } from '../components/SplitInbox';
import { AnalyticsDashboard } from '../components/AnalyticsDashboard';
import { MeetingAlerts } from '../components/MeetingAlerts';
import { UpcomingMeetings } from '../components/UpcomingMeetings';
import { MailSpecialistTimeline } from '../components/MailSpecialistTimeline';
import type { EmailThread } from '../components/MailThreadCard';
import { CommandPalette } from '../components/CommandPalette';
import { UserDropdown } from '../components/UserDropdown';

type Tab = 'home' | 'important' | 'all' | 'calendar';

export default function Dashboard() {
    const navigate = useNavigate();
    const [profile, setProfile] = useState<{ actionItems: number, timeSaved: number, meetingsToday: number } | null>(null);
    const [loading, setLoading] = useState(true);
    const [syncing, setSyncing] = useState(false);
    const [inbox, setInbox] = useState<EmailThread[]>([]);
    const [activeTab, setActiveTab] = useState<Tab>('home');

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

            const mappedEmails: EmailThread[] = (emailsRes.data.emails || []).map((e: any) => {
                const draft = draftMap.get(e._id);
                return {
                    id: e._id,
                    sender: e.sender_name || e.sender_email || "Unknown Sender",
                    subject: e.subject || "No Subject",
                    snippet: e.snippet || "",
                    isUnread: e.is_read === false,
                    priorityScore: e.priority_score ?? 50,
                    category: e.category || "General",
                    suggestedAction: e.suggested_action || "REVIEW ONLY",
                    hasAiDraft: !!draft,
                    aiConfidence: draft ? Math.round(draft.ai_confidence * 100) : undefined,
                    riskFlags: e.risk_flags || []
                };
            });

            setInbox(mappedEmails);

            // Calculate pending action items instantly from loaded emails
            const actionCount = (emailsRes.data.emails || []).reduce((acc: number, e: any) => acc + (e.action_items ? e.action_items.length : 0), 0);

            setProfile({
                actionItems: actionCount,
                meetingsToday: 0,
                // Estimated 2.5 min saved per AI draft (based on average email composition time)
                timeSaved: Math.round(drafts.length * 2.5)
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
    }, [navigate]);

    const handleSync = async () => {
        try {
            setSyncing(true);
            await api.post('/gmail/sync');
            await api.post('/gmail/process');
            await fetchDashboardData();
        } catch (err) {
            console.error("Sync failed", err);
            toast.error("Sync failed. You might need to reconnect your Google account.");
        } finally {
            setSyncing(false);
        }
    };

    const handleCommand = (actionId: string) => {
        switch (actionId) {
            case 'sync': handleSync(); break;
            case 'logout': localStorage.removeItem('nexus_token'); navigate('/'); break;
            case 'compose': toast("Compose feature coming soon!"); break;
            case 'search': toast("Search functionality coming soon!"); break;
            case 'settings': navigate('/profile'); break;
            default: break;
        }
    };

    if (loading) {
        return <div className="min-h-screen bg-nexus-bg flex items-center justify-center text-white">Loading Dashboard...</div>
    }

    // ─── Derived stats ───
    const NON_IMPORTANT_CATS = ['promotional', 'newsletter', 'marketing', 'social', 'transactional', 'spam', 'noreply', 'automated'];
    const importantEmails = inbox.filter(e => !NON_IMPORTANT_CATS.includes((e.category || '').toLowerCase()) && e.priorityScore >= 35);
    const riskCount = inbox.filter(e => e.riskFlags && e.riskFlags.length > 0).length;

    // ─── Tab config ───
    const tabs: { id: Tab; label: string; icon: React.ComponentType<{ className?: string }>; accent: string; activeAccent: string }[] = [
        { id: 'home', label: 'Home', icon: Home, accent: 'text-nexus-textMuted hover:text-nexus-text hover:bg-white/5', activeAccent: 'bg-nexus-primary/20 text-nexus-primary' },
        { id: 'important', label: 'Important', icon: Sparkles, accent: 'text-nexus-textMuted hover:text-nexus-text hover:bg-white/5', activeAccent: 'bg-rose-500/20 text-rose-400' },
        { id: 'all', label: 'All Mail', icon: Inbox, accent: 'text-nexus-textMuted hover:text-nexus-text hover:bg-white/5', activeAccent: 'bg-blue-500/20 text-blue-400' },
        { id: 'calendar', label: 'Calendar & Meetings', icon: Calendar, accent: 'text-nexus-textMuted hover:text-nexus-text hover:bg-white/5', activeAccent: 'bg-emerald-500/20 text-emerald-400' },
    ];

    return (
        <div className="min-h-screen bg-nexus-bg text-nexus-text p-8 flex flex-col">
                <CommandPalette onAction={handleCommand} />

                <header className="flex justify-between items-center mb-8">
                    {/* Left: Branding + Tabs */}
                    <div className="flex items-center gap-8">
                        <div>
                            <h1 className="text-3xl font-bold bg-gradient-to-r from-nexus-primary to-blue-400 bg-clip-text text-transparent">Nexus Workspace</h1>
                            <p className="text-nexus-textMuted text-sm mt-1">Autonomous Email Intelligence</p>
                        </div>

                        {/* Unified tab bar: Home | Important | All | Calendar */}
                        <div className="flex items-center gap-1 bg-white/5 rounded-full p-1">
                            {tabs.map(tab => {
                                const Icon = tab.icon;
                                const isActive = activeTab === tab.id;
                                return (
                                    <button
                                        key={tab.id}
                                        onClick={() => setActiveTab(tab.id)}
                                        className={`px-4 py-2 rounded-full text-sm font-medium transition-all flex items-center gap-1.5 ${
                                            isActive ? tab.activeAccent : tab.accent
                                        }`}
                                    >
                                        <Icon className="w-3.5 h-3.5" />
                                        {tab.label}
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    {/* Right: Status + User */}
                    <div className="flex items-center gap-4">
                        <div className="glass-panel px-4 py-2 flex items-center gap-2 border-green-500/20">
                            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse shadow-[0_0_10px_rgba(34,197,94,0.6)]"></span>
                            <span className="text-sm font-medium text-nexus-text">System Active</span>
                        </div>
                        <UserDropdown onSync={handleSync} syncing={syncing} />
                    </div>
                </header>

                {/* ═══════════════════════════════════════════════════════════
                    HOME TAB — first thing user sees after login
                ═══════════════════════════════════════════════════════════ */}
                {activeTab === 'home' && (
                    <div className="w-full flex flex-col gap-6 mb-12">

                        {/* Greeting + Quick Stats Row */}
                        <div className="flex items-end justify-between">
                            <div>
                                <h2 className="text-2xl font-bold text-nexus-text">
                                    {new Date().getHours() < 12 ? 'Good morning' : new Date().getHours() < 17 ? 'Good afternoon' : 'Good evening'} 👋
                                </h2>
                                <p className="text-sm text-nexus-textMuted mt-0.5">Here's what needs your attention today.</p>
                            </div>
                            <div className="flex items-center gap-3">
                                <div className="glass-panel px-3 py-1.5 flex items-center gap-2 text-xs">
                                    <Mail className="w-3.5 h-3.5 text-nexus-textMuted" />
                                    <span className="text-nexus-textMuted">{inbox.length} emails</span>
                                </div>
                                <div className="glass-panel px-3 py-1.5 flex items-center gap-2 text-xs">
                                    <Sparkles className="w-3.5 h-3.5 text-rose-400" />
                                    <span className="text-rose-400 font-medium">{importantEmails.length} important</span>
                                </div>
                            </div>
                        </div>

                        {/* Stat Cards */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div className="glass-panel p-5 border-l-4 border-l-rose-500 rounded-lg cursor-pointer hover:bg-white/5 transition-colors" onClick={() => setActiveTab('important')}>
                                <div className="flex items-center justify-between mb-1.5">
                                    <h3 className="text-nexus-textMuted font-medium text-xs tracking-wide uppercase">Important</h3>
                                    <Brain className="text-rose-400 w-5 h-5 bg-rose-500/10 p-1 rounded" />
                                </div>
                                <p className="text-3xl font-bold font-mono text-nexus-text">{importantEmails.length}</p>
                                <p className="text-[10px] text-nexus-textMuted mt-0.5">Filtered by AI</p>
                            </div>
                            <div className="glass-panel p-5 border-l-4 border-l-blue-400 rounded-lg cursor-pointer hover:bg-white/5 transition-colors" onClick={() => setActiveTab('calendar')}>
                                <div className="flex items-center justify-between mb-1.5">
                                    <h3 className="text-nexus-textMuted font-medium text-xs tracking-wide uppercase">Meetings</h3>
                                    <Calendar className="text-blue-400 w-5 h-5 bg-blue-500/10 p-1 rounded" />
                                </div>
                                <p className="text-3xl font-bold font-mono text-nexus-text">{profile?.meetingsToday || 0}</p>
                                <p className="text-[10px] text-nexus-textMuted mt-0.5">Today's schedule</p>
                            </div>
                            <div className="glass-panel p-5 border-l-4 border-l-amber-400 rounded-lg relative overflow-hidden">
                                <div className="flex items-center justify-between mb-1.5 relative">
                                    <h3 className="text-nexus-textMuted font-medium text-xs tracking-wide uppercase">Action Items</h3>
                                    <CheckSquare className="text-amber-400 w-5 h-5 bg-amber-500/10 p-1 rounded" />
                                </div>
                                <p className="text-3xl font-bold font-mono relative text-nexus-text">{profile?.actionItems || 0}</p>
                                <p className="text-[10px] text-nexus-textMuted mt-0.5">Pending response</p>
                            </div>
                            <div className="glass-panel p-5 border-l-4 border-l-green-400 rounded-lg relative overflow-hidden">
                                <div className="flex items-center justify-between mb-1.5">
                                    <h3 className="text-nexus-textMuted font-medium text-xs tracking-wide uppercase">Time Saved</h3>
                                    <Clock className="text-green-400 w-5 h-5" />
                                </div>
                                <p className="text-3xl font-bold font-mono text-nexus-text">{profile?.timeSaved || 0}<span className="text-sm text-nexus-textMuted font-medium font-sans ml-1">min</span></p>
                                <p className="text-[10px] text-nexus-textMuted mt-0.5">By AI drafts</p>
                            </div>
                        </div>

                        {/* Main 2-column layout: Content + Meetings sidebar */}
                        <div className="grid grid-cols-1 xl:grid-cols-[1fr_350px] gap-6">
                            {/* Left column — 2-col inner grid */}
                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                {/* Recent Important */}
                                <div className="glass-panel p-5 flex flex-col min-h-[300px]">
                                    <div className="flex items-center justify-between mb-4">
                                        <h3 className="text-sm font-semibold text-nexus-text flex items-center gap-2">
                                            <Sparkles className="w-4 h-4 text-rose-400" /> Recent Important
                                        </h3>
                                        <button onClick={() => setActiveTab('important')} className="text-[10px] text-nexus-primary hover:underline uppercase tracking-wide">View All →</button>
                                    </div>
                                    <div className="flex flex-col gap-2 flex-1">
                                        {importantEmails.slice(0, 5).map(e => (
                                            <div key={e.id} className="flex items-start gap-3 p-2.5 rounded-lg bg-white/[0.03] hover:bg-white/[0.06] transition-colors cursor-pointer border border-transparent hover:border-nexus-border">
                                                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-rose-500/20 to-nexus-primary/20 flex items-center justify-center text-xs font-bold text-rose-300 flex-shrink-0">
                                                    {e.sender.charAt(0).toUpperCase()}
                                                </div>
                                                <div className="min-w-0 flex-1">
                                                    <p className="text-xs font-medium text-nexus-text truncate">{e.subject}</p>
                                                    <p className="text-[10px] text-nexus-textMuted truncate">{e.sender}</p>
                                                </div>
                                                <span className="text-[10px] font-mono text-rose-400 bg-rose-500/10 px-1.5 py-0.5 rounded flex-shrink-0">{e.priorityScore}</span>
                                            </div>
                                        ))}
                                        {importantEmails.length === 0 && (
                                            <div className="flex flex-col items-center justify-center flex-1 gap-2 opacity-30 py-6">
                                                <Sparkles className="w-6 h-6 text-rose-400" />
                                                <p className="text-xs text-nexus-textMuted">All clear — nothing urgent</p>
                                            </div>
                                        )}
                                    </div>
                                </div>

                                {/* Inbox Breakdown */}
                                <div className="glass-panel p-5 flex flex-col min-h-[300px]">
                                    <div className="flex items-center justify-between mb-4">
                                        <h3 className="text-sm font-semibold text-nexus-text flex items-center gap-2">
                                            <TrendingUp className="w-4 h-4 text-blue-400" /> Inbox Breakdown
                                        </h3>
                                        <button onClick={() => setActiveTab('all')} className="text-[10px] text-nexus-primary hover:underline uppercase tracking-wide">View All →</button>
                                    </div>
                                    <div className="flex flex-col gap-2.5 flex-1">
                                        {[
                                            { label: 'Work', color: 'bg-blue-400', cats: ['work','business','professional','important'] },
                                            { label: 'Promotions', color: 'bg-purple-400', cats: ['promotional','newsletter','marketing'] },
                                            { label: 'Transactional', color: 'bg-slate-400', cats: ['transactional','noreply','automated','social'] },
                                            { label: 'Finance / OTPs', color: 'bg-emerald-400', cats: ['bank','finance','otp','alert','security','verification'] },
                                            { label: 'Bills', color: 'bg-rose-400', cats: ['bill','invoice','receipt','subscription'] },
                                        ].map(row => {
                                            const count = inbox.filter(e => row.cats.includes((e.category || '').toLowerCase())).length;
                                            const pct = inbox.length > 0 ? Math.round((count / inbox.length) * 100) : 0;
                                            return (
                                                <div key={row.label} className="flex items-center gap-3">
                                                    <span className={`w-2 h-2 rounded-full ${row.color} flex-shrink-0`} />
                                                    <span className="text-xs text-nexus-textMuted w-28 truncate">{row.label}</span>
                                                    <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
                                                        <div className={`h-full rounded-full ${row.color} transition-all`} style={{ width: `${pct}%` }} />
                                                    </div>
                                                    <span className="text-[10px] font-mono text-nexus-textMuted w-8 text-right">{count}</span>
                                                </div>
                                            );
                                        })}
                                    </div>
                                    <div className="mt-3 pt-3 border-t border-nexus-border flex justify-between text-xs text-nexus-textMuted">
                                        <span>Total emails</span>
                                        <span className="font-mono font-semibold text-nexus-text">{inbox.length}</span>
                                    </div>
                                </div>

                                {/* Risk & Alerts */}
                                <div className="glass-panel p-5 flex flex-col min-h-[200px]">
                                    <div className="flex items-center justify-between mb-4">
                                        <h3 className="text-sm font-semibold text-nexus-text flex items-center gap-2">
                                            <Shield className="w-4 h-4 text-amber-400" /> Risk & Alerts
                                        </h3>
                                    </div>
                                    <div className="flex flex-col gap-2 flex-1">
                                        {riskCount > 0 ? (
                                            inbox.filter(e => e.riskFlags && e.riskFlags.length > 0).slice(0, 3).map(e => (
                                                <div key={e.id} className="flex items-start gap-3 p-2.5 rounded-lg bg-red-500/5 border border-red-500/10">
                                                    <div className="w-7 h-7 rounded-full bg-red-500/15 flex items-center justify-center flex-shrink-0">
                                                        <Shield className="w-3 h-3 text-red-400" />
                                                    </div>
                                                    <div className="min-w-0 flex-1">
                                                        <p className="text-xs font-medium text-nexus-text truncate">{e.subject}</p>
                                                        <p className="text-[10px] text-red-400 truncate">{e.riskFlags?.join(', ')}</p>
                                                    </div>
                                                </div>
                                            ))
                                        ) : (
                                            <div className="flex flex-col items-center justify-center flex-1 gap-2 opacity-30 py-4">
                                                <Shield className="w-7 h-7 text-green-400" />
                                                <p className="text-xs text-nexus-textMuted">No risks detected</p>
                                            </div>
                                        )}
                                    </div>
                                </div>

                                {/* Quick Actions */}
                                <div className="glass-panel p-5 flex flex-col min-h-[200px]">
                                    <h3 className="text-sm font-semibold text-nexus-text flex items-center gap-2 mb-4">
                                        <CheckSquare className="w-4 h-4 text-nexus-primary" /> Quick Actions
                                    </h3>
                                    <div className="grid grid-cols-2 gap-2 flex-1">
                                        <button onClick={handleSync} disabled={syncing}
                                            className="glass-panel p-3 rounded-lg flex flex-col items-center gap-2 hover:bg-white/5 transition-colors border border-nexus-border hover:border-nexus-primary/30 cursor-pointer">
                                            <Mail className={`w-5 h-5 text-nexus-primary ${syncing ? 'animate-spin' : ''}`} />
                                            <span className="text-[10px] text-nexus-textMuted font-medium">{syncing ? 'Syncing...' : 'Sync Inbox'}</span>
                                        </button>
                                        <button onClick={() => setActiveTab('all')}
                                            className="glass-panel p-3 rounded-lg flex flex-col items-center gap-2 hover:bg-white/5 transition-colors border border-nexus-border hover:border-blue-500/30 cursor-pointer">
                                            <Inbox className="w-5 h-5 text-blue-400" />
                                            <span className="text-[10px] text-nexus-textMuted font-medium">All Mail</span>
                                        </button>
                                        <button onClick={() => setActiveTab('calendar')}
                                            className="glass-panel p-3 rounded-lg flex flex-col items-center gap-2 hover:bg-white/5 transition-colors border border-nexus-border hover:border-emerald-500/30 cursor-pointer">
                                            <Calendar className="w-5 h-5 text-emerald-400" />
                                            <span className="text-[10px] text-nexus-textMuted font-medium">Calendar</span>
                                        </button>
                                        <button onClick={() => navigate('/profile')}
                                            className="glass-panel p-3 rounded-lg flex flex-col items-center gap-2 hover:bg-white/5 transition-colors border border-nexus-border hover:border-purple-500/30 cursor-pointer">
                                            <Brain className="w-5 h-5 text-purple-400" />
                                            <span className="text-[10px] text-nexus-textMuted font-medium">AI Settings</span>
                                        </button>
                                    </div>
                                </div>
                            </div>

                            {/* Right column — Today's Schedule (compact meetings widget) */}
                            <div className="h-full min-h-[620px]">
                                <UpcomingMeetings />
                            </div>
                        </div>

                        {/* Meeting Alerts (pending approvals) */}
                        <MeetingAlerts />

                        {/* Analytics */}
                        <AnalyticsDashboard />
                    </div>
                )}

                {/* ═══════════════════════════════════════════════════════════
                    IMPORTANT TAB
                ═══════════════════════════════════════════════════════════ */}
                {activeTab === 'important' && (
                    <div className="w-full flex flex-col gap-6 mb-12">
                        <MeetingAlerts />
                        <div className="w-full h-[820px] xl:h-[900px]">
                            <SplitInbox inbox={inbox} mode="important" />
                        </div>
                    </div>
                )}

                {/* ═══════════════════════════════════════════════════════════
                    ALL MAIL TAB
                ═══════════════════════════════════════════════════════════ */}
                {activeTab === 'all' && (
                    <div className="w-full flex flex-col gap-6 mb-12">
                        <div className="w-full h-[820px] xl:h-[900px]">
                            <SplitInbox inbox={inbox} mode="all" />
                        </div>
                    </div>
                )}

                {/* ═══════════════════════════════════════════════════════════
                    CALENDAR & MEETINGS TAB
                ═══════════════════════════════════════════════════════════ */}
                {activeTab === 'calendar' && (
                    <div className="w-full flex flex-col gap-6 mb-12">
                        <MeetingAlerts />
                        <div className="w-full h-[820px] xl:h-[900px] flex justify-center">
                            <MailSpecialistTimeline fullWidth={true} />
                        </div>
                    </div>
                )}
        </div>
    );
}
