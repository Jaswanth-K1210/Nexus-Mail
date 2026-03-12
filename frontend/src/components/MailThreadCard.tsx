import { motion } from 'framer-motion';
import { Brain, ShieldAlert } from 'lucide-react';
import clsx from 'clsx';

export type EmailThread = {
    id: string;
    sender: string;
    subject: string;
    snippet: string;
    isUnread: boolean;
    priorityScore: number;
    category: string;
    hasAiDraft: boolean;
    aiConfidence?: number;
    suggestedAction?: string;
    riskFlags?: string[];
};

interface MailThreadCardProps {
    thread: EmailThread;
    onClick: () => void;
    isSelected?: boolean;
}

export function MailThreadCard({ thread, onClick, isSelected = false }: MailThreadCardProps) {
    // Determine color based on priority score
    const getScoreColor = (score: number) => {
        if (score >= 80) return 'text-nexus-primary bg-nexus-primary/10 border-nexus-primary/30';
        if (score >= 50) return 'text-blue-500 bg-blue-500/10 border-blue-500/30';
        return 'text-nexus-textMuted bg-nexus-card border-nexus-border';
    };

    const getActionColor = (action?: string) => {
        switch (action) {
            case 'ACTION REQUIRED': return 'text-red-400 border-red-500/20 bg-red-500/10';
            case 'REVIEW ONLY': return 'text-amber-400 border-amber-500/20 bg-amber-500/10';
            case 'LOW RELEVANCE': return 'text-gray-400 border-gray-500/20 bg-gray-500/10';
            case 'AUTO-ARCHIVE': return 'text-nexus-textMuted border-nexus-border bg-black/40';
            default: return 'hidden';
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            whileHover={!isSelected ? { scale: 1.01, transition: { duration: 0.2 } } : undefined}
            onClick={onClick}
            className={clsx(
                "cursor-pointer group relative p-4 rounded-xl transition-all duration-300",
                "bg-nexus-card border shadow-sm backdrop-blur-md",
                thread.isUnread ? "border-nexus-primary/30 bg-nexus-cardHover" : "border-nexus-border",
                isSelected
                    ? "border-nexus-primary shadow-[0_0_15px_rgba(177,158,239,0.3)] bg-nexus-primary/10 ring-1 ring-nexus-primary z-10"
                    : "hover:bg-nexus-cardHover hover:border-nexus-primary/30 hover:shadow-glass"
            )}
        >
            {/* Read indicator glow */}
            {thread.isUnread && (
                <div className="absolute top-1/2 -left-px -translate-y-1/2 w-1 h-8 bg-nexus-primary rounded-r-md shadow-[0_0_10px_rgba(177,158,239,0.8)]"></div>
            )}

            <div className="flex justify-between items-start mb-2">
                <div className="flex items-center gap-3">
                    {/* Avatar Placeholder */}
                    <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-nexus-card to-nexus-cardHover border border-nexus-border flex items-center justify-center font-semibold text-sm shadow-inner text-nexus-text">
                        {thread.sender.charAt(0).toUpperCase()}
                    </div>
                    <div>
                        <h4 className={clsx("font-medium text-sm", thread.isUnread ? "text-nexus-text font-semibold" : "text-nexus-textMuted")}>
                            {thread.sender}
                        </h4>
                        <p className={clsx("text-xs truncate max-w-[200px] sm:max-w-xs", thread.isUnread ? "text-nexus-text font-medium" : "text-nexus-textMuted opacity-80")}>
                            {thread.subject}
                        </p>
                    </div>
                </div>

                {/* Priority & Action Badges */}
                <div className="flex flex-col items-end gap-1.5">
                    <div className="flex items-center gap-2 flex-wrap justify-end">
                        {thread.suggestedAction && thread.suggestedAction !== 'REVIEW ONLY' && (
                            <div className={clsx("text-[9px] font-bold tracking-wider px-2 py-0.5 rounded-md border", getActionColor(thread.suggestedAction))}>
                                {thread.suggestedAction}
                            </div>
                        )}
                        {thread.riskFlags && thread.riskFlags.length > 0 && (
                            <div className="text-[10px] text-red-400 bg-red-500/10 border border-red-500/30 px-2 py-0.5 rounded-md flex items-center gap-1 shadow-[0_0_10px_rgba(239,68,68,0.2)]" title="Security & Risk Warning">
                                <ShieldAlert className="w-3 h-3 flex-shrink-0" /> RISK
                            </div>
                        )}
                        <div className={clsx("text-xs font-mono px-2 py-0.5 rounded-md border flex items-center gap-1", getScoreColor(thread.priorityScore))}>
                            <TrendingUpIcon className="w-3 h-3" />
                            {thread.priorityScore}
                        </div>
                    </div>
                </div>
            </div>

            <p className="text-nexus-textMuted text-xs line-clamp-2 pl-13 ml-13">
                {thread.snippet}
            </p>

            {/* AI Draft Status */}
            {thread.hasAiDraft && (
                <div className="mt-3 ml-13 flex items-center gap-2">
                    <div className={clsx(
                        "text-[10px] uppercase tracking-wider font-semibold px-2 py-1 rounded border flex items-center gap-1.5 w-max",
                        (thread.aiConfidence || 0) > 85 ? "bg-green-500/10 text-green-400 border-green-500/20" : "bg-nexus-primary/10 text-nexus-primary border-nexus-primary/20"
                    )}>
                        <Brain className="w-3 h-3" />
                        Draft Ready • {(thread.aiConfidence || 0)}% Conf
                    </div>
                </div>
            )}
        </motion.div>
    );
}

function TrendingUpIcon(props: React.SVGProps<SVGSVGElement>) {
    return (
        <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" />
            <polyline points="16 7 22 7 22 13" />
        </svg>
    );
}
