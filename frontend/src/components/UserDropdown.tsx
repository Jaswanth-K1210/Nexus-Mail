import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, Settings, LogOut, RefreshCw, ChevronDown } from 'lucide-react';
import api from '../api';

interface UserDropdownProps {
    onSync: () => void;
    syncing: boolean;
}

export function UserDropdown({ onSync, syncing }: UserDropdownProps) {
    const navigate = useNavigate();
    const [isOpen, setIsOpen] = useState(false);
    const [userEmail, setUserEmail] = useState<string>('');
    const dropdownRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        api.get('/auth/consent-status').then((res) => {
            if (res.data.email) {
                setUserEmail(res.data.email);
            }
        }).catch(() => {});
    }, []);

    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        }
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleLogout = () => {
        localStorage.removeItem('nexus_token');
        navigate('/');
    };

    const handleProfileClick = () => {
        setIsOpen(false);
        navigate('/profile');
    };

    const handleSyncClick = () => {
        setIsOpen(false);
        onSync();
    };

    const userInitial = userEmail ? userEmail[0].toUpperCase() : 'U';

    return (
        <div className="relative" ref={dropdownRef}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                onMouseEnter={() => setIsOpen(true)}
                className="flex items-center gap-2 glass-panel px-3 py-2 rounded-full hover:bg-white/10 transition-all cursor-pointer group"
            >
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-nexus-primary to-blue-500 flex items-center justify-center text-sm font-bold text-white">
                    {userInitial}
                </div>
                <ChevronDown className={`w-4 h-4 text-nexus-textMuted transition-transform ${isOpen ? 'rotate-180' : ''}`} />
            </button>

            {isOpen && (
                <div
                    className="absolute right-0 top-full mt-2 w-64 glass-panel rounded-xl border border-nexus-border shadow-xl overflow-hidden z-50"
                    onMouseLeave={() => setIsOpen(false)}
                >
                    {/* User Info */}
                    <div className="p-4 border-b border-nexus-border">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-nexus-primary to-blue-500 flex items-center justify-center text-lg font-bold text-white">
                                {userInitial}
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="text-sm font-semibold text-nexus-text truncate">{userEmail || 'User'}</p>
                                <p className="text-xs text-nexus-textMuted">Google Account</p>
                            </div>
                        </div>
                    </div>

                    {/* Menu Items */}
                    <div className="p-2">
                        <button
                            onClick={handleProfileClick}
                            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-nexus-text hover:bg-white/5 transition-colors text-left"
                        >
                            <User className="w-4 h-4 text-nexus-textMuted" />
                            <span className="text-sm">View Profile</span>
                        </button>
                        <button
                            onClick={handleProfileClick}
                            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-nexus-text hover:bg-white/5 transition-colors text-left"
                        >
                            <Settings className="w-4 h-4 text-nexus-textMuted" />
                            <span className="text-sm">Settings</span>
                        </button>
                        <button
                            onClick={handleSyncClick}
                            disabled={syncing}
                            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-nexus-text hover:bg-white/5 transition-colors text-left ${syncing ? 'opacity-50' : ''}`}
                        >
                            <RefreshCw className={`w-4 h-4 text-nexus-textMuted ${syncing ? 'animate-spin' : ''}`} />
                            <span className="text-sm">{syncing ? 'Syncing...' : 'Force Sync'}</span>
                        </button>
                    </div>

                    {/* Logout */}
                    <div className="p-2 border-t border-nexus-border">
                        <button
                            onClick={handleLogout}
                            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-red-400 hover:bg-red-500/10 transition-colors text-left"
                        >
                            <LogOut className="w-4 h-4" />
                            <span className="text-sm">Logout</span>
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
