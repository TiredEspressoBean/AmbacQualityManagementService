import { useEffect, useState } from "react";
import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    ResponsiveContainer,
    BarChart,
    Bar,
    Cell,
} from "recharts";
import {
    ChartContainer,
    ChartTooltip,
    ChartTooltipContent,
} from "@/components/ui/chart";
import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";

const chartConfig = {
    fpy: { label: "First Pass Yield", color: "hsl(var(--chart-1))" },
    count: { label: "Count", color: "hsl(var(--chart-2))" },
};

// Demo data - will be replaced with real API data
const kpis = [
    { label: "First Pass Yield", value: "94.2%", status: "good" },
    { label: "Active CAPAs", value: "8", status: "warn" },
    { label: "Open NCRs", value: "12", status: "ok" },
    { label: "Parts in WIP", value: "47", status: "ok" },
    { label: "Due Today", value: "5", status: "ok" },
];

// 30-day FPY trend
const fpyTrend = Array.from({ length: 30 }).map((_, i) => ({
    day: i + 1,
    fpy: 92 + Math.sin(i / 5) * 3 + (Math.random() - 0.5) * 2,
}));

// Defects by type (Pareto)
const defectsByType = [
    { type: "Dimensional", count: 18 },
    { type: "Scratch", count: 14 },
    { type: "Burr", count: 11 },
    { type: "Contamination", count: 7 },
    { type: "Other", count: 4 },
];

// Recent activity
const recentActivity = [
    { icon: "✅", text: "WO-1852: 25 parts completed" },
    { icon: "⚠️", text: "CAPA-2025-008 due tomorrow" },
    { icon: "🔧", text: "NCR-042: Rework in progress" },
    { icon: "✅", text: "Order ORD-2025-147 shipped" },
];

export default function BigScreenPage() {
    const [currentTime, setCurrentTime] = useState(new Date());

    // Update clock every minute
    useEffect(() => {
        const timer = setInterval(() => setCurrentTime(new Date()), 60000);
        return () => clearInterval(timer);
    }, []);

    return (
        <div className="h-screen w-screen overflow-hidden bg-background flex flex-col">
            {/* Header */}
            <header className="shrink-0 px-6 py-4 flex items-center justify-between border-b">
                <div>
                    <h1 className="text-4xl font-bold tracking-tight">Production Dashboard</h1>
                    <p className="text-lg text-muted-foreground">
                        Live performance overview
                    </p>
                </div>
                <div className="text-right">
                    <div className="text-3xl font-semibold tabular-nums">
                        {currentTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                    <div className="text-muted-foreground">
                        {currentTime.toLocaleDateString([], { weekday: 'long', month: 'short', day: 'numeric' })}
                    </div>
                </div>
            </header>

            {/* KPI Row */}
            <div className="shrink-0 px-6 py-4 grid grid-cols-5 gap-4">
                {kpis.map((kpi) => (
                    <Card key={kpi.label} className="text-center py-3">
                        <CardHeader className="py-1 px-2">
                            <CardTitle className="text-sm font-medium text-muted-foreground">
                                {kpi.label}
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="py-1 px-2">
                            <div
                                className={`text-4xl font-bold ${
                                    kpi.status === "good"
                                        ? "text-green-500"
                                        : kpi.status === "warn"
                                            ? "text-yellow-500"
                                            : "text-blue-500"
                                }`}
                            >
                                {kpi.value}
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>

            {/* Main content */}
            <div className="flex-1 min-h-0 px-6 pb-4 grid grid-cols-3 gap-4">
                {/* FPY Trend Chart - 2 columns */}
                <Card className="col-span-2 flex flex-col overflow-hidden">
                    <CardHeader className="shrink-0 py-3">
                        <CardTitle className="text-xl">First Pass Yield - 30 Day Trend</CardTitle>
                    </CardHeader>
                    <CardContent className="flex-1 min-h-0 pb-4">
                        <ChartContainer config={chartConfig} className="h-full w-full">
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart
                                    data={fpyTrend}
                                    margin={{ top: 10, right: 20, left: 0, bottom: 0 }}
                                >
                                    <defs>
                                        <linearGradient id="fpyGradient" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="var(--chart-1)" stopOpacity={0.4} />
                                            <stop offset="95%" stopColor="var(--chart-1)" stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid vertical={false} strokeDasharray="3 3" />
                                    <XAxis dataKey="day" axisLine={false} tickLine={false} />
                                    <YAxis domain={[85, 100]} axisLine={false} tickLine={false} width={35} tickFormatter={(v) => `${v}%`} />
                                    <Area
                                        type="monotone"
                                        dataKey="fpy"
                                        stroke="var(--chart-1)"
                                        strokeWidth={2}
                                        fill="url(#fpyGradient)"
                                    />
                                    <ChartTooltip content={<ChartTooltipContent formatter={(v) => `${Number(v).toFixed(1)}%`} />} />
                                </AreaChart>
                            </ResponsiveContainer>
                        </ChartContainer>
                    </CardContent>
                </Card>

                {/* Right column */}
                <div className="flex flex-col gap-4 min-h-0">
                    {/* Defects by Type */}
                    <Card className="flex-1 min-h-0 flex flex-col overflow-hidden">
                        <CardHeader className="shrink-0 py-3">
                            <CardTitle className="text-xl">Defects by Type (30 days)</CardTitle>
                        </CardHeader>
                        <CardContent className="flex-1 min-h-0 pb-2">
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart
                                    data={defectsByType}
                                    layout="vertical"
                                    margin={{ top: 0, right: 20, left: 0, bottom: 0 }}
                                >
                                    <CartesianGrid horizontal={false} strokeDasharray="3 3" />
                                    <XAxis type="number" axisLine={false} tickLine={false} />
                                    <YAxis type="category" dataKey="type" axisLine={false} tickLine={false} width={90} />
                                    <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                                        {defectsByType.map((_, index) => (
                                            <Cell key={index} fill={index === 0 ? "var(--chart-1)" : "var(--chart-2)"} />
                                        ))}
                                    </Bar>
                                    <ChartTooltip content={<ChartTooltipContent />} />
                                </BarChart>
                            </ResponsiveContainer>
                        </CardContent>
                    </Card>

                    {/* Recent Activity */}
                    <Card className="shrink-0">
                        <CardHeader className="py-3">
                            <CardTitle className="text-xl">Recent Activity</CardTitle>
                        </CardHeader>
                        <CardContent className="py-2">
                            <ul className="space-y-2">
                                {recentActivity.map((item, i) => (
                                    <li key={i} className="flex items-center gap-3 text-sm">
                                        <span className="text-xl">{item.icon}</span>
                                        <span>{item.text}</span>
                                    </li>
                                ))}
                            </ul>
                        </CardContent>
                    </Card>
                </div>
            </div>

            {/* Footer */}
            <footer className="shrink-0 px-6 py-2 border-t text-center text-muted-foreground text-sm">
                Data refreshes automatically • Press F11 for fullscreen
            </footer>
        </div>
    );
}
