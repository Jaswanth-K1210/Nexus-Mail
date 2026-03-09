import { useEffect, useState } from 'react';
import { PieChart, Pie, Cell, Tooltip, BarChart, Bar, XAxis, YAxis, ResponsiveContainer } from 'recharts';
import api from '../api';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#A288E3', '#F94144', '#43AA8B', '#F3722C'];

export function AnalyticsDashboard() {
    const [categories, setCategories] = useState<{ name: string, value: number }[]>([]);
    const [volume, setVolume] = useState<{ date: string, count: number }[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function fetchAnalytics() {
            try {
                const [catRes, volRes] = await Promise.all([
                    api.get('/analytics/categories'),
                    api.get('/analytics/volume?days=14')
                ]);

                setCategories(catRes.data.data.map((item: { category?: string, count: number }) => ({
                    name: item.category || 'Uncategorized',
                    value: item.count
                })));

                setVolume(volRes.data.data.map((item: { date?: string, _id?: string, count: number }) => ({
                    date: item.date || item._id,
                    count: item.count
                })));
            } catch (err) {
                console.error("Failed to fetch analytics:", err);
            } finally {
                setLoading(false);
            }
        }
        fetchAnalytics();
    }, []);

    if (loading) return <div className="p-4 text-gray-400">Loading charts...</div>;

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8">
            <div className="glass-panel p-6">
                <h3 className="text-lg font-medium mb-4 text-white">Category Breakdown</h3>
                <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                            <Pie
                                data={categories}
                                cx="50%"
                                cy="50%"
                                innerRadius={60}
                                outerRadius={80}
                                fill="#8884d8"
                                paddingAngle={5}
                                dataKey="value"
                            >
                                {categories.map((_, index) => (
                                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                ))}
                            </Pie>
                            <Tooltip
                                contentStyle={{ backgroundColor: 'rgba(0,0,0,0.8)', border: 'none', borderRadius: '8px', color: '#fff' }}
                                itemStyle={{ color: '#fff' }}
                            />
                        </PieChart>
                    </ResponsiveContainer>
                </div>
            </div>

            <div className="glass-panel p-6">
                <h3 className="text-lg font-medium mb-4 text-white">Daily Volume (14 Days)</h3>
                <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={volume}>
                            <XAxis dataKey="date" stroke="#666" tick={{ fill: '#888' }} />
                            <YAxis stroke="#666" tick={{ fill: '#888' }} />
                            <Tooltip
                                cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                                contentStyle={{ backgroundColor: 'rgba(0,0,0,0.8)', border: 'none', borderRadius: '8px', color: '#fff' }}
                            />
                            <Bar dataKey="count" fill="#4ea8de" radius={[4, 4, 0, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>
        </div>
    );
}
