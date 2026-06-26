import { type ReactNode } from "react";
import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from "recharts";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import { cn } from "@/lib/utils";
import { usePartTypeQualitySummary } from "@/hooks/usePartTypeQualitySummary";

/**
 * Right-panel quality dashboard for a PartType's detail page — an aggregate of
 * all quality reports for parts of this type: FPY / pass-fail, open
 * dispositions & CAPAs, a defect Pareto, recent failures, and a 30-day FPY
 * trend. Wired as the `RendererSidebarComponent` for `parttypes`.
 */

type RendererProps = {
    modelType?: string;
    modelData: { id?: string | number };
    documents?: unknown[];
    loading?: boolean;
};

const fpyChartConfig = { fpy: { label: "FPY %", color: "var(--chart-1)" } };

function Kpi({
    label,
    value,
    sub,
    tone,
}: {
    label: string;
    value: ReactNode;
    sub?: string;
    tone?: "good" | "bad" | "warn";
}) {
    const toneCls =
        tone === "good"
            ? "text-green-600"
            : tone === "bad"
                ? "text-destructive"
                : tone === "warn"
                    ? "text-amber-600"
                    : "text-foreground";
    return (
        <Card>
            <CardContent className="p-3">
                <div className="text-xs text-muted-foreground">{label}</div>
                <div className={cn("text-xl font-bold", toneCls)}>{value}</div>
                {sub && <div className="text-[10px] text-muted-foreground">{sub}</div>}
            </CardContent>
        </Card>
    );
}

