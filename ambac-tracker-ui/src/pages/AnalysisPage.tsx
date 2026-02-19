import { useMemo, useState } from "react";
import {
    Area,
    AreaChart,
    CartesianGrid,
    ReferenceLine,
    XAxis,
    YAxis,
} from "recharts";
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
    CheckCircle2,
    AlertTriangle,
    AlertCircle,
    TrendingUp,
    TrendingDown,
    Minus,
    ArrowRight,
    LineChart,
    FileText,
    Package,
    Clock,
} from "lucide-react";
import { Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { DateRangeToggle, rangeToDays, type DateRange } from "@/components/analytics";

// Hooks
import { useDashboardKpis } from "@/hooks/useDashboardKpis";
import { useFpyTrend } from "@/hooks/useFpyTrend";
import { useNeedsAttention } from "@/hooks/useNeedsAttention";
import { useQualityRates } from "@/hooks/useQualityRates";
import { useDefectPareto } from "@/hooks/useDefectPareto";

// ---------- Types ----------
type FpyPoint = { label: string; fpy: number | null; ts: number };

type OverallStatus = "good" | "warning" | "critical";

// ---------- Chart config ----------
const fpyChartConfig = {
    fpy: { label: "First Pass Yield %", color: "var(--chart-1)" },
} as const;

// ---------- Status determination ----------
function determineOverallStatus(
    attentionCount: number,
    overdueCapas: number,
    fpy: number,
    fypTarget: number
): { status: OverallStatus; message: string } {
    if (overdueCapas > 3 || attentionCount > 5) {
        return { status: "critical", message: "Immediate attention required" };
    }
    if (overdueCapas > 0 || attentionCount > 2 || fpy < fypTarget - 5) {
        return { status: "warning", message: "Some issues need attention" };
    }
    return { status: "good", message: "Quality on track" };
}

// ---------- Trend calculation ----------
function calculateTrend(data: FpyPoint[]): { direction: "up" | "down" | "flat"; change: number } {
    if (data.length < 7) return { direction: "flat", change: 0 };

    const recent = data.slice(-7);
    const earlier = data.slice(-14, -7);

    if (earlier.length === 0) return { direction: "flat", change: 0 };

    const recentAvg = recent.filter(d => d.fpy !== null).reduce((s, d) => s + (d.fpy || 0), 0) / recent.length;
    const earlierAvg = earlier.filter(d => d.fpy !== null).reduce((s, d) => s + (d.fpy || 0), 0) / earlier.length;

    const change = Math.round((recentAvg - earlierAvg) * 10) / 10;

    if (Math.abs(change) < 1) return { direction: "flat", change: 0 };
    return { direction: change > 0 ? "up" : "down", change: Math.abs(change) };
}

// ---------- Components ----------
function StatusBanner({ status, message, itemCount }: { status: OverallStatus; message: string; itemCount: number }) {
    const config = {
        good: {
            bg: "bg-green-500/10 border-green-500/30",
            icon: CheckCircle2,
            iconColor: "text-green-600",
            textColor: "text-green-700",
        },
        warning: {
            bg: "bg-amber-500/10 border-amber-500/30",
            icon: AlertTriangle,
            iconColor: "text-amber-600",
            textColor: "text-amber-700",
        },
        critical: {
            bg: "bg-red-500/10 border-red-500/30",
            icon: AlertCircle,
            iconColor: "text-red-600",
            textColor: "text-red-700",
        },
    };

    const { bg, icon: Icon, iconColor, textColor } = config[status];

    return (
        <div className={cn("rounded-lg border p-4 flex items-center gap-4", bg)}>
            <Icon className={cn("h-8 w-8", iconColor)} />
            <div className="flex-1">
                <p className={cn("text-lg font-semibold", textColor)}>{message}</p>
                <p className="text-sm text-muted-foreground">
                    {status === "good"
                        ? "All metrics within targets"
                        : `${itemCount} item${itemCount !== 1 ? 's' : ''} requiring attention`}
                </p>
            </div>
            {status !== "good" && (
                <Button variant="outline" size="sm" asChild>
                    <a href="#attention">View Issues</a>
                </Button>
            )}
        </div>
    );
}

interface MetricCardProps {
    label: string;
    value: string | number;
    subtext: string;
    trend?: { direction: "up" | "down" | "flat"; change: number; goodDirection?: "up" | "down" };
    status?: "good" | "warning" | "critical" | "neutral";
    link?: string;
}

function MetricCard({ label, value, subtext, trend, status = "neutral", link }: MetricCardProps) {
    const statusStyles = {
        good: "border-green-500/40 bg-green-500/5",
        warning: "border-amber-500/40 bg-amber-500/5",
        critical: "border-red-500/40 bg-red-500/5",
        neutral: "border-muted/40",
    };

    const valueStyles = {
        good: "text-green-600",
        warning: "text-amber-600",
        critical: "text-red-600",
        neutral: "text-foreground",
    };

    const TrendIcon = trend?.direction === "up" ? TrendingUp : trend?.direction === "down" ? TrendingDown : Minus;

    // Determine if trend is positive or negative based on context
    const trendIsGood = trend && (
        (trend.goodDirection === "up" && trend.direction === "up") ||
        (trend.goodDirection === "down" && trend.direction === "down") ||
        trend.direction === "flat"
    );

    const content = (
        <Card className={cn(statusStyles[status], "hover:shadow-sm transition-all", link && "cursor-pointer")}>
            <CardContent className="p-4">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{label}</p>
                <div className="flex items-baseline gap-2 mt-1">
                    <span className={cn("text-3xl font-bold tabular-nums", valueStyles[status])}>
                        {value}
                    </span>
                    {trend && trend.direction !== "flat" && (
                        <span className={cn(
                            "flex items-center text-xs font-medium",
                            trendIsGood ? "text-green-600" : "text-red-600"
                        )}>
                            <TrendIcon className="h-3 w-3 mr-0.5" />
                            {trend.change}%
                        </span>
                    )}
                </div>
                <p className="text-xs text-muted-foreground mt-1">{subtext}</p>
            </CardContent>
        </Card>
    );

    if (link) {
        return <Link to={link} className="block">{content}</Link>;
    }
    return content;
}

function AttentionItem({
    severity,
    message,
    count,
    link
}: {
    severity: "critical" | "high" | "medium" | "low";
    message: string;
    count: number;
    link: string;
}) {
    const styles = {
        critical: "bg-red-500/10 border-red-500/30 text-red-700",
        high: "bg-amber-500/10 border-amber-500/30 text-amber-700",
        medium: "bg-yellow-500/10 border-yellow-500/30 text-yellow-700",
        low: "bg-blue-500/10 border-blue-500/30 text-blue-700",
    };

    return (
        <Link to={link} className="block">
            <div className={cn("rounded-lg border p-3 flex items-center gap-3 hover:opacity-80 transition-opacity", styles[severity])}>
                <div className="flex-1">
                    <p className="font-medium text-sm">{message}</p>
                </div>
                <span className="font-bold text-lg tabular-nums">{count}</span>
                <ArrowRight className="h-4 w-4 opacity-50" />
            </div>
        </Link>
    );
}

// ---------- Main Component ----------
export default function AnalysisPage() {
    // Date range state for trend chart
    const [dateRange, setDateRange] = useState<DateRange>("30d");
    const days = rangeToDays(dateRange);

    // API Hooks
    const { data: kpisData, isLoading: _isLoadingKpis } = useDashboardKpis();
    const { data: fpyTrendData, isLoading: isLoadingFpy } = useFpyTrend({ days });
    const { data: attentionData } = useNeedsAttention();
    const { data: qualityRates } = useQualityRates({ days });
    const { data: paretoData, isLoading: isLoadingPareto } = useDefectPareto({ days, limit: 5 });

    // Transform FPY data
    const fpyData = useMemo((): FpyPoint[] => {
        if (!fpyTrendData?.data) return [];
        return fpyTrendData.data.map((d) => ({
            label: d.label,
            fpy: d.fpy,
            ts: d.ts,
        }));
    }, [fpyTrendData]);

    // Calculate metrics
    const currentFpy = kpisData?.current_fpy ?? 0;
    const fpyTarget = 95;
    const fpyTrend = useMemo(() => calculateTrend(fpyData), [fpyData]);
    const avgFpy = fpyTrendData?.average ?? 0;
    const totalInspections = fpyTrendData?.total_inspections ?? 0;

    // Quality rates
    const scrapRate = qualityRates?.scrap_rate ?? 0;
    const reworkRate = qualityRates?.rework_rate ?? 0;

    const openIssues = (kpisData?.open_ncrs ?? 0) + (kpisData?.parts_in_quarantine ?? 0);
    const activeCapas = kpisData?.active_capas ?? 0;
    const overdueCapas = kpisData?.overdue_capas ?? 0;

    // Attention items
    const attentionItems = attentionData?.data ?? [];

    // Top defects for mini Pareto
    const topDefects = paretoData?.data ?? [];

    // Overall status
    const { status: overallStatus, message: statusMessage } = useMemo(() =>
        determineOverallStatus(attentionItems.length, overdueCapas, currentFpy, fpyTarget),
        [attentionItems.length, overdueCapas, currentFpy]
    );

    // Determine metric statuses
    const fpyStatus = currentFpy >= fpyTarget ? "good" : currentFpy >= fpyTarget - 5 ? "warning" : "critical";
    const issuesStatus = openIssues === 0 ? "good" : openIssues < 50 ? "neutral" : openIssues < 100 ? "warning" : "critical";
    const overdueStatus = overdueCapas === 0 ? "good" : overdueCapas < 3 ? "warning" : "critical";
    const scrapStatus = scrapRate <= 2 ? "good" : scrapRate <= 5 ? "warning" : "critical";
    const reworkStatus = reworkRate <= 5 ? "good" : reworkRate <= 10 ? "warning" : "critical";

    return (
        <div className="container mx-auto p-5 space-y-6 max-w-6xl">
            {/* Header */}
            <div>
                <h1 className="text-2xl font-semibold tracking-tight">Quality Dashboard</h1>
                <p className="text-sm text-muted-foreground">
                    Real-time overview of quality performance
                </p>
            </div>

            {/* Overall Status Banner */}
            <StatusBanner
                status={overallStatus}
                message={statusMessage}
                itemCount={attentionItems.length}
            />

            {/* Key Metrics - 6 cards */}
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                <MetricCard
                    label="First Pass Yield"
                    value={`${currentFpy}%`}
                    subtext={`Target: ${fpyTarget}%`}
                    trend={{ ...fpyTrend, goodDirection: "up" }}
                    status={fpyStatus}
                    link="/spc"
                />
                <MetricCard
                    label="Scrap Rate"
                    value={`${scrapRate.toFixed(1)}%`}
                    subtext="Parts scrapped"
                    status={scrapStatus}
                    link="/quality/ncrs"
                />
                <MetricCard
                    label="Rework Rate"
                    value={`${reworkRate.toFixed(1)}%`}
                    subtext="Parts reworked"
                    status={reworkStatus}
                    link="/quality/ncrs"
                />
                <MetricCard
                    label="Open Issues"
                    value={openIssues}
                    subtext="NCRs + Quarantine"
                    status={issuesStatus}
                    link="/production/dispositions"
                />
                <MetricCard
                    label="Active CAPAs"
                    value={activeCapas}
                    subtext="In progress"
                    status="neutral"
                    link="/quality/capas"
                />
                <MetricCard
                    label="Overdue"
                    value={overdueCapas}
                    subtext="Past due date"
                    status={overdueStatus}
                    link="/quality/capas"
                />
            </div>

            {/* Two Column Layout: Chart + Attention */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* FPY Trend - 2 columns */}
                <Card className="lg:col-span-2 border-muted/40">
                    <CardHeader className="pb-2">
                        <div className="flex items-center justify-between">
                            <div>
                                <CardTitle className="text-base">FPY Trend</CardTitle>
                                <p className="text-xs text-muted-foreground">
                                    Avg: {avgFpy.toFixed(1)}% • {totalInspections.toLocaleString()} inspections
                                </p>
                            </div>
                            <div className="flex items-center gap-2">
                                <DateRangeToggle value={dateRange} onChange={setDateRange} />
                                <Button variant="ghost" size="sm" asChild>
                                    <Link to="/spc">
                                        <LineChart className="h-4 w-4 mr-2" />
                                        SPC
                                    </Link>
                                </Button>
                            </div>
                        </div>
                    </CardHeader>
                    <CardContent>
                        {isLoadingFpy ? (
                            <div className="h-[200px] flex items-center justify-center text-muted-foreground">
                                Loading...
                            </div>
                        ) : (
                            <ChartContainer className="h-[200px] w-full" config={fpyChartConfig}>
                                <AreaChart data={fpyData} margin={{ left: 0, right: 0, top: 8, bottom: 0 }}>
                                    <defs>
                                        <linearGradient id="fpyGradient" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="var(--chart-1)" stopOpacity={0.3} />
                                            <stop offset="95%" stopColor="var(--chart-1)" stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                    <XAxis
                                        dataKey="label"
                                        tickLine={false}
                                        axisLine={false}
                                        tick={{ fontSize: 10 }}
                                        interval="preserveStartEnd"
                                    />
                                    <YAxis
                                        width={35}
                                        domain={[
                                            (dataMin: number) => Math.max(0, Math.floor(dataMin - 5)),
                                            100
                                        ]}
                                        tickLine={false}
                                        axisLine={false}
                                        tick={{ fontSize: 10 }}
                                        tickFormatter={(v) => `${v}%`}
                                    />
                                    <ChartTooltip
                                        content={<ChartTooltipContent formatter={(value) => `${value}%`} />}
                                    />
                                    {/* Target line */}
                                    <ReferenceLine
                                        y={fpyTarget}
                                        stroke="var(--chart-4)"
                                        strokeDasharray="5 5"
                                        label={{ value: "Target", position: "right", fontSize: 10, fill: "var(--chart-4)" }}
                                    />
                                    {/* Average line */}
                                    <ReferenceLine
                                        y={avgFpy}
                                        stroke="var(--chart-3)"
                                        strokeDasharray="3 3"
                                        strokeOpacity={0.7}
                                    />
                                    <Area
                                        dataKey="fpy"
                                        type="monotone"
                                        stroke="var(--chart-1)"
                                        fill="url(#fpyGradient)"
                                        strokeWidth={2}
                                    />
                                </AreaChart>
                            </ChartContainer>
                        )}
                    </CardContent>
                </Card>

                {/* Attention Panel - 1 column */}
                <Card className="border-muted/40" id="attention">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-base flex items-center gap-2">
                            {attentionItems.length > 0 ? (
                                <AlertTriangle className="h-4 w-4 text-amber-500" />
                            ) : (
                                <CheckCircle2 className="h-4 w-4 text-green-500" />
                            )}
                            Needs Attention
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                        {attentionItems.length > 0 ? (
                            attentionItems.slice(0, 5).map((item, i) => (
                                <AttentionItem
                                    key={i}
                                    severity={item.severity}
                                    message={item.message}
                                    count={item.count}
                                    link={item.link}
                                />
                            ))
                        ) : (
                            <div className="text-center py-6">
                                <CheckCircle2 className="h-10 w-10 text-green-500 mx-auto mb-2" />
                                <p className="font-medium text-green-700">All Clear</p>
                                <p className="text-xs text-muted-foreground">No urgent issues</p>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* Top Defects - Mini Pareto */}
            <Card className="border-muted/40">
                <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                        <div>
                            <CardTitle className="text-base">Top Defects</CardTitle>
                            <p className="text-xs text-muted-foreground">
                                {paretoData?.total ?? 0} total defects in {days}d
                            </p>
                        </div>
                        <Button variant="ghost" size="sm" asChild>
                            <Link to="/quality/defects">
                                <AlertTriangle className="h-4 w-4 mr-2" />
                                Full Analysis
                            </Link>
                        </Button>
                    </div>
                </CardHeader>
                <CardContent>
                    {isLoadingPareto ? (
                        <div className="h-[140px] flex items-center justify-center text-muted-foreground">
                            Loading...
                        </div>
                    ) : topDefects.length > 0 ? (
                        <div className="space-y-2">
                            {topDefects.map((defect, i) => {
                                const maxCount = topDefects[0]?.count || 1;
                                const percentage = (defect.count / maxCount) * 100;
                                return (
                                    <div key={i} className="flex items-center gap-3">
                                        <span className="text-xs text-muted-foreground w-28 truncate" title={defect.errorType}>
                                            {defect.errorType}
                                        </span>
                                        <div className="flex-1 h-5 bg-muted/30 rounded overflow-hidden">
                                            <div
                                                className="h-full bg-chart-2 rounded"
                                                style={{ width: `${percentage}%` }}
                                            />
                                        </div>
                                        <span className="text-xs font-mono font-medium w-8 text-right">
                                            {defect.count}
                                        </span>
                                    </div>
                                );
                            })}
                        </div>
                    ) : (
                        <div className="h-[140px] flex items-center justify-center text-muted-foreground">
                            <div className="text-center">
                                <CheckCircle2 className="h-8 w-8 text-green-500 mx-auto mb-2" />
                                <p className="text-sm">No defects recorded</p>
                            </div>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Quick Links - Minimal */}
            <div className="flex flex-wrap gap-2 pt-2">
                <span className="text-xs text-muted-foreground self-center mr-2">Explore:</span>
                <Button variant="ghost" size="sm" asChild>
                    <Link to="/quality/ncrs">
                        <Package className="h-4 w-4 mr-1" />
                        NCR Analysis
                    </Link>
                </Button>
                <Button variant="ghost" size="sm" asChild>
                    <Link to="/quality/defects">
                        <AlertTriangle className="h-4 w-4 mr-1" />
                        Defect Patterns
                    </Link>
                </Button>
                <Button variant="ghost" size="sm" asChild>
                    <Link to="/quality/capas">
                        <Clock className="h-4 w-4 mr-1" />
                        CAPA Management
                    </Link>
                </Button>
                <Button variant="ghost" size="sm" asChild>
                    <Link to="/editor/qualityReports">
                        <FileText className="h-4 w-4 mr-1" />
                        All Reports
                    </Link>
                </Button>
            </div>
        </div>
    );
}
