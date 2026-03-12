import { useEffect, useState, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import api from '../api';

export default function AuthCallback() {
    const navigate = useNavigate();
    const location = useLocation();
    const [status, setStatus] = useState('Authenticating with Nexus Backend...');
    const isProcessed = useRef(false);

    useEffect(() => {
        async function processAuth() {
            if (isProcessed.current) return;
            isProcessed.current = true;

            const params = new URLSearchParams(location.search);
            const code = params.get('code');

            if (!code) {
                setStatus('Authentication failed. No code provided.');
                return;
            }

            try {
                setStatus('Validating Google OAuth credentials...');
                const response = await api.post('/auth/google/callback', {
                    code: code,
                    consent_given: true // Per the backend requirement
                });

                if (response.data && response.data.access_token) {
                    localStorage.setItem('nexus_token', response.data.access_token);
                    setStatus('Authentication successful! Setting up...');

                    // Check if user already completed onboarding
                    try {
                        const ctx = await api.get('/tone/context');
                        const hasContext = ctx.data && ctx.data.role;
                        navigate(hasContext ? '/dashboard' : '/onboarding');
                    } catch {
                        navigate('/onboarding');
                    }
                } else {
                    setStatus('Authentication failed: Missing token in response.');
                }

            } catch (err: unknown) {
                console.error("Auth Exception:", err);
                const errorObj = err as { response?: { data?: { detail?: string } }, message?: string };
                const errorDetail = errorObj.response?.data?.detail || errorObj.message || JSON.stringify(err);
                setStatus(`Authentication failed: ${errorDetail}`);
            }
        }

        processAuth();
    }, [location.search, navigate]);

    return (
        <div className="min-h-screen bg-nexus-bg flex items-center justify-center text-white p-4">
            <div className="glass-panel w-full max-w-md p-10 flex flex-col items-center">
                <div className="w-12 h-12 border-4 border-nexus-primary/30 border-t-nexus-primary rounded-full animate-spin mb-6"></div>
                <p className="text-center font-medium opacity-80">{status}</p>
            </div>
        </div>
    );
}
