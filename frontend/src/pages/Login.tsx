import { useState } from 'react';
import toast from 'react-hot-toast';
import { GhostCursor } from '../components/GhostCursor';
import { Mail, Sparkles, Zap, Shield } from 'lucide-react';
import { motion } from 'framer-motion';
import api from '../api';

export default function Login() {
    const [isLoading, setIsLoading] = useState(false);


    const handleGoogleLogin = async () => {
        try {
            setIsLoading(true);
            const res = await api.get('/auth/google/url');
            if (res.data?.auth_url) {
                window.location.href = res.data.auth_url;
            }
        } catch (err) {
            console.error('Failed to get Auth URL', err);
            toast.error('Failed to connect to backend.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="relative min-h-screen bg-nexus-bg text-white flex flex-col justify-center items-center overflow-hidden font-sans selection:bg-nexus-primary selection:text-black">

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
            <div className="absolute inset-0 z-0 bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] from-[rgba(177,158,239,0.15)] via-transparent to-transparent opacity-80" />
            <div className="absolute inset-0 z-0 bg-[radial-gradient(circle_at_bottom_left,_var(--tw-gradient-stops))] from-[rgba(130,110,234,0.1)] via-transparent to-transparent opacity-60" />

            {/* Main Login / Hero Overlay Container */}
            <div className="z-20 w-full max-w-6xl px-6 grid grid-cols-1 lg:grid-cols-2 gap-16 items-center flex-1">

                {/* Left Side: Value Proposition */}
                <motion.div
                    initial={{ opacity: 0, x: -40 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 1, ease: "easeOut" }}
                    className="flex flex-col gap-6"
                >
                    <div className="inline-flex items-center gap-2 bg-white/5 border border-white/10 rounded-full px-4 py-1.5 w-max backdrop-blur-md">
                        <Sparkles className="w-4 h-4 text-nexus-primary" />
                        <span className="text-sm font-medium tracking-wide text-white/80">Nexus Intelligence Engine v3.1</span>
                    </div>

                    <h1 className="text-5xl md:text-7xl font-bold tracking-tighter leading-tight mt-2">
                        The smartest <br />
                        <span className="bg-gradient-to-r from-nexus-primary to-blue-400 bg-clip-text text-transparent">
                            inbox ever built.
                        </span>
                    </h1>

                    <p className="text-gray-400 text-lg md:text-xl max-w-lg leading-relaxed mb-6 font-light">
                        Combining lightning-fast communication velocity with uncompromising AI safety. Stop managing emails. Start dispatching workflows.
                    </p>

                    {/* Feature List */}
                    <div className="flex flex-col gap-4 mb-4">
                        <div className="flex items-center gap-4 text-white/70">
                            <div className="bg-white/5 p-2 rounded-full"><Zap className="w-5 h-5 text-nexus-primary" /></div>
                            <span className="text-base font-medium">Draft-First Safety & Smart Priority</span>
                        </div>
                        <div className="flex items-center gap-4 text-white/70">
                            <div className="bg-white/5 p-2 rounded-full"><Shield className="w-5 h-5 text-blue-400" /></div>
                            <span className="text-base font-medium">Redis-Backed Distributed Zero-Loss Sync</span>
                        </div>
                    </div>
                </motion.div>

                {/* Right Side: Glass Login Card */}
                <motion.div
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 1, delay: 0.2, ease: "easeOut" }}
                    className="relative flex justify-center lg:justify-end"
                >
                    <div className="glass-panel w-full max-w-md p-10 flex flex-col items-center relative overflow-hidden group">

                        {/* Ambient card glow */}
                        <div className="absolute top-0 right-0 w-32 h-32 bg-nexus-primary/20 blur-[60px] rounded-full group-hover:bg-nexus-primary/30 transition-all duration-700"></div>

                        <div className="bg-gradient-to-tr from-nexus-card to-nexus-cardHover p-4 rounded-2xl mb-8 border border-white/10 shadow-glass">
                            <Mail className="w-8 h-8 text-white" strokeWidth={1.5} />
                        </div>

                        <h2 className="text-2xl font-semibold mb-2">Sign in to Nexus</h2>
                        <p className="text-white/60 text-center mb-8 font-light text-sm">
                            Connect your Google Workspace.
                            Your data is encrypted via AES-256-GCM.
                        </p>

                        <button
                            onClick={handleGoogleLogin}
                            disabled={isLoading}
                            className={`glass-button w-full shadow-[0_0_20px_rgba(255,255,255,0.05)] mb-6 hover:bg-white/20 transition-all ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
                        >
                            <svg className="w-5 h-5 mr-1" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                                <path d="M5.84 14.1c-.22-.66-.35-1.36-.35-2.1s.13-1.44.35-2.1V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l3.66-2.84z" fill="#FBBC05" />
                                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" fill="#EA4335" />
                            </svg>
                            {isLoading ? 'Connecting...' : 'Sign in with Google'}
                        </button>

                        <p className="mt-6 text-xs text-white/40 text-center font-light">
                            By continuing, you agree to our Terms of Service and Architecture Manifesto.
                        </p>
                    </div>
                </motion.div>
            </div>

        </div>
    );
}
