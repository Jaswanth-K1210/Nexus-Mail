import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Brain, Briefcase, Building2, Users, Sparkles,
    ChevronRight, ChevronLeft, Rocket,
} from 'lucide-react';
import api from '../api';

const ROLES = [
    'Startup Founder / CEO', 'Product Manager', 'Software Engineer',
    'Designer', 'Sales / BD', 'Marketing', 'Investor / VC', 'Freelancer', 'Student', 'Other',
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

export default function Onboarding() {
    const navigate = useNavigate();
    const [step, setStep] = useState(0);
    const [role, setRole] = useState('');
    const [customRole, setCustomRole] = useState('');
    const [industry, setIndustry] = useState('');
    const [companySize, setCompanySize] = useState('Startup (1-10)');
    const [importantSenders, setImportantSenders] = useState<string[]>([]);
    const [saving, setSaving] = useState(false);

    const effectiveRole = ROLES.includes(role) ? role : customRole || role;

    const toggleSender = (s: string) => {
        setImportantSenders(prev =>
            prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s]
        );
    };

    const handleFinish = async () => {
        try {
            setSaving(true);
            await api.patch('/tone/context', {
                role: effectiveRole,
                industry,
                company_size: companySize,
                important_senders: importantSenders,
                custom_persona: '',
            });
            navigate('/dashboard');
        } catch (err) {
            console.error('Failed to save context', err);
            // Still navigate — don't block the user
            navigate('/dashboard');
        }
    };

    const handleSkip = () => {
        localStorage.setItem('nexus_onboarding_skipped', 'true');
        navigate('/dashboard');
    };

    const steps = [
        // Step 0 — Role
        {
            title: 'What do you do?',
            subtitle: 'This helps Nexus prioritise the emails that matter to you.',
            icon: Briefcase,
            content: (
                <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-2">
                        {ROLES.map(r => (
                            <button key={r} onClick={() => setRole(r)}
                                className={`px-4 py-3 rounded-xl text-sm font-medium border transition-all text-left ${
                                    role === r
                                        ? 'bg-nexus-primary/20 border-nexus-primary text-nexus-primary shadow-[0_0_15px_rgba(177,158,239,0.2)]'
                                        : 'border-nexus-border text-nexus-textMuted hover:border-nexus-primary/40 hover:text-nexus-text bg-white/5'
                                }`}>{r}</button>
                        ))}
                    </div>
                    {role === 'Other' && (
                        <input type="text" placeholder="Type your role..."
                            value={customRole} onChange={e => setCustomRole(e.target.value)}
                            autoFocus
                            className="w-full px-4 py-3 rounded-xl text-sm text-nexus-text bg-white/5 border border-nexus-border focus:border-nexus-primary outline-none"
                        />
                    )}
                </div>
            ),
            canProceed: !!effectiveRole,
        },
        // Step 1 — Industry + Size
        {
            title: 'Your company',
            subtitle: 'Industry context makes classification smarter.',
            icon: Building2,
            content: (
                <div className="space-y-6">
                    <div>
                        <label className="text-xs text-nexus-textMuted uppercase tracking-wide font-semibold mb-3 block">Industry</label>
                        <div className="grid grid-cols-2 gap-2">
                            {INDUSTRIES.map(ind => (
                                <button key={ind} onClick={() => setIndustry(ind)}
                                    className={`px-3 py-2.5 rounded-xl text-sm font-medium border transition-all text-left ${
                                        industry === ind
                                            ? 'bg-blue-500/20 border-blue-400 text-blue-300 shadow-[0_0_12px_rgba(59,130,246,0.15)]'
                                            : 'border-nexus-border text-nexus-textMuted hover:border-blue-500/40 bg-white/5'
                                    }`}>{ind}</button>
                            ))}
                        </div>
                    </div>
                    <div>
                        <label className="text-xs text-nexus-textMuted uppercase tracking-wide font-semibold mb-3 block">Company Size</label>
                        <div className="flex gap-2 flex-wrap">
                            {SIZES.map(size => (
                                <button key={size} onClick={() => setCompanySize(size)}
                                    className={`px-3 py-2.5 rounded-xl text-xs font-medium border transition-all ${
                                        companySize === size
                                            ? 'bg-emerald-500/20 border-emerald-400 text-emerald-300'
                                            : 'border-nexus-border text-nexus-textMuted hover:border-emerald-500/40 bg-white/5'
                                    }`}>{size}</button>
                            ))}
                        </div>
                    </div>
                </div>
            ),
            canProceed: !!industry,
        },
        // Step 2 — Important Senders
        {
            title: 'Who matters most?',
            subtitle: 'Select the groups whose emails should always be high priority.',
            icon: Users,
            content: (
                <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-2">
                        {SENDERS.map(sender => (
                            <button key={sender} onClick={() => toggleSender(sender)}
                                className={`px-3 py-2.5 rounded-xl text-sm font-medium border transition-all text-left ${
                                    importantSenders.includes(sender)
                                        ? 'bg-purple-500/20 border-purple-400 text-purple-300 shadow-[0_0_12px_rgba(168,85,247,0.15)]'
                                        : 'border-nexus-border text-nexus-textMuted hover:border-purple-500/40 bg-white/5'
                                }`}>{sender}</button>
                        ))}
                    </div>
                    <p className="text-xs text-nexus-textMuted text-center mt-2">
                        You can change these anytime in Settings → AI Context
                    </p>
                </div>
            ),
            canProceed: importantSenders.length > 0,
        },
    ];

    const current = steps[step];
    const Icon = current.icon;
    const isLast = step === steps.length - 1;

    return (
        <div className="min-h-screen bg-nexus-bg flex items-center justify-center p-4">
            {/* Background glow */}
            <div className="fixed inset-0 overflow-hidden pointer-events-none">
                <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full bg-nexus-primary/5 blur-[120px]" />
            </div>

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="glass-panel w-full max-w-lg p-8 relative z-10"
            >
                {/* Progress bar */}
                <div className="flex gap-2 mb-8">
                    {steps.map((_, i) => (
                        <div key={i} className="flex-1 h-1 rounded-full overflow-hidden bg-white/10">
                            <motion.div
                                className="h-full bg-nexus-primary rounded-full"
                                initial={{ width: 0 }}
                                animate={{ width: i <= step ? '100%' : '0%' }}
                                transition={{ duration: 0.4, ease: 'easeOut' }}
                            />
                        </div>
                    ))}
                </div>

                {/* Header */}
                <div className="flex items-center gap-3 mb-2">
                    <div className="w-10 h-10 rounded-xl bg-nexus-primary/15 flex items-center justify-center">
                        <Icon className="w-5 h-5 text-nexus-primary" />
                    </div>
                    <div>
                        <h2 className="text-xl font-bold text-nexus-text">{current.title}</h2>
                        <p className="text-xs text-nexus-textMuted">{current.subtitle}</p>
                    </div>
                </div>

                {/* Step content with animation */}
                <AnimatePresence mode="wait">
                    <motion.div
                        key={step}
                        initial={{ opacity: 0, x: 30 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -30 }}
                        transition={{ duration: 0.25 }}
                        className="mt-6 mb-8"
                    >
                        {current.content}
                    </motion.div>
                </AnimatePresence>

                {/* Navigation */}
                <div className="flex items-center justify-between">
                    <div>
                        {step > 0 ? (
                            <button onClick={() => setStep(s => s - 1)}
                                className="flex items-center gap-1.5 text-sm text-nexus-textMuted hover:text-nexus-text transition-colors">
                                <ChevronLeft className="w-4 h-4" /> Back
                            </button>
                        ) : (
                            <button onClick={handleSkip}
                                className="text-xs text-nexus-textMuted hover:text-nexus-text transition-colors underline underline-offset-2 opacity-60 hover:opacity-100">
                                Skip for now
                            </button>
                        )}
                    </div>

                    <button
                        onClick={isLast ? handleFinish : () => setStep(s => s + 1)}
                        disabled={!current.canProceed || (isLast && saving)}
                        className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold transition-all ${
                            current.canProceed
                                ? 'bg-nexus-primary text-white hover:bg-nexus-primary/90 shadow-[0_0_20px_rgba(177,158,239,0.3)]'
                                : 'bg-white/5 text-nexus-textMuted cursor-not-allowed'
                        }`}
                    >
                        {isLast ? (
                            saving
                                ? <>Saving...</>
                                : <><Rocket className="w-4 h-4" /> Launch Inbox</>
                        ) : (
                            <>Continue <ChevronRight className="w-4 h-4" /></>
                        )}
                    </button>
                </div>

                {/* Step counter */}
                <div className="mt-6 flex items-center justify-center gap-2">
                    <Brain className="w-3.5 h-3.5 text-nexus-primary/50" />
                    <span className="text-[10px] text-nexus-textMuted uppercase tracking-widest">
                        Step {step + 1} of {steps.length}
                    </span>
                    <Sparkles className="w-3.5 h-3.5 text-nexus-primary/50" />
                </div>
            </motion.div>
        </div>
    );
}
