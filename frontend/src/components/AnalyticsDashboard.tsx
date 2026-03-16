import { useEffect, useState } from 'react';
import { PieChart, Pie, Cell, Tooltip, BarChart, Bar, XAxis, YAxis, ResponsiveContainer } from 'recharts';
import { TrendingUp, BarChart2, Lightbulb } from 'lucide-react';
import api from '../api';
import { getRoleLanes } from '../config/roleCategories';

const COLORS = ['#A288E3', '#4ea8de', '#43AA8B', '#F3722C', '#F94144', '#FFBB28', '#0088FE', '#00C49F', '#8ecae6', '#e76f51'];

// Role-specific smart tips
const ROLE_TIPS: Record<string, string[]> = {
    student: ['Check the Academics tab — exams & deadlines are highlighted.', 'Internship offers land in Career. Set up a notification so you never miss one.', 'Enable auto-archive for campus newsletters to keep your inbox clean.'],
    working_professional: ['Approval emails auto-land in Work. Resolve them quickly to un-block teammates.', 'Client emails are priority-scored separately from internal updates.', 'Use "Draft a Reply" on deadline reminders to reply instantly.'],
    founder: ['Investor emails are marked ACTION REQUIRED — never let them sit.', 'Cold outreach is automatically separated into its own lane.', 'Set up weekly reprocessing so classifications improve as you grow.'],
    influencer: ['Brand deal emails are highlighted in the Brand Deals lane.', 'Payment verification is auto-flagged when an invoice arrives.', 'Platform policy updates are auto-separated from fan messages.'],
    freelancer: ['Contracts and invoices auto-land in Payments — flag overdue ones.', 'New project inquiries are isolated in Projects so you never miss a lead.', 'Revision requests are tracked separately from client check-ins.'],
    business_owner: ['Vendor emails are sorted away from customer orders.', 'Finance tab keeps GST, bank statements, and accounting emails together.', 'Staff HR emails never mix with supplier communications.'],
    healthcare: ['Lab results are always flagged ACTION REQUIRED.', 'Drug recall emails from pharma are auto-marked REVIEW URGENT.', 'CME events are collected in one lane so deadlines don\'t slip.'],
    legal: ['Court notices are always flagged with Review Deadline.', 'Client communication is isolated from opposing counsel emails.', 'Use the Billing tab to track unpaid client invoices.'],
    educator: ['Student queries and grade-related emails are in Students tab.', 'Admin directives are always surfaced with high priority.', 'Conference submissions are tracked in the Research lane.'],
    trades: ['Work orders are flagged urgent by default — respond same-day.', 'Parts procurement emails are grouped away from client site communication.', 'Safety compliance emails are always high priority — don\'t ignore them.'],
    real_estate: ['Listing inquiries trigger ACTION REQUIRED — respond within 1 hour.', 'Closing documents are flagged in Deals with a Flag Closing action.', 'MLS alerts are separated so you always see new listings first.'],
    nonprofit: ['Grant application emails are marked Review Deadline automatically.', 'Donor communication is isolated and always prioritized.', 'Government compliance emails are flagged urgent regardless of source.'],
    finance: ['Tax filing emails are flagged Review Deadline with due date context.', 'Audit requests are always marked Action Required.', 'Payroll confirmation emails land in Finance tab for easy tracking.'],
    sales_marketing: ['Inbound leads always trigger ACTION REQUIRED — respond fast.', 'Campaign reports land in a dedicated lane away from deal updates.', 'CRM notifications are isolated from real client communication.'],
};

