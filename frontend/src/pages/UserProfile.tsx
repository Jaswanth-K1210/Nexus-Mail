import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    User, RefreshCw, Sun, Moon, LogOut, Settings,
    Bell, Shield, Palette, KeyRound, ArrowLeft, Mail,
    Link2, HelpCircle, Brain, Briefcase, Building2,
    Users, Sparkles, Save, AlertTriangle,
    X, Zap,
} from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../api';

type SettingsSection = 'profile' | 'preferences' | 'sync' | 'appearance' | 'notifications' | 'security' | 'integrations' | 'help';

// ─── Constants ───────────────────────────────────────────────────────────────
const ROLE_OPTIONS = [
    { key: 'student', label: 'Student', emoji: '🎓' },
    { key: 'working_professional', label: 'Working Professional', emoji: '💼' },
    { key: 'founder', label: 'Founder / Entrepreneur', emoji: '🚀' },
    { key: 'influencer', label: 'Influencer / Creator', emoji: '🎤' },
    { key: 'freelancer', label: 'Freelancer', emoji: '🖥️' },
    { key: 'business_owner', label: 'Business Owner', emoji: '🏢' },
    { key: 'healthcare', label: 'Healthcare Professional', emoji: '🩺' },
    { key: 'legal', label: 'Legal Professional', emoji: '⚖️' },
    { key: 'educator', label: 'Educator / Teacher', emoji: '📚' },
    { key: 'trades', label: 'Trades / Field Engineer', emoji: '🔧' },
    { key: 'real_estate', label: 'Real Estate Agent', emoji: '🏠' },
    { key: 'nonprofit', label: 'Nonprofit / NGO', emoji: '🤝' },
    { key: 'finance', label: 'Finance / Accounting', emoji: '📊' },
    { key: 'sales_marketing', label: 'Sales & Marketing', emoji: '📣' },
];

const INDUSTRIES = [
    'SaaS / Software', 'Finance / Fintech', 'Healthcare', 'E-commerce',
    'Media / Content', 'Education', 'Consulting', 'Other',
];

const SIZES = ['Solo', 'Startup (1-10)', 'SMB (10-100)', 'Mid-market (100-1k)', 'Enterprise (1k+)'];

const SENDERS = [
    'Investors / VCs', 'Customers / Clients', 'Co-founders / Team',
    'Vendors / Partners', 'Press / Media', 'Advisors / Mentors',
    'Job Applicants', 'Government / Legal', 'Personal Contacts',
];

// ─── Types ───────────────────────────────────────────────────────────────────
interface UserPreferences {
    role: string;
    roleKey: string;
    industry: string;
    companySize: string;
    importantSenders: string[];
    customPersona: string;
}

interface UserInfo {
    email: string;
    name: string;
    picture: string;
    createdAt: string;
    calendarConnected: boolean;
}

const DEFAULT_PREFS: UserPreferences = {
    role: '',
    roleKey: '',
    industry: '',
    companySize: 'Startup (1-10)',
    importantSenders: [],
    customPersona: '',
};

function prefsEqual(a: UserPreferences, b: UserPreferences): boolean {
    return (
        a.role === b.role &&
        a.roleKey === b.roleKey &&
        a.industry === b.industry &&
        a.companySize === b.companySize &&
        a.customPersona === b.customPersona &&
        a.importantSenders.length === b.importantSenders.length &&
        a.importantSenders.every((s, i) => b.importantSenders[i] === s)
    );
}