export function PartTypeQualityRenderer({ modelData }: RendererProps) {
    const id = modelData?.id != null ? String(modelData.id) : undefined;
    const { data, isLoading, isError } = usePartTypeQualitySummary(id);

    if (isLoading) {
        return <div className="text-sm text-muted-foreground">Loading quality summary…</div>;
    }
    if (isError || !data) {
        return <div className="text-sm text-muted-foreground">No quality data available for this part type.</div>;
    }

    const { reports, open, parts_total, defect_pareto, spc, recent_failures, fpy_trend } = data;
    const maxDefect = Math.max(1, ...defect_pareto.map((d) => d.count));
    const hasTrend = fpy_trend.some((p) => p.fpy != null);

    return (
        <div className="space-y-4">
            <div>
                <h2 className="text-lg font-semibold">Quality Overview</h2>
                <p className="text-sm text-muted-foreground">
                    Aggregated across all parts of this type.
                </p>
            </div>

            <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
                <Kpi
                    label="First Pass Yield"
                    value={reports.fpy != null ? `${reports.fpy}%` : "—"}
                    sub={`${reports.total} inspection${reports.total === 1 ? "" : "s"}`}
                />
                <Kpi label="Passed" value={reports.passed} tone={reports.passed ? "good" : undefined} />
                <Kpi label="Failed" value={reports.failed} tone={reports.failed ? "bad" : undefined} />
                <Kpi label="Pending" value={reports.pending} />
                <Kpi label="Parts" value={parts_total} />
                <Kpi label="Open dispositions" value={open.dispositions} tone={open.dispositions ? "warn" : undefined} />
                <Kpi label="Open CAPAs" value={open.capas} tone={open.capas ? "warn" : undefined} />
            </div>

            <Card>
                <CardHeader className="pb-2">
                    <CardTitle className="text-base">FPY Trend (30 days)</CardTitle>
                </CardHeader>
                <CardContent>
                    {hasTrend ? (
                        <ChartContainer className="h-[180px] w-full" config={fpyChartConfig}>
                            <AreaChart data={fpy_trend} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
                                <defs>
                                    <linearGradient id="ptFpyGradient" x1="0" y1="0" x2="0" y2="1">
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
                                    domain={[0, 100]}
                                    tickLine={false}
                                    axisLine={false}
                                    tick={{ fontSize: 10 }}
                                    tickFormatter={(v) => `${v}%`}
                                />
                                <ChartTooltip content={<ChartTooltipContent formatter={(value) => `${value}%`} />} />
                                <Area
                                    dataKey="fpy"
                                    type="monotone"
                                    stroke="var(--chart-1)"
                                    fill="url(#ptFpyGradient)"
                                    strokeWidth={2}
                                    connectNulls
                                />
                            </AreaChart>
                        </ChartContainer>
                    ) : (
                        <p className="py-6 text-center text-sm text-muted-foreground">
                            No inspections in the last 30 days.
                        </p>
                    )}
                </CardContent>
            </Card>

            <Card>
                <CardHeader className="pb-2">
                    <CardTitle className="text-base">Top Defects</CardTitle>
                </CardHeader>
                <CardContent>
                    {defect_pareto.length ? (
                        <div className="space-y-2">
                            {defect_pareto.map((d) => (
                                <div key={d.error_type} className="space-y-1">
                                    <div className="flex items-center justify-between text-sm">
                                        <span className="truncate">{d.error_type}</span>
                                        <span className="ml-2 flex-shrink-0 text-muted-foreground">{d.count}</span>
                                    </div>
                                    <div className="h-2 rounded bg-muted">
                                        <div
                                            className="h-2 rounded bg-destructive"
                                            style={{ width: `${(d.count / maxDefect) * 100}%` }}
                                        />
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p className="py-4 text-center text-sm text-muted-foreground">No defects recorded.</p>
                    )}
                </CardContent>
            </Card>

            <Card>
                <CardHeader className="pb-2">
                    <CardTitle className="text-base">SPC / Measurement Capability</CardTitle>
                </CardHeader>
                <CardContent>
                    {spc.length ? (
                        <div className="space-y-3">
                            {spc.map((m) => (
                                <div key={m.measurement_id} className="space-y-1">
                                    <div className="flex items-center justify-between gap-2 text-sm">
                                        <span className="truncate">{m.label}</span>
                                        <span className="flex flex-shrink-0 items-center gap-2">
                                            {m.ppk != null && (
                                                <span
                                                    className={cn(
                                                        "rounded px-1.5 py-0.5 text-[10px] font-medium",
                                                        m.capable
                                                            ? "bg-green-600/15 text-green-600"
                                                            : "bg-destructive/15 text-destructive",
                                                    )}
                                                >
                                                    Ppk {m.ppk}
                                                </span>
                                            )}
                                            <span className="text-xs text-muted-foreground">
                                                {m.in_spec_pct}% in-spec
                                            </span>
                                        </span>
                                    </div>
                                    <div className="h-2 rounded bg-muted">
                                        <div
                                            className={cn(
                                                "h-2 rounded",
                                                m.in_spec_pct >= 95
                                                    ? "bg-green-600"
                                                    : m.in_spec_pct >= 80
                                                        ? "bg-amber-500"
                                                        : "bg-destructive",
                                            )}
                                            style={{ width: `${m.in_spec_pct}%` }}
                                        />
                                    </div>
                                    <div className="text-[10px] text-muted-foreground">
                                        n={m.n} · mean {m.mean}
                                        {m.unit ? ` ${m.unit}` : ""}
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p className="py-4 text-center text-sm text-muted-foreground">
                            No numeric measurement data.
                        </p>
                    )}
                </CardContent>
            </Card>

            <Card>
                <CardHeader className="pb-2">
                    <CardTitle className="text-base">Recent Failures</CardTitle>
                </CardHeader>
                <CardContent>
                    {recent_failures.length ? (
                        <div className="space-y-2">
                            {recent_failures.map((r) => (
                                <div
                                    key={r.id}
                                    className="flex items-center justify-between gap-2 rounded border p-2 text-sm"
                                >
                                    <div className="min-w-0">
                                        <div className="truncate font-medium">
                                            {r.report_number || `Report ${r.id.slice(0, 8)}`}
                                        </div>
                                        <div className="truncate text-xs text-muted-foreground">
                                            {[r.part, r.step].filter(Boolean).join(" · ") || "—"}
                                        </div>
                                    </div>
                                    <span className="flex-shrink-0 text-xs text-muted-foreground">
                                        {new Date(r.created_at).toLocaleDateString()}
                                    </span>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p className="py-4 text-center text-sm text-muted-foreground">No recent failures.</p>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