export function AnalyticsDashboard({ roleKey }: { roleKey?: string }) {
    const [categories, setCategories] = useState<{ name: string; value: number }[]>([]);
    const [volume, setVolume] = useState<{ date: string; count: number }[]>([]);
    const [loading, setLoading] = useState(true);
    const [activeTip, setActiveTip] = useState(0);

    const tips = roleKey ? (ROLE_TIPS[roleKey] || []) : [];
    const roleLanes = roleKey ? getRoleLanes(roleKey) : null;

    // Role-aware category display names
    const categoryLabel = (raw: string) => {
        if (!roleLanes) return raw;
        for (const lane of roleLanes) {
            if (lane.categories.includes(raw)) return lane.label;
        }
        return raw.replace(/_/g, ' ');
    };

    useEffect(() => {
        async function fetchAnalytics() {
            try {
                const [catRes, volRes] = await Promise.all([
                    api.get('/analytics/categories'),
                    api.get('/analytics/volume?days=14'),
                ]);
                setCategories(
                    catRes.data.data.map((item: { category?: string; count: number }) => ({
                        name: categoryLabel(item.category || 'uncategorized'),
                        value: item.count,
                    })),
                );
                setVolume(
                    volRes.data.data.map((item: { date?: string; _id?: string; count: number }) => ({
                        date: item.date || item._id,
                        count: item.count,
                    })),
                );
            } catch (err) {
                console.error('Failed to fetch analytics:', err);
            } finally {
                setLoading(false);
            }
        }
        fetchAnalytics();
    }, [roleKey]);

    if (loading) return <div className="p-4 text-gray-400 text-sm">Loading charts...</div>;

    return (
        <div className="flex flex-col gap-6 mt-8">
            {/* Smart Tips banner — only for roles with tips */}
            {tips.length > 0 && (
                <div className="glass-panel p-4 border border-nexus-primary/20 bg-nexus-primary/5 flex items-start gap-3">
                    <Lightbulb className="w-4 h-4 text-nexus-primary shrink-0 mt-0.5" />
                    <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold text-nexus-primary uppercase tracking-wide mb-1">Smart Tip for your role</p>
                        <p className="text-sm text-nexus-text leading-relaxed">{tips[activeTip]}</p>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                        {tips.map((_, i) => (
                            <button
                                key={i}
                                onClick={() => setActiveTip(i)}
                                className={`w-1.5 h-1.5 rounded-full transition-all ${i === activeTip ? 'bg-nexus-primary' : 'bg-white/20 hover:bg-white/40'}`}
                            />
                        ))}
                    </div>
                </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Category breakdown — role-aware labels */}
                <div className="glass-panel p-6">
                    <h3 className="text-sm font-semibold mb-4 text-nexus-text flex items-center gap-2">
                        <BarChart2 className="w-4 h-4 text-nexus-primary" />
                        {roleKey ? 'Your Inbox by Category' : 'Category Breakdown'}
                    </h3>
                    <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={categories}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={55}
                                    outerRadius={80}
                                    paddingAngle={4}
                                    dataKey="value"
                                >
                                    {categories.map((_, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip
                                    contentStyle={{ backgroundColor: 'rgba(10,10,20,0.9)', border: '1px solid rgba(177,158,239,0.2)', borderRadius: '8px', color: '#fff', fontSize: '12px' }}
                                    itemStyle={{ color: '#fff' }}
                                />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                    {/* Legend */}
                    <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1.5">
                        {categories.slice(0, 6).map((cat, idx) => (
                            <div key={cat.name} className="flex items-center gap-1.5 text-[10px] text-nexus-textMuted">
                                <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: COLORS[idx % COLORS.length] }} />
                                <span className="capitalize">{cat.name}</span>
                                <span className="font-mono text-nexus-text/60">{cat.value}</span>
                            </div>
                        ))}
                    </div>
                </div>

                {/* daily volume */}
                <div className="glass-panel p-6">
                    <h3 className="text-sm font-semibold mb-4 text-nexus-text flex items-center gap-2">
                        <TrendingUp className="w-4 h-4 text-blue-400" />
                        Daily Volume (14 Days)
                    </h3>
                    <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={volume}>
                                <XAxis dataKey="date" stroke="#444" tick={{ fill: '#666', fontSize: 10 }} />
                                <YAxis stroke="#444" tick={{ fill: '#666', fontSize: 10 }} />
                                <Tooltip
                                    cursor={{ fill: 'rgba(177,158,239,0.05)' }}
                                    contentStyle={{ backgroundColor: 'rgba(10,10,20,0.9)', border: '1px solid rgba(177,158,239,0.2)', borderRadius: '8px', color: '#fff', fontSize: '12px' }}
                                />
                                <Bar dataKey="count" fill="#A288E3" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>
        </div>
    );
}
