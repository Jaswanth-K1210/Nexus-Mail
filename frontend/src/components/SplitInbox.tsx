import { MailThreadCard, type EmailThread } from './MailThreadCard';


export interface SplitInboxProps {
    inbox: EmailThread[];
}

export function SplitInbox({ inbox }: SplitInboxProps) {
    // Sort emails by priority score to feed the split logic
    const sorted = [...inbox].sort((a, b) => b.priorityScore - a.priorityScore);

    const priorityQueue = sorted.filter(t => t.priorityScore >= 50);
    const lowPriority = sorted.filter(t => t.priorityScore < 50);

    return (
        <div className="w-full flex-1 grid grid-cols-1 xl:grid-cols-2 gap-6 h-full overflow-hidden">

            {/* Column 1: Priority Inbox */}
            <div className="glass-panel w-full h-full flex flex-col overflow-hidden border-nexus-primary/20 shadow-[0_0_15px_rgba(177,158,239,0.05)] relative">
                <div className="p-4 border-b border-white/10 flex items-center justify-between sticky top-0 bg-black/40 backdrop-blur-xl z-10">
                    <h3 className="font-semibold text-nexus-primary flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-nexus-primary animate-pulse"></span>
                        Priority Inbox
                    </h3>
                    <span className="text-xs bg-white/10 px-2 py-1 rounded-md text-white/70">{priorityQueue.length} items</span>
                </div>
                <div className="p-4 overflow-y-auto custom-scrollbar flex flex-col gap-3 flex-1 pb-20">
                    {priorityQueue.map(thread => (
                        <MailThreadCard key={thread.id} thread={thread} onClick={() => console.log('Clicked', thread.id)} />
                    ))}
                    {priorityQueue.length === 0 && <span className="text-white/40 text-sm italic p-4 text-center block">Inbox Zero.</span>}
                </div>
                <div className="absolute bottom-0 w-full h-12 bg-gradient-to-t from-black/80 to-transparent pointer-events-none"></div>
            </div>

            {/* Column 2: Standard Queue (Newsletters / Transactional) */}
            <div className="glass-panel w-full h-full flex flex-col overflow-hidden opacity-90 transition-opacity border-white/5 relative">
                <div className="p-4 border-b border-white/10 flex items-center justify-between sticky top-0 bg-black/40 backdrop-blur-xl z-10">
                    <h3 className="font-medium text-white/70 flex items-center gap-2">
                        Other Inbox
                    </h3>
                    <span className="text-xs bg-white/10 px-2 py-1 rounded-md text-white/40">{lowPriority.length} items</span>
                </div>
                <div className="p-4 overflow-y-auto custom-scrollbar flex flex-col gap-3 flex-1 pb-20">
                    {lowPriority.map(thread => (
                        <MailThreadCard key={thread.id} thread={thread} onClick={() => console.log('Clicked', thread.id)} />
                    ))}
                    {lowPriority.length === 0 && <span className="text-white/40 text-sm italic p-4 text-center block">Clear!</span>}
                </div>
                <div className="absolute bottom-0 w-full h-12 bg-gradient-to-t from-black/80 to-transparent pointer-events-none"></div>
            </div>

        </div>
    );
}
