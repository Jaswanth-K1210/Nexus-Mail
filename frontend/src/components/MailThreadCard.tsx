import { motion } from 'framer-motion';
import { Brain } from 'lucide-react';
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
};

interface MailThreadCardProps {
    thread: EmailThread;
    onClick: () => void;
}

export function MailThreadCard({ thread, onClick }: MailThreadCardProps) {
    // Determine color based on priority score
    const getScoreColor = (score: number) => {
        if (score >= 80) return 'text-nexus-primary bg-nexus-primary/10 border-nexus-primary/30';
        if (score >= 50) return 'text-blue-400 bg-blue-400/10 border-blue-400/30';
        return 'text-gray-400 bg-white/5 border-white/10';
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            whileHover={{ scale: 1.01, transition: { duration: 0.2 } }}
            onClick={onClick}
            className={clsx(
                "cursor-pointer group relative p-4 rounded-xl transition-all duration-300",
                "bg-white/5 border shadow-sm backdrop-blur-md",
                thread.isUnread ? "border-white/20 bg-white/10" : "border-white/5",
                "hover:bg-white/10 hover:border-nexus-primary/30 hover:shadow-glass"
            )}
        >
            {/* Read indicator glow */}
            {thread.isUnread && (
                <div className="absolute top-1/2 -left-px -translate-y-1/2 w-1 h-8 bg-nexus-primary rounded-r-md shadow-[0_0_10px_rgba(177,158,239,0.8)]"></div>
            )}

            <div className="flex justify-between items-start mb-2">
                <div className="flex items-center gap-3">
                    {/* Avatar Placeholder */}
                    <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-nexus-card to-nexus-cardHover border border-white/10 flex items-center justify-center font-semibold text-sm shadow-inner text-white/80">
                        {thread.sender.charAt(0).toUpperCase()}
                    </div>
                    <div>
                        <h4 className={clsx("font-medium text-sm", thread.isUnread ? "text-white" : "text-white/70")}>
                            {thread.sender}
                        </h4>
                        <p className={clsx("text-xs truncate max-w-[200px] sm:max-w-xs", thread.isUnread ? "text-white/90 font-medium" : "text-white/50")}>
                            {thread.subject}
                        </p>
                    </div>
                </div>

                {/* Priority Badge */}
                <div className={clsx("flex flex-col items-end gap-1.5")}>
                    <div className={clsx("text-xs font-mono px-2 py-0.5 rounded-md border flex items-center gap-1", getScoreColor(thread.priorityScore))}>
                        <TrendingUpIcon className="w-3 h-3" />
                        {thread.priorityScore}
                    </div>

                </div>
            </div>

            <p className="text-white/40 text-xs line-clamp-2 pl-13 ml-13">
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
