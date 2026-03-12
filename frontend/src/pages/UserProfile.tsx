import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    User,
    RefreshCw,
    Sun,
    Moon,
    LogOut,
    Settings,
    Bell,
    Shield,
    Palette,
    KeyRound,
    ArrowLeft,
    Mail,
    Link2,
    HelpCircle,
    Brain,
    Briefcase,
    Building2,
    Users,
    Sparkles,
    CheckCircle2,
} from 'lucide-react';
import api from '../api';

type SettingsSection = 'profile' | 'aicontext' | 'sync' | 'appearance' | 'notifications' | 'security' | 'integrations' | 'help';

export default function UserProfile() {
    const navigate = useNavigate();
    const [activeSection, setActiveSection] = useState<SettingsSection>('profile');
    const [isDarkMode, setIsDarkMode] = useState(true);
    const [syncing, setSyncing] = useState(false);
    const [userEmail, setUserEmail] = useState<string>('');

    // AI Context state
    const [aiRole, setAiRole] = useState('');
    const [aiIndustry, setAiIndustry] = useState('');
    const [aiCompanySize, setAiCompanySize] = useState('Startup (1-10)');
    const [aiImportantSenders, setAiImportantSenders] = useState<string[]>([]);
    const [aiCustomPersona, setAiCustomPersona] = useState('');
    const [aiSaving, setAiSaving] = useState(false);
    const [aiSaved, setAiSaved] = useState(false);
    const [aiPersonaPreview, setAiPersonaPreview] = useState('');

    useEffect(() => {
        const token = localStorage.getItem('nexus_token');
        if (!token) {
            navigate('/');
            return;
        }
        api.get('/auth/consent-status').then((res) => {
            if (res.data.email) setUserEmail(res.data.email);
        }).catch(() => { navigate('/'); });
        // Load saved AI context
        api.get('/tone/context').then((res) => {
            if (res.data.role) setAiRole(res.data.role);
            if (res.data.industry) setAiIndustry(res.data.industry);
            if (res.data.company_size) setAiCompanySize(res.data.company_size);
            if (res.data.important_senders) setAiImportantSenders(res.data.important_senders);
            if (res.data.custom_persona) setAiCustomPersona(res.data.custom_persona);
            if (res.data.generated_persona) setAiPersonaPreview(res.data.generated_persona);
        }).catch(() => {});
    }, [navigate]);

    const handleSync = async () => {
        try {
            setSyncing(true);
            await api.post('/gmail/sync');
            await api.post('/gmail/process');
            alert('Sync completed successfully!');
        } catch (err) {
            console.error("Sync failed", err);
            alert("Sync failed. You might need to reconnect your Google account.");
        } finally {
            setSyncing(false);
        }
    };

    const handleLogout = () => {
        localStorage.removeItem('nexus_token');
        navigate('/');
    };

    const handleSaveAiContext = async () => {
        try {
            setAiSaving(true);
            const res = await api.patch('/tone/context', {
                role: aiRole,
                industry: aiIndustry,
                company_size: aiCompanySize,
                important_senders: aiImportantSenders,
                custom_persona: aiCustomPersona,
            });
            setAiPersonaPreview(res.data.persona || '');
            setAiSaved(true);
            setTimeout(() => setAiSaved(false), 3000);
        } catch (err) {
            console.error('AI context save failed', err);
        } finally {
            setAiSaving(false);
        }
    };

    const toggleSender = (s: string) => {
        setAiImportantSenders(prev =>
            prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s]
        );
    };

    const sidebarItems = [
        { id: 'profile' as SettingsSection, label: 'Profile', icon: User },
        { id: 'aicontext' as SettingsSection, label: 'AI Context', icon: Brain },
        { id: 'sync' as SettingsSection, label: 'Sync & Data', icon: RefreshCw },
        { id: 'appearance' as SettingsSection, label: 'Appearance', icon: Palette },
        { id: 'notifications' as SettingsSection, label: 'Notifications', icon: Bell },
        { id: 'security' as SettingsSection, label: 'Security', icon: Shield },
        { id: 'integrations' as SettingsSection, label: 'Integrations', icon: Link2 },
        { id: 'help' as SettingsSection, label: 'Help & Support', icon: HelpCircle },
    ];

    const renderContent = () => {
        switch (activeSection) {
            case 'aicontext':
                return (
                    <div className="space-y-6">
                        <div>
                            <h2 className="text-2xl font-bold text-nexus-text flex items-center gap-3">
                                <Brain className="w-6 h-6 text-nexus-primary" />
                                AI Classification Context
                            </h2>
                            <p className="text-sm text-nexus-textMuted mt-1">
                                Tell Nexus who you are. This is injected directly into the AI classifier so emails are prioritised correctly from day one.
                            </p>
                        </div>

                        {/* Role Picker */}
                        <div className="glass-panel p-6 space-y-4">
                            <div className="flex items-center gap-2">
                                <Briefcase className="w-4 h-4 text-nexus-primary" />
                                <h3 className="text-base font-semibold text-nexus-text">Your Role</h3>
                            </div>
                            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                                {['Startup Founder / CEO','Product Manager','Software Engineer','Designer','Sales / BD','Marketing','Investor / VC','Freelancer','Other'].map(role => (
                                    <button key={role} onClick={() => setAiRole(role)}
                                        className={`px-3 py-2.5 rounded-lg text-sm font-medium border transition-all text-left ${
                                            aiRole === role ? 'bg-nexus-primary/20 border-nexus-primary text-nexus-primary' : 'border-nexus-border text-nexus-textMuted hover:border-nexus-primary/50 bg-white/5'
                                        }`}>{role}</button>
                                ))}
                            </div>
                            <input type="text" placeholder="Or type a custom role..."
                                value={['Startup Founder / CEO','Product Manager','Software Engineer','Designer','Sales / BD','Marketing','Investor / VC','Freelancer','Other'].includes(aiRole) ? '' : aiRole}
                                onChange={e => setAiRole(e.target.value)}
                                className="w-full glass-panel px-4 py-2.5 text-sm text-nexus-text bg-white/5 rounded-lg border border-nexus-border focus:border-nexus-primary outline-none"
                            />
                        </div>

                        {/* Industry + Company Size */}
                        <div className="glass-panel p-6 space-y-5">
                            <div className="flex items-center gap-2">
                                <Building2 className="w-4 h-4 text-nexus-primary" />
                                <h3 className="text-base font-semibold text-nexus-text">Company & Industry</h3>
                            </div>
                            <div>
                                <label className="text-xs text-nexus-textMuted uppercase tracking-wide font-medium mb-2 block">Industry</label>
                                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                                    {['SaaS / Software','Finance / Fintech','Healthcare','E-commerce','Media / Content','Education','Consulting','Other'].map(ind => (
                                        <button key={ind} onClick={() => setAiIndustry(ind)}
                                            className={`px-3 py-2 rounded-lg text-xs font-medium border transition-all ${
                                                aiIndustry === ind ? 'bg-blue-500/20 border-blue-400 text-blue-300' : 'border-nexus-border text-nexus-textMuted hover:border-blue-500/50 bg-white/5'
                                            }`}>{ind}</button>
                                    ))}
                                </div>
                            </div>
                            <div>
                                <label className="text-xs text-nexus-textMuted uppercase tracking-wide font-medium mb-2 block">Company Size</label>
                                <div className="flex gap-2 flex-wrap">
                                    {['Solo','Startup (1-10)','SMB (10-100)','Mid-market (100-1k)','Enterprise (1k+)'].map(size => (
                                        <button key={size} onClick={() => setAiCompanySize(size)}
                                            className={`px-3 py-2 rounded-lg text-xs font-medium border transition-all ${
                                                aiCompanySize === size ? 'bg-emerald-500/20 border-emerald-400 text-emerald-300' : 'border-nexus-border text-nexus-textMuted hover:border-emerald-500/50 bg-white/5'
                                            }`}>{size}</button>
                                    ))}
                                </div>
                            </div>
                        </div>

                        {/* Important Senders */}
                        <div className="glass-panel p-6 space-y-4">
                            <div className="flex items-center gap-2">
                                <Users className="w-4 h-4 text-nexus-primary" />
                                <h3 className="text-base font-semibold text-nexus-text">Who matters most?</h3>
                            </div>
                            <p className="text-xs text-nexus-textMuted">Emails from these groups get elevated priority automatically.</p>
                            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                                {['Investors / VCs','Customers / Clients','Co-founders / Team','Vendors / Partners','Press / Media','Advisors / Mentors','Job Applicants','Government / Legal','Personal Contacts'].map(sender => (
                                    <button key={sender} onClick={() => toggleSender(sender)}
                                        className={`px-3 py-2 rounded-lg text-xs font-medium border transition-all text-left ${
                                            aiImportantSenders.includes(sender) ? 'bg-purple-500/20 border-purple-400 text-purple-300' : 'border-nexus-border text-nexus-textMuted hover:border-purple-500/50 bg-white/5'
                                        }`}>{sender}</button>
                                ))}
                            </div>
                        </div>

                        {/* Preview */}
                        {aiPersonaPreview && (
                            <div className="glass-panel p-5 border border-nexus-primary/20 bg-nexus-primary/5">
                                <div className="flex items-center gap-2 mb-2">
                                    <Sparkles className="w-4 h-4 text-nexus-primary" />
                                    <span className="text-xs font-semibold text-nexus-primary uppercase tracking-wide">AI Persona (injected into classifier)</span>
                                </div>
                                <p className="text-sm text-nexus-text leading-relaxed">{aiPersonaPreview}</p>
                            </div>
                        )}

                        {/* Save */}
                        <button onClick={handleSaveAiContext} disabled={aiSaving}
                            className={`glass-button-primary px-6 py-3 rounded-lg flex items-center gap-2 transition-all ${
                                aiSaved ? 'bg-green-500/20 border-green-400 text-green-300' : ''
                            } ${aiSaving ? 'opacity-50 cursor-not-allowed' : ''}`}>
                            {aiSaved
                                ? <><CheckCircle2 className="w-5 h-5" /> Saved!</>
                                : aiSaving
                                    ? <><RefreshCw className="w-5 h-5 animate-spin" /> Saving...</>
                                    : <><Brain className="w-5 h-5" /> Save & Apply to AI</>}
                        </button>
                    </div>
                );
            case 'profile':
                return (
                    <div className="space-y-6">
                        <h2 className="text-2xl font-bold text-nexus-text">Profile Settings</h2>
                        <div className="glass-panel p-6 space-y-4">
                            <div className="flex items-center gap-4">
                                <div className="w-20 h-20 rounded-full bg-gradient-to-br from-nexus-primary to-blue-500 flex items-center justify-center text-3xl font-bold text-white">
                                    {userEmail ? userEmail[0].toUpperCase() : 'U'}
                                </div>
                                <div>
                                    <p className="text-lg font-semibold text-nexus-text">{userEmail || 'User'}</p>
                                    <p className="text-sm text-nexus-textMuted">Connected via Google</p>
                                </div>
                            </div>
                            <div className="pt-4 border-t border-nexus-border">
                                <label className="block text-sm font-medium text-nexus-textMuted mb-2">Email Address</label>
                                <input
                                    type="email"
                                    value={userEmail}
                                    disabled
                                    className="w-full glass-panel px-4 py-3 text-nexus-text bg-white/5 rounded-lg cursor-not-allowed"
                                />
                            </div>
                        </div>
                    </div>
                );
            case 'sync':
                return (
                    <div className="space-y-6">
                        <h2 className="text-2xl font-bold text-nexus-text">Sync & Data</h2>
                        <div className="glass-panel p-6 space-y-6">
                            <div>
                                <h3 className="text-lg font-semibold text-nexus-text mb-2">Force Sync</h3>
                                <p className="text-sm text-nexus-textMuted mb-4">
                                    Manually sync your inbox and process emails through the AI pipeline.
                                </p>
                                <button
                                    onClick={handleSync}
                                    disabled={syncing}
                                    className={`glass-button-primary px-6 py-3 rounded-lg flex items-center gap-2 ${syncing ? 'opacity-50 cursor-not-allowed' : ''}`}
                                >
                                    <RefreshCw className={`w-5 h-5 ${syncing ? 'animate-spin' : ''}`} />
                                    {syncing ? 'Syncing...' : 'Force Sync Now'}
                                </button>
                            </div>
                            <div className="border-t border-nexus-border pt-6">
                                <h3 className="text-lg font-semibold text-nexus-text mb-2">Auto-Sync Settings</h3>
                                <p className="text-sm text-nexus-textMuted mb-4">
                                    Configure how often Nexus automatically syncs your emails.
                                </p>
                                <select className="glass-panel px-4 py-3 rounded-lg text-nexus-text bg-white/5 w-full max-w-xs">
                                    <option value="5">Every 5 minutes</option>
                                    <option value="15">Every 15 minutes</option>
                                    <option value="30">Every 30 minutes</option>
                                    <option value="60">Every hour</option>
                                </select>
                            </div>
                        </div>
                    </div>
                );
            case 'appearance':
                return (
                    <div className="space-y-6">
                        <h2 className="text-2xl font-bold text-nexus-text">Appearance</h2>
                        <div className="glass-panel p-6 space-y-6">
                            <div>
                                <h3 className="text-lg font-semibold text-nexus-text mb-2">Theme</h3>
                                <p className="text-sm text-nexus-textMuted mb-4">
                                    Choose between dark and light mode.
                                </p>
                                <div className="flex gap-4">
                                    <button
                                        onClick={() => setIsDarkMode(true)}
                                        className={`glass-panel px-6 py-4 rounded-lg flex items-center gap-3 transition-all ${isDarkMode ? 'ring-2 ring-nexus-primary' : ''}`}
                                    >
                                        <Moon className="w-6 h-6 text-blue-400" />
                                        <span className="text-nexus-text font-medium">Dark</span>
                                    </button>
                                    <button
                                        onClick={() => setIsDarkMode(false)}
                                        className={`glass-panel px-6 py-4 rounded-lg flex items-center gap-3 transition-all ${!isDarkMode ? 'ring-2 ring-nexus-primary' : ''}`}
                                    >
                                        <Sun className="w-6 h-6 text-amber-400" />
                                        <span className="text-nexus-text font-medium">Light</span>
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                );
            case 'notifications':
                return (
                    <div className="space-y-6">
                        <h2 className="text-2xl font-bold text-nexus-text">Notifications</h2>
                        <div className="glass-panel p-6 space-y-6">
                            <div className="flex items-center justify-between">
                                <div>
                                    <h3 className="text-lg font-semibold text-nexus-text">Email Notifications</h3>
                                    <p className="text-sm text-nexus-textMuted">Get notified about important emails</p>
                                </div>
                                <label className="relative inline-flex items-center cursor-pointer">
                                    <input type="checkbox" defaultChecked className="sr-only peer" />
                                    <div className="w-11 h-6 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-nexus-primary"></div>
                                </label>
                            </div>
                            <div className="flex items-center justify-between border-t border-nexus-border pt-6">
                                <div>
                                    <h3 className="text-lg font-semibold text-nexus-text">Meeting Reminders</h3>
                                    <p className="text-sm text-nexus-textMuted">Get reminded about upcoming meetings</p>
                                </div>
                                <label className="relative inline-flex items-center cursor-pointer">
                                    <input type="checkbox" defaultChecked className="sr-only peer" />
                                    <div className="w-11 h-6 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-nexus-primary"></div>
                                </label>
                            </div>
                            <div className="flex items-center justify-between border-t border-nexus-border pt-6">
                                <div>
                                    <h3 className="text-lg font-semibold text-nexus-text">AI Draft Ready</h3>
                                    <p className="text-sm text-nexus-textMuted">Notify when AI completes a draft</p>
                                </div>
                                <label className="relative inline-flex items-center cursor-pointer">
                                    <input type="checkbox" defaultChecked className="sr-only peer" />
                                    <div className="w-11 h-6 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-nexus-primary"></div>
                                </label>
                            </div>
                        </div>
                    </div>
                );
            case 'security':
                return (
                    <div className="space-y-6">
                        <h2 className="text-2xl font-bold text-nexus-text">Security</h2>
                        <div className="glass-panel p-6 space-y-6">
                            <div>
                                <h3 className="text-lg font-semibold text-nexus-text mb-2">Connected Account</h3>
                                <p className="text-sm text-nexus-textMuted mb-4">
                                    Your account is connected via Google OAuth.
                                </p>
                                <div className="flex items-center gap-3 glass-panel px-4 py-3 rounded-lg w-fit">
                                    <Mail className="w-5 h-5 text-nexus-primary" />
                                    <span className="text-nexus-text">{userEmail}</span>
                                    <span className="text-xs bg-green-500/20 text-green-400 px-2 py-1 rounded">Connected</span>
                                </div>
                            </div>
                            <div className="border-t border-nexus-border pt-6">
                                <h3 className="text-lg font-semibold text-nexus-text mb-2">Session</h3>
                                <p className="text-sm text-nexus-textMuted mb-4">
                                    Manage your current session.
                                </p>
                                <button
                                    onClick={handleLogout}
                                    className="glass-button px-6 py-3 rounded-lg flex items-center gap-2 text-red-400 hover:bg-red-500/10 transition-colors"
                                >
                                    <LogOut className="w-5 h-5" />
                                    Logout
                                </button>
                            </div>
                        </div>
                    </div>
                );
            case 'integrations':
                return (
                    <div className="space-y-6">
                        <h2 className="text-2xl font-bold text-nexus-text">Integrations</h2>
                        <div className="glass-panel p-6 space-y-6">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-4">
                                    <div className="w-12 h-12 bg-white/10 rounded-lg flex items-center justify-center">
                                        <Mail className="w-6 h-6 text-red-400" />
                                    </div>
                                    <div>
                                        <h3 className="text-lg font-semibold text-nexus-text">Gmail</h3>
                                        <p className="text-sm text-nexus-textMuted">Primary email integration</p>
                                    </div>
                                </div>
                                <span className="text-xs bg-green-500/20 text-green-400 px-3 py-1 rounded-full">Connected</span>
                            </div>
                            <div className="flex items-center justify-between border-t border-nexus-border pt-6">
                                <div className="flex items-center gap-4">
                                    <div className="w-12 h-12 bg-white/10 rounded-lg flex items-center justify-center">
                                        <KeyRound className="w-6 h-6 text-blue-400" />
                                    </div>
                                    <div>
                                        <h3 className="text-lg font-semibold text-nexus-text">Google Calendar</h3>
                                        <p className="text-sm text-nexus-textMuted">Calendar sync</p>
                                    </div>
                                </div>
                                <span className="text-xs bg-green-500/20 text-green-400 px-3 py-1 rounded-full">Connected</span>
                            </div>
                        </div>
                    </div>
                );
            case 'help':
                return (
                    <div className="space-y-6">
                        <h2 className="text-2xl font-bold text-nexus-text">Help & Support</h2>
                        <div className="glass-panel p-6 space-y-6">
                            <div>
                                <h3 className="text-lg font-semibold text-nexus-text mb-2">Documentation</h3>
                                <p className="text-sm text-nexus-textMuted mb-4">
                                    Learn how to get the most out of Nexus Mail.
                                </p>
                                <a href="#" className="text-nexus-primary hover:underline">View Documentation →</a>
                            </div>
                            <div className="border-t border-nexus-border pt-6">
                                <h3 className="text-lg font-semibold text-nexus-text mb-2">Keyboard Shortcuts</h3>
                                <p className="text-sm text-nexus-textMuted mb-4">
                                    Quick access to common actions.
                                </p>
                                <div className="space-y-2 text-sm">
                                    <div className="flex justify-between">
                                        <span className="text-nexus-textMuted">Command Palette</span>
                                        <kbd className="glass-panel px-2 py-1 rounded text-xs">⌘ + K</kbd>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-nexus-textMuted">Next Email</span>
                                        <kbd className="glass-panel px-2 py-1 rounded text-xs">J</kbd>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-nexus-textMuted">Previous Email</span>
                                        <kbd className="glass-panel px-2 py-1 rounded text-xs">K</kbd>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-nexus-textMuted">Open Email</span>
                                        <kbd className="glass-panel px-2 py-1 rounded text-xs">Enter</kbd>
                                    </div>
                                </div>
                            </div>
                            <div className="border-t border-nexus-border pt-6">
                                <h3 className="text-lg font-semibold text-nexus-text mb-2">Version</h3>
                                <p className="text-sm text-nexus-textMuted">Nexus Mail v1.0.0</p>
                            </div>
                        </div>
                    </div>
                );
            default:
                return null;
        }
    };

    return (
        <div className={`min-h-screen font-sans ${isDarkMode ? '' : 'light-theme bg-[#F5F5F7] text-[#1d1d1f]'} transition-colors duration-500`}>
            <div className="min-h-screen bg-nexus-bg text-nexus-text flex">
                {/* Sidebar */}
                <aside className="w-72 border-r border-nexus-border p-6 flex flex-col">
                    <button
                        onClick={() => navigate('/dashboard')}
                        className="flex items-center gap-2 text-nexus-textMuted hover:text-nexus-text transition-colors mb-8"
                    >
                        <ArrowLeft className="w-5 h-5" />
                        <span>Back to Dashboard</span>
                    </button>

                    <div className="flex items-center gap-3 mb-8">
                        <Settings className="w-6 h-6 text-nexus-primary" />
                        <h1 className="text-xl font-bold text-nexus-text">Settings</h1>
                    </div>

                    <nav className="flex-1 space-y-1">
                        {sidebarItems.map((item) => (
                            <button
                                key={item.id}
                                onClick={() => setActiveSection(item.id)}
                                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                                    activeSection === item.id
                                        ? 'bg-nexus-primary/10 text-nexus-primary'
                                        : 'text-nexus-textMuted hover:text-nexus-text hover:bg-white/5'
                                }`}
                            >
                                <item.icon className="w-5 h-5" />
                                <span className="font-medium">{item.label}</span>
                            </button>
                        ))}
                    </nav>

                    <div className="border-t border-nexus-border pt-6 mt-6">
                        <button
                            onClick={handleLogout}
                            className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-red-400 hover:bg-red-500/10 transition-all"
                        >
                            <LogOut className="w-5 h-5" />
                            <span className="font-medium">Logout</span>
                        </button>
                    </div>
                </aside>

                {/* Main Content */}
                <main className="flex-1 p-8 overflow-auto">
                    <div className="max-w-3xl">
                        {renderContent()}
                    </div>
                </main>
            </div>
        </div>
    );
}
