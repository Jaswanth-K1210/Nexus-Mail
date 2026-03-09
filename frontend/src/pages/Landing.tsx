import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { GhostCursor } from '../components/GhostCursor';
import { Sparkles, Zap, Shield, ChevronRight, Github, Lock, Clock, Calendar, Database } from 'lucide-react';

export default function Landing() {
    const navigate = useNavigate();

    return (
        <div className="relative min-h-screen bg-nexus-bg text-white overflow-x-hidden font-sans selection:bg-nexus-primary selection:text-black">
            {/* Ghost Cursor running in the background */}
            <GhostCursor
                color="#B19EEF"
                brightness={1.2}
                edgeIntensity={0}
                trailLength={20}
                inertia={0.4}
                grainIntensity={0.05}
                bloomStrength={0.5}
                bloomRadius={0.7}
                bloomThreshold={0}
                fadeDelayMs={200}
                fadeDurationMs={1000}
            />

            {/* Background decoration: Glows */}
            <div className="fixed inset-0 z-0 bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] from-[rgba(177,158,239,0.1)] via-transparent to-transparent opacity-80 pointer-events-none" />
            <div className="fixed inset-0 z-0 bg-[radial-gradient(circle_at_bottom_left,_var(--tw-gradient-stops))] from-[rgba(130,110,234,0.05)] via-transparent to-transparent opacity-60 pointer-events-none" />

            {/* Navbar */}
            <nav className="relative z-20 w-full bg-black/50 backdrop-blur-xl border-b border-white/10 px-6 py-4">
                <div className="max-w-7xl mx-auto flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-nexus-primary to-blue-500 shadow-[0_0_15px_rgba(177,158,239,0.5)]"></div>
                        <span className="font-bold text-xl tracking-wide">Nexus Mail</span>
                    </div>
                    <div className="flex items-center gap-6">
                        <a href="https://github.com/Jaswanth-K1210/Nexus-Mail.git" target="_blank" rel="noreferrer" className="text-white/70 hover:text-white transition-colors hidden md:flex items-center gap-2 text-sm font-medium">
                            <Github className="w-4 h-4" /> Open Source
                        </a>
                        <button onClick={() => navigate('/login')} className="glass-button text-sm py-2 px-6">
                            Sign In
                        </button>
                    </div>
                </div>
            </nav>

            {/* Hero Section */}
            <section className="relative z-10 max-w-7xl mx-auto px-6 pt-32 pb-20 flex flex-col items-center text-center">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8 }}
                    className="inline-flex items-center gap-2 bg-white/5 border border-white/10 rounded-full px-4 py-1.5 w-max backdrop-blur-md mb-8"
                >
                    <Sparkles className="w-4 h-4 text-nexus-primary" />
                    <span className="text-sm font-medium tracking-wide text-white/80">Enterprise SaaS Architecture Released</span>
                </motion.div>

                <motion.h1
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, delay: 0.1 }}
                    className="text-6xl md:text-8xl font-bold tracking-tighter leading-tight max-w-4xl"
                >
                    The smartest <br className="hidden md:block" />
                    <span className="bg-gradient-to-r from-nexus-primary to-blue-400 bg-clip-text text-transparent">
                        inbox ever built.
                    </span>
                </motion.h1>

                <motion.p
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, delay: 0.2 }}
                    className="text-gray-400 text-xl max-w-2xl leading-relaxed mt-6 mb-12 font-light"
                >
                    A privacy-first, zero-data retention command center.
                    Stop managing emails. Start dispatching workflows using lightning-fast AI.
                </motion.p>

                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, delay: 0.3 }}
                    className="flex flex-col sm:flex-row gap-4 w-full sm:w-auto"
                >
                    <button onClick={() => navigate('/login')} className="glass-button glass-button-primary px-8 py-4 text-lg w-full sm:w-auto flex items-center justify-center gap-2 group">
                        Get Started Free
                        <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                    </button>
                    <a href="https://github.com/Jaswanth-K1210/Nexus-Mail.git" target="_blank" rel="noreferrer" className="glass-button px-8 py-4 text-lg w-full sm:w-auto flex items-center justify-center gap-2 hover:bg-white/10">
                        <Github className="w-5 h-5" /> Star on GitHub
                    </a>
                </motion.div>
            </section>

            {/* Features Grid */}
            <section className="relative z-10 max-w-7xl mx-auto px-6 py-24">
                <div className="text-center mb-16">
                    <h2 className="text-3xl md:text-5xl font-bold mb-4">Engineered for Enterprise</h2>
                    <p className="text-white/50 text-lg max-w-2xl mx-auto">Open-source flexibility. B2B SaaS scalability. Uncompromising security.</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {/* Feature 1 */}
                    <div className="glass-panel p-8 hover:bg-white/[0.03] transition-colors border-white/5 shadow-glass group relative overflow-hidden">
                        <div className="absolute top-0 right-0 w-32 h-32 bg-nexus-primary/10 blur-[50px] rounded-full group-hover:bg-nexus-primary/20 transition-all duration-700"></div>
                        <Database className="w-10 h-10 text-nexus-primary mb-6" />
                        <h3 className="text-xl font-semibold mb-3">Zero-Data Retention</h3>
                        <p className="text-white/60 font-light leading-relaxed">
                            We aggressively drop heavy HTML/Text payloads from the database the moment AI processing concludes. Keep the intelligence, drop the bulk. MongoDB 30-Day TTL automates data purging.
                        </p>
                    </div>

                    {/* Feature 2 */}
                    <div className="glass-panel p-8 hover:bg-white/[0.03] transition-colors border-white/5 shadow-glass group relative overflow-hidden">
                        <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/10 blur-[50px] rounded-full group-hover:bg-blue-500/20 transition-all duration-700"></div>
                        <Zap className="w-10 h-10 text-blue-400 mb-6" />
                        <h3 className="text-xl font-semibold mb-3">Sub-Second AI (Groq)</h3>
                        <p className="text-white/60 font-light leading-relaxed">
                            Powered by Llama-3 8b via Groq. Features highly-optimized Plain-Text KV extraction to process incoming emails with under 1s latency at a fraction of standard JSON API token costs.
                        </p>
                    </div>

                    {/* Feature 3 */}
                    <div className="glass-panel p-8 hover:bg-white/[0.03] transition-colors border-white/5 shadow-glass group relative overflow-hidden">
                        <div className="absolute top-0 right-0 w-32 h-32 bg-purple-500/10 blur-[50px] rounded-full group-hover:bg-purple-500/20 transition-all duration-700"></div>
                        <Calendar className="w-10 h-10 text-purple-400 mb-6" />
                        <h3 className="text-xl font-semibold mb-3">Mail Specialist Timeline</h3>
                        <p className="text-white/60 font-light leading-relaxed">
                            Stop missing deadlines. Nexus extracts action items directly from email bodies and merges them cohesively with a scrolling timeline of your upcoming Google Calendar meetings.
                        </p>
                    </div>
                </div>
            </section>

            {/* SaaS Tiers */}
            <section className="relative z-10 max-w-7xl mx-auto px-6 py-24 border-t border-white/5">
                <div className="text-center mb-16">
                    <h2 className="text-3xl md:text-5xl font-bold mb-4">Scalable Tiers</h2>
                    <p className="text-white/50 text-lg max-w-2xl mx-auto">Deploy internally or use our hosted cloud infrastructure.</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
                    {/* Free */}
                    <div className="glass-panel p-8 border-white/10 opacity-80 hover:opacity-100 transition-opacity flex flex-col">
                        <h3 className="text-2xl font-bold text-white mb-2">Community Free</h3>
                        <p className="text-3xl font-light mb-6">$0<span className="text-lg text-white/40">/mo</span></p>
                        <ul className="text-white/60 flex flex-col gap-4 mb-8 flex-1 text-sm font-light border-t border-white/10 pt-6">
                            <li className="flex items-center gap-3"><Clock className="w-4 h-4 text-nexus-primary" /> 15-Minute Sync Polling</li>
                            <li className="flex items-center gap-3"><Lock className="w-4 h-4" /> 500 Emails / Week</li>
                            <li className="flex items-center gap-3"><Sparkles className="w-4 h-4" /> Basic Priority Splitting</li>
                        </ul>
                        <button onClick={() => navigate('/login')} className="glass-button w-full py-3 hover:bg-white/10">Get Started</button>
                    </div>

                    {/* Pro */}
                    <div className="glass-panel p-8 border-nexus-primary/30 shadow-[0_0_30px_rgba(177,158,239,0.1)] relative transform md:-translate-y-4 flex flex-col">
                        <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-nexus-primary text-black text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider">Most Popular</div>
                        <h3 className="text-2xl font-bold text-nexus-primary mb-2">Pro Individual</h3>
                        <p className="text-3xl font-light mb-6">$15<span className="text-lg text-white/40">/mo</span></p>
                        <ul className="text-white/80 flex flex-col gap-4 mb-8 flex-1 text-sm font-light border-t border-white/10 pt-6">
                            <li className="flex items-center gap-3"><Zap className="w-4 h-4 text-nexus-primary" /> Real-time Google Webhook Push</li>
                            <li className="flex items-center gap-3"><Lock className="w-4 h-4 text-blue-400" /> Unlimited Email Syncs</li>
                            <li className="flex items-center gap-3"><Calendar className="w-4 h-4 text-purple-400" /> Full Specialist Timeline</li>
                            <li className="flex items-center gap-3"><Shield className="w-4 h-4" /> Draft-First Replies</li>
                        </ul>
                        <button onClick={() => navigate('/login')} className="glass-button glass-button-primary w-full py-3">Upgrade to Pro</button>
                    </div>

                    {/* Enterprise */}
                    <div className="glass-panel p-8 border-white/10 opacity-80 hover:opacity-100 transition-opacity flex flex-col">
                        <h3 className="text-2xl font-bold text-white mb-2">Enterprise</h3>
                        <p className="text-3xl font-light mb-6">$12<span className="text-lg text-white/40">/seat</span></p>
                        <ul className="text-white/60 flex flex-col gap-4 mb-8 flex-1 text-sm font-light border-t border-white/10 pt-6">
                            <li className="flex items-center gap-3"><Lock className="w-4 h-4 text-nexus-primary" /> Centralized Billing</li>
                            <li className="flex items-center gap-3"><Database className="w-4 h-4" /> Logical ID Data Segregation</li>
                            <li className="flex items-center gap-3"><Sparkles className="w-4 h-4" /> Group NLP Automation Rules</li>
                        </ul>
                        <button onClick={() => window.open('https://github.com/Jaswanth-K1210/Nexus-Mail.git')} className="glass-button w-full py-3 hover:bg-white/10">Fork Repository</button>
                    </div>
                </div>
            </section>

            {/* Footer */}
            <footer className="relative z-10 w-full border-t border-white/10 py-10 mt-10 bg-black/40">
                <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-4">
                    <div className="flex items-center gap-2 opacity-50">
                        <div className="w-5 h-5 rounded-full bg-gradient-to-tr from-white to-gray-500"></div>
                        <span className="font-semibold text-sm">Nexus Mail OS</span>
                    </div>
                    <p className="text-sm text-white/30">© 2026 Nexus Mail. Open Source under MIT License.</p>
                </div>
            </footer>
        </div>
    );
}
