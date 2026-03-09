import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { GhostCursor } from '../components/GhostCursor';
import { Sparkles, ChevronRight, Github } from 'lucide-react';

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
                    <span className="text-sm font-medium tracking-wide text-white/80">The Open Source Architecture of Empathy</span>
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