// ─── Component ───────────────────────────────────────────────────────────────
export default function UserProfile() {
    const navigate = useNavigate();
    const [activeSection, setActiveSection] = useState<SettingsSection>('profile');
    const [isDarkMode, setIsDarkMode] = useState(true);
    const [syncing, setSyncing] = useState(false);

    // User info (read-only)
    const [userInfo, setUserInfo] = useState<UserInfo>({
        email: '', name: '', picture: '', createdAt: '', calendarConnected: false,
    });

    // Preferences (editable)
    const [prefs, setPrefs] = useState<UserPreferences>({ ...DEFAULT_PREFS });
    const [savedPrefs, setSavedPrefs] = useState<UserPreferences>({ ...DEFAULT_PREFS });
    const [personaPreview, setPersonaPreview] = useState('');

    // Save state
    const [saving, setSaving] = useState(false);
    const [loading, setLoading] = useState(true);

    // Auto-reply state
    const [autoReplyEnabled, setAutoReplyEnabled] = useState(false);
    const [autoReplyCategories, setAutoReplyCategories] = useState<string[]>([
        'newsletter', 'transactional', 'social', 'promotional',
    ]);

    const hasUnsavedChanges = !prefsEqual(prefs, savedPrefs);

    // ─── Load data ───
    useEffect(() => {
        const token = localStorage.getItem('nexus_token');
        if (!token) { navigate('/'); return; }

        Promise.all([
            api.get('/auth/me').catch(() =>
                // Fallback if /auth/me is not available yet
                api.get('/auth/consent-status')
            ),
            api.get('/tone/context').catch(() => ({ data: {} })),
            api.get('/auto-reply/settings').catch(() => ({ data: {} })),
        ]).then(([meRes, ctxRes, autoReplyRes]) => {
            const me = meRes.data || {};
            setUserInfo({
                email: me.email || '',
                name: me.name || '',
                picture: me.picture || '',
                createdAt: me.created_at || '',
                calendarConnected: me.calendar_connected || false,
            });

            const ctx = ctxRes.data || {};
            const loaded: UserPreferences = {
                role: ctx.role || '',
                roleKey: ctx.role_key || '',
                industry: ctx.industry || '',
                companySize: ctx.company_size || 'Startup (1-10)',
                importantSenders: ctx.important_senders || [],
                customPersona: ctx.custom_persona || '',
            };
            setPrefs(loaded);
            setSavedPrefs(loaded);
            if (ctx.generated_persona) setPersonaPreview(ctx.generated_persona);

            // Auto-reply settings
            const arData = autoReplyRes.data || {};
            if (arData.enabled !== undefined) setAutoReplyEnabled(arData.enabled);
            if (arData.categories) setAutoReplyCategories(arData.categories);
        }).catch((err) => {
            console.error('Failed to load settings', err);
            // Only redirect if it's an auth error (401)
            if (err?.response?.status === 401) navigate('/');
        }).finally(() => setLoading(false));
    }, [navigate]);

    // ─── Preference setters ───
    const updatePref = useCallback(<K extends keyof UserPreferences>(key: K, value: UserPreferences[K]) => {
        setPrefs(prev => ({ ...prev, [key]: value }));
    }, []);

    const toggleSender = useCallback((s: string) => {
        setPrefs(prev => ({
            ...prev,
            importantSenders: prev.importantSenders.includes(s)
                ? prev.importantSenders.filter(x => x !== s)
                : [...prev.importantSenders, s],
        }));
    }, []);

    // ─── Save ───
    const handleSave = async () => {
        try {
            setSaving(true);
            const res = await api.patch('/tone/context', {
                role: prefs.role,
                role_key: prefs.roleKey,
                industry: prefs.industry,
                company_size: prefs.companySize,
                important_senders: prefs.importantSenders,
                custom_persona: prefs.customPersona,
            });
            setPersonaPreview(res.data.persona || '');
            setSavedPrefs({ ...prefs });
            toast.success('Settings saved successfully');

            // Trigger reprocessing with new role in background
            api.post('/gmail/reprocess').catch((err) => {
                console.error('Auto-reprocessing failed', err);
            });
        } catch (err: any) {
            console.error('Save failed', err?.response?.data || err);
            const detail = err?.response?.data?.detail;
            toast.error(detail ? `Save failed: ${detail}` : 'Failed to save settings. Please try again.');
        } finally {
            setSaving(false);
        }
    };

    const handleDiscard = () => {
        setPrefs({ ...savedPrefs });
    };

    // ─── Other actions ───
    const handleSync = async () => {
        try {
            setSyncing(true);
            await api.post('/gmail/sync');
            await api.post('/gmail/process');
            toast.success('Sync completed successfully');
        } catch {
            toast.error('Sync failed. You might need to reconnect your Google account.');
        } finally {
            setSyncing(false);
        }
    };

    const handleLogout = () => {
        localStorage.removeItem('nexus_token');
        navigate('/');
    };

    // ─── Navigation guard ───
    const handleNavigateAway = (path: string) => {
        if (hasUnsavedChanges) {
            if (!window.confirm('You have unsaved changes. Discard and leave?')) return;
        }
        navigate(path);
    };

    // ─── Sidebar items ───
    const sidebarItems = [
        { id: 'profile' as SettingsSection, label: 'Profile', icon: User },
        { id: 'preferences' as SettingsSection, label: 'Preferences', icon: Brain },
        { id: 'sync' as SettingsSection, label: 'Sync & Data', icon: RefreshCw },
        { id: 'appearance' as SettingsSection, label: 'Appearance', icon: Palette },
        { id: 'notifications' as SettingsSection, label: 'Notifications', icon: Bell },
        { id: 'security' as SettingsSection, label: 'Security', icon: Shield },
        { id: 'integrations' as SettingsSection, label: 'Integrations', icon: Link2 },
        { id: 'help' as SettingsSection, label: 'Help & Support', icon: HelpCircle },
    ];

    // ─── Format join date ───
    const formatDate = (dateStr: string) => {
        if (!dateStr) return 'Unknown';
        try {
            return new Date(dateStr).toLocaleDateString('en-US', {
                year: 'numeric', month: 'long', day: 'numeric',
            });
        } catch { return 'Unknown'; }
    };

    const currentRole = ROLE_OPTIONS.find(r => r.key === prefs.roleKey);

    // ─── Render sections ───
    const renderContent = () => {
        switch (activeSection) {
            // ── Profile ──────────────────────────────────────────────────
            case 'profile':
                return (
                    <div className="space-y-6">
                        <div>
                            <h2 className="text-2xl font-bold text-nexus-text flex items-center gap-3">
                                <User className="w-6 h-6 text-nexus-primary" />
                                Profile
                            </h2>
                            <p className="text-sm text-nexus-textMuted mt-1">
                                Your account information. Email cannot be changed as it's linked to your Google account.
                            </p>
                        </div>

                        {/* User card */}
                        <div className="glass-panel p-6">
                            <div className="flex items-center gap-5">
                                {userInfo.picture ? (
                                    <img
                                        src={userInfo.picture}
                                        alt="Profile"
                                        className="w-20 h-20 rounded-full border-2 border-nexus-primary/30"
                                        referrerPolicy="no-referrer"
                                    />
                                ) : (
                                    <div className="w-20 h-20 rounded-full bg-gradient-to-br from-nexus-primary to-blue-500 flex items-center justify-center text-3xl font-bold text-white">
                                        {userInfo.name ? userInfo.name[0].toUpperCase() : userInfo.email ? userInfo.email[0].toUpperCase() : 'U'}
                                    </div>
                                )}
                                <div className="flex-1">
                                    <p className="text-lg font-semibold text-nexus-text">
                                        {userInfo.name || 'Nexus User'}
                                    </p>
                                    <p className="text-sm text-nexus-textMuted">{userInfo.email}</p>
                                    {currentRole && (
                                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border border-nexus-primary/30 bg-nexus-primary/10 text-nexus-primary mt-2">
                                            <span>{currentRole.emoji}</span>
                                            <span>{currentRole.label}</span>
                                        </span>
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Details */}
                        <div className="glass-panel p-6 space-y-5">
                            <div>
                                <label className="block text-xs font-medium text-nexus-textMuted uppercase tracking-wide mb-2">Email Address</label>
                                <div className="flex items-center gap-3">
                                    <input
                                        type="email"
                                        value={userInfo.email}
                                        disabled
                                        className="flex-1 glass-panel px-4 py-3 text-nexus-text bg-white/5 rounded-lg cursor-not-allowed opacity-60"
                                    />
                                    <span className="text-[10px] text-nexus-textMuted bg-white/5 px-2 py-1 rounded border border-nexus-border">
                                        Linked to Google
                                    </span>
                                </div>
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-nexus-textMuted uppercase tracking-wide mb-2">Full Name</label>
                                <input
                                    type="text"
                                    value={userInfo.name}
                                    disabled
                                    className="w-full glass-panel px-4 py-3 text-nexus-text bg-white/5 rounded-lg cursor-not-allowed opacity-60"
                                />
                            </div>
                            <div className="flex items-center justify-between pt-3 border-t border-nexus-border">
                                <span className="text-xs text-nexus-textMuted">Member since</span>
                                <span className="text-xs font-medium text-nexus-text">{formatDate(userInfo.createdAt)}</span>
                            </div>
                        </div>

                        {/* Current preferences summary */}
                        <div className="glass-panel p-6 space-y-4">
                            <div className="flex items-center justify-between">
                                <h3 className="text-base font-semibold text-nexus-text flex items-center gap-2">
                                    <Sparkles className="w-4 h-4 text-nexus-primary" />
                                    Current Preferences
                                </h3>
                                <button
                                    onClick={() => setActiveSection('preferences')}
                                    className="text-xs text-nexus-primary hover:underline"
                                >
                                    Edit Preferences
                                </button>
                            </div>
                            <div className="grid grid-cols-2 gap-4 text-sm">
                                <div>
                                    <span className="text-xs text-nexus-textMuted block mb-1">Role</span>
                                    <span className="text-nexus-text font-medium">
                                        {currentRole ? `${currentRole.emoji} ${currentRole.label}` : 'Not set'}
                                    </span>
                                </div>
                                <div>
                                    <span className="text-xs text-nexus-textMuted block mb-1">Industry</span>
                                    <span className="text-nexus-text font-medium">{savedPrefs.industry || 'Not set'}</span>
                                </div>
                                <div>
                                    <span className="text-xs text-nexus-textMuted block mb-1">Company Size</span>
                                    <span className="text-nexus-text font-medium">{savedPrefs.companySize || 'Not set'}</span>
                                </div>
                                <div>
                                    <span className="text-xs text-nexus-textMuted block mb-1">Priority Senders</span>
                                    <span className="text-nexus-text font-medium">
                                        {savedPrefs.importantSenders.length > 0
                                            ? `${savedPrefs.importantSenders.length} groups`
                                            : 'Not set'}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                );

            // ── Preferences ──────────────────────────────────────────────
            case 'preferences':
                return (
                    <div className="space-y-6">
                        <div>
                            <h2 className="text-2xl font-bold text-nexus-text flex items-center gap-3">
                                <Brain className="w-6 h-6 text-nexus-primary" />
                                Preferences
                            </h2>
                            <p className="text-sm text-nexus-textMuted mt-1">
                                Configure how Nexus classifies and prioritises your emails. Changes take effect after saving.
                            </p>
                        </div>

                        {/* Role Picker */}
                        <div className="glass-panel p-6 space-y-4">
                            <div className="flex items-center gap-2">
                                <Briefcase className="w-4 h-4 text-nexus-primary" />
                                <h3 className="text-base font-semibold text-nexus-text">Your Role</h3>
                                {prefs.roleKey !== savedPrefs.roleKey && (
                                    <span className="text-[10px] text-amber-400 bg-amber-400/10 px-1.5 py-0.5 rounded">Changed</span>
                                )}
                            </div>
                            <div className="grid grid-cols-2 gap-2">
                                {ROLE_OPTIONS.map(r => (
                                    <button
                                        key={r.key}
                                        onClick={() => { updatePref('role', r.label); updatePref('roleKey', r.key); }}
                                        className={`px-3 py-2.5 rounded-xl text-sm font-medium border transition-all text-left flex items-center gap-2 ${
                                            prefs.roleKey === r.key
                                                ? 'bg-nexus-primary/20 border-nexus-primary text-nexus-primary shadow-[0_0_15px_rgba(177,158,239,0.2)]'
                                                : 'border-nexus-border text-nexus-textMuted hover:border-nexus-primary/40 hover:text-nexus-text bg-white/5'
                                        }`}
                                    >
                                        <span>{r.emoji}</span>
                                        <span>{r.label}</span>
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Industry + Company Size */}
                        <div className="glass-panel p-6 space-y-5">
                            <div className="flex items-center gap-2">
                                <Building2 className="w-4 h-4 text-nexus-primary" />
                                <h3 className="text-base font-semibold text-nexus-text">Company & Industry</h3>
                                {(prefs.industry !== savedPrefs.industry || prefs.companySize !== savedPrefs.companySize) && (
                                    <span className="text-[10px] text-amber-400 bg-amber-400/10 px-1.5 py-0.5 rounded">Changed</span>
                                )}
                            </div>
                            <div>
                                <label className="text-xs text-nexus-textMuted uppercase tracking-wide font-medium mb-2 block">Industry</label>
                                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                                    {INDUSTRIES.map(ind => (
                                        <button
                                            key={ind}
                                            onClick={() => updatePref('industry', ind)}
                                            className={`px-3 py-2 rounded-lg text-xs font-medium border transition-all ${
                                                prefs.industry === ind
                                                    ? 'bg-blue-500/20 border-blue-400 text-blue-300'
                                                    : 'border-nexus-border text-nexus-textMuted hover:border-blue-500/50 bg-white/5'
                                            }`}
                                        >
                                            {ind}
                                        </button>
                                    ))}
                                </div>
                            </div>
                            <div>
                                <label className="text-xs text-nexus-textMuted uppercase tracking-wide font-medium mb-2 block">Company Size</label>
                                <div className="flex gap-2 flex-wrap">
                                    {SIZES.map(size => (
                                        <button
                                            key={size}
                                            onClick={() => updatePref('companySize', size)}
                                            className={`px-3 py-2 rounded-lg text-xs font-medium border transition-all ${
                                                prefs.companySize === size
                                                    ? 'bg-emerald-500/20 border-emerald-400 text-emerald-300'
                                                    : 'border-nexus-border text-nexus-textMuted hover:border-emerald-500/50 bg-white/5'
                                            }`}
                                        >
                                            {size}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>

                        {/* Important Senders */}
                        <div className="glass-panel p-6 space-y-4">
                            <div className="flex items-center gap-2">
                                <Users className="w-4 h-4 text-nexus-primary" />
                                <h3 className="text-base font-semibold text-nexus-text">Who matters most?</h3>
                                {JSON.stringify(prefs.importantSenders) !== JSON.stringify(savedPrefs.importantSenders) && (
                                    <span className="text-[10px] text-amber-400 bg-amber-400/10 px-1.5 py-0.5 rounded">Changed</span>
                                )}
                            </div>
                            <p className="text-xs text-nexus-textMuted">Emails from these groups get elevated priority automatically.</p>
                            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                                {SENDERS.map(sender => (
                                    <button
                                        key={sender}
                                        onClick={() => toggleSender(sender)}
                                        className={`px-3 py-2 rounded-lg text-xs font-medium border transition-all text-left ${
                                            prefs.importantSenders.includes(sender)
                                                ? 'bg-purple-500/20 border-purple-400 text-purple-300'
                                                : 'border-nexus-border text-nexus-textMuted hover:border-purple-500/50 bg-white/5'
                                        }`}
                                    >
                                        {sender}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Auto-Reply Settings */}
                        <div className="glass-panel p-6 space-y-4">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <Zap className="w-4 h-4 text-nexus-primary" />
                                    <h3 className="text-base font-semibold text-nexus-text">Smart Auto-Reply</h3>
                                </div>
                                <button
                                    onClick={async () => {
                                        const newVal = !autoReplyEnabled;
                                        setAutoReplyEnabled(newVal);
                                        try {
                                            await api.put('/auto-reply/settings', { enabled: newVal, categories: autoReplyCategories });
                                            toast.success(newVal ? 'Auto-reply enabled' : 'Auto-reply disabled');
                                        } catch { toast.error('Failed to update auto-reply settings'); }
                                    }}
                                    className={`relative w-12 h-6 rounded-full transition-colors ${autoReplyEnabled ? 'bg-nexus-primary' : 'bg-white/10'}`}
                                >
                                    <div className={`absolute top-0.5 w-5 h-5 rounded-full bg-white transition-transform ${autoReplyEnabled ? 'translate-x-6' : 'translate-x-0.5'}`} />
                                </button>
                            </div>
                            <p className="text-xs text-nexus-textMuted">
                                Automatically sends short acknowledgement replies to low-priority emails that need a response — using your tone profile. No commitments are made.
                            </p>
                            {autoReplyEnabled && (
                                <div>
                                    <label className="text-xs text-nexus-textMuted uppercase tracking-wide font-medium mb-2 block">Auto-reply for these categories</label>
                                    <div className="flex flex-wrap gap-2">
                                        {['newsletter', 'transactional', 'social', 'promotional', 'requires_response'].map(cat => (
                                            <button
                                                key={cat}
                                                onClick={async () => {
                                                    const newCats = autoReplyCategories.includes(cat)
                                                        ? autoReplyCategories.filter(c => c !== cat)
                                                        : [...autoReplyCategories, cat];
                                                    setAutoReplyCategories(newCats);
                                                    try { await api.put('/auto-reply/settings', { enabled: true, categories: newCats }); } catch {}
                                                }}
                                                className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all capitalize ${
                                                    autoReplyCategories.includes(cat)
                                                        ? 'bg-nexus-primary/20 border-nexus-primary text-nexus-primary'
                                                        : 'border-nexus-border text-nexus-textMuted hover:border-nexus-primary/40 bg-white/5'
                                                }`}
                                            >
                                                {cat.replace('_', ' ')}
                                            </button>
                                        ))}
                                    </div>
                                    <p className="text-[10px] text-nexus-textMuted/50 mt-2">
                                        Only emails with priority score below 35 and not marked "ACTION REQUIRED" will get auto-replies.
                                    </p>
                                </div>
                            )}
                        </div>

                        {/* AI Persona Preview */}
                        {personaPreview && (
                            <div className="glass-panel p-5 border border-nexus-primary/20 bg-nexus-primary/5">
                                <div className="flex items-center gap-2 mb-2">
                                    <Sparkles className="w-4 h-4 text-nexus-primary" />
                                    <span className="text-xs font-semibold text-nexus-primary uppercase tracking-wide">AI Persona (injected into classifier)</span>
                                </div>
                                <p className="text-sm text-nexus-text leading-relaxed">{personaPreview}</p>
                            </div>
                        )}

                        {/* Save / Discard buttons */}
                        <div className="flex items-center gap-3 pt-2">
                            <button
                                onClick={handleSave}
                                disabled={saving || !hasUnsavedChanges}
                                className={`flex items-center gap-2 px-6 py-3 rounded-lg text-sm font-semibold transition-all ${
                                    hasUnsavedChanges
                                        ? 'bg-nexus-primary text-white hover:bg-nexus-primary/90 shadow-[0_0_20px_rgba(177,158,239,0.3)]'
                                        : 'bg-white/5 text-nexus-textMuted cursor-not-allowed'
                                } ${saving ? 'opacity-50 cursor-not-allowed' : ''}`}
                            >
                                {saving ? (
                                    <><RefreshCw className="w-4 h-4 animate-spin" /> Saving...</>
                                ) : (
                                    <><Save className="w-4 h-4" /> Save Changes</>
                                )}
                            </button>
                            {hasUnsavedChanges && (
                                <button
                                    onClick={handleDiscard}
                                    className="flex items-center gap-2 px-5 py-3 rounded-lg text-sm font-medium text-nexus-textMuted hover:text-nexus-text hover:bg-white/5 transition-colors border border-nexus-border"
                                >
                                    <X className="w-4 h-4" /> Discard
                                </button>
                            )}
                        </div>
                    </div>
                );

            // ── Sync & Data ──────────────────────────────────────────────
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

            // ── Appearance ───────────────────────────────────────────────
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

            // ── Notifications ────────────────────────────────────────────
            case 'notifications':
                return (
                    <div className="space-y-6">
                        <h2 className="text-2xl font-bold text-nexus-text">Notifications</h2>
                        <div className="glass-panel p-6 space-y-6">
                            {[
                                { title: 'Email Notifications', desc: 'Get notified about important emails' },
                                { title: 'Meeting Reminders', desc: 'Get reminded about upcoming meetings' },
                                { title: 'AI Draft Ready', desc: 'Notify when AI completes a draft' },
                            ].map((item, i) => (
                                <div key={item.title} className={`flex items-center justify-between ${i > 0 ? 'border-t border-nexus-border pt-6' : ''}`}>
                                    <div>
                                        <h3 className="text-lg font-semibold text-nexus-text">{item.title}</h3>
                                        <p className="text-sm text-nexus-textMuted">{item.desc}</p>
                                    </div>
                                    <label className="relative inline-flex items-center cursor-pointer">
                                        <input type="checkbox" defaultChecked className="sr-only peer" />
                                        <div className="w-11 h-6 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-nexus-primary" />
                                    </label>
                                </div>
                            ))}
                        </div>
                    </div>
                );

            // ── Security ─────────────────────────────────────────────────
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
                                    <span className="text-nexus-text">{userInfo.email}</span>
                                    <span className="text-xs bg-green-500/20 text-green-400 px-2 py-1 rounded">Connected</span>
                                </div>
                            </div>
                            <div className="border-t border-nexus-border pt-6">
                                <h3 className="text-lg font-semibold text-nexus-text mb-2">Session</h3>
                                <p className="text-sm text-nexus-textMuted mb-4">Manage your current session.</p>
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

            // ── Integrations ─────────────────────────────────────────────
            case 'integrations':
                return (
                    <div className="space-y-6">
                        <h2 className="text-2xl font-bold text-nexus-text">Integrations</h2>
                        <div className="glass-panel p-6 space-y-6">
                            {[
                                { icon: Mail, iconColor: 'text-red-400', name: 'Gmail', desc: 'Primary email integration', connected: true },
                                { icon: KeyRound, iconColor: 'text-blue-400', name: 'Google Calendar', desc: 'Calendar sync', connected: userInfo.calendarConnected },
                            ].map((item, i) => (
                                <div key={item.name} className={`flex items-center justify-between ${i > 0 ? 'border-t border-nexus-border pt-6' : ''}`}>
                                    <div className="flex items-center gap-4">
                                        <div className="w-12 h-12 bg-white/10 rounded-lg flex items-center justify-center">
                                            <item.icon className={`w-6 h-6 ${item.iconColor}`} />
                                        </div>
                                        <div>
                                            <h3 className="text-lg font-semibold text-nexus-text">{item.name}</h3>
                                            <p className="text-sm text-nexus-textMuted">{item.desc}</p>
                                        </div>
                                    </div>
                                    <span className={`text-xs px-3 py-1 rounded-full ${
                                        item.connected
                                            ? 'bg-green-500/20 text-green-400'
                                            : 'bg-white/10 text-nexus-textMuted'
                                    }`}>
                                        {item.connected ? 'Connected' : 'Not connected'}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                );

            // ── Help ─────────────────────────────────────────────────────
            case 'help':
                return (
                    <div className="space-y-6">
                        <h2 className="text-2xl font-bold text-nexus-text">Help & Support</h2>
                        <div className="glass-panel p-6 space-y-6">
                            <div>
                                <h3 className="text-lg font-semibold text-nexus-text mb-2">Keyboard Shortcuts</h3>
                                <div className="space-y-2 text-sm">
                                    {[
                                        ['Command Palette', '⌘ + K'],
                                        ['Next Email', 'J'],
                                        ['Previous Email', 'K'],
                                        ['Open Email', 'Enter'],
                                    ].map(([label, key]) => (
                                        <div key={label} className="flex justify-between">
                                            <span className="text-nexus-textMuted">{label}</span>
                                            <kbd className="glass-panel px-2 py-1 rounded text-xs">{key}</kbd>
                                        </div>
                                    ))}
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

    if (loading) {
        return (
            <div className="min-h-screen bg-nexus-bg flex items-center justify-center text-white">
                <div className="w-8 h-8 border-2 border-nexus-primary/30 border-t-nexus-primary rounded-full animate-spin" />
            </div>
        );
    }

    return (
        <div className={`min-h-screen font-sans ${isDarkMode ? '' : 'light-theme bg-[#F5F5F7] text-[#1d1d1f]'} transition-colors duration-500`}>
            <div className="min-h-screen bg-nexus-bg text-nexus-text flex">
                {/* Sidebar */}
                <aside className="w-72 border-r border-nexus-border p-6 flex flex-col">
                    <button
                        onClick={() => handleNavigateAway('/dashboard')}
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
                <main className="flex-1 flex flex-col overflow-hidden">
                    {/* Unsaved changes banner */}
                    {hasUnsavedChanges && (
                        <div className="flex items-center justify-between px-8 py-3 bg-amber-500/10 border-b border-amber-500/20">
                            <div className="flex items-center gap-2 text-amber-400">
                                <AlertTriangle className="w-4 h-4" />
                                <span className="text-sm font-medium">You have unsaved changes</span>
                            </div>
                            <div className="flex items-center gap-3">
                                <button
                                    onClick={handleDiscard}
                                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-nexus-textMuted hover:text-nexus-text hover:bg-white/5 transition-colors"
                                >
                                    <X className="w-3.5 h-3.5" />
                                    Discard
                                </button>
                                <button
                                    onClick={handleSave}
                                    disabled={saving}
                                    className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-semibold bg-nexus-primary text-white hover:bg-nexus-primary/90 transition-colors disabled:opacity-50"
                                >
                                    {saving ? (
                                        <><RefreshCw className="w-3.5 h-3.5 animate-spin" /> Saving...</>
                                    ) : (
                                        <><Save className="w-3.5 h-3.5" /> Save Changes</>
                                    )}
                                </button>
                            </div>
                        </div>
                    )}

                    <div className="flex-1 overflow-auto p-8">
                        <div className="max-w-3xl">
                            {renderContent()}
                        </div>
                    </div>
                </main>
            </div>
        </div>
    );
}
