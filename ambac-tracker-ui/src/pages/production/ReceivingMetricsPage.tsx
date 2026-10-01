import { useState } from "react";
import { queryOptions, useQuery } from "@tanstack/react-query";
import { Clock, Hourglass, PackageCheck, PackageX, ShieldAlert } from "lucide-react";
import { api } from "@/lib/api/generated";
import {
    ChartCard, DateRangeToggle, KpiCard, KpiGrid, SimpleHorizontalBarChart, StackedBarChart,
    rangeToDays, type DateRange,
} from "@/components/analytics";
import { HOLD_LABELS } from "@/components/receiving/lotStatus";
import type { Schema } from "@/lib/api/types";

type Metrics = Schema<"DockMetrics">;

const metricsOptions = (days: number) =>
    queryOptions({
        queryKey: ["dock-metrics", days],
        queryFn: () => api.api_MaterialLots_dock_metrics_retrieve({ queries: { days } }) as Promise<Metrics>,
    });

const reasonLabel = (code: string) => HOLD_LABELS[code] ?? code;

/**
 * Receiving's own numbers — how the dock is doing, as opposed to how the suppliers are
 * (that's Supplier Quality). What came in, what is waiting and how long, how fast lots
 * get a decision, what is held and why, and what was rejected in pieces.
 */
export function ReceivingMetricsPage() {
    const [range, setRange] = useState<DateRange>("30d");
    const days = rangeToDays(range);
    const { data: m, isLoading } = useQuery(metricsOptions(days));

    return (
        <div className="mx-auto max-w-6xl space-y-4 p-6">
            <div className="flex flex-wrap items-end justify-between gap-3">
                <div>
                    <h1 className="text-2xl font-semibold tracking-tight">Receiving metrics</h1>
                    <p className="text-sm text-muted-foreground">
                        How the dock is doing over the last {days} days. Supplier performance is on Supplier Quality.
                    </p>
                </div>
                <DateRangeToggle value={range} onChange={setRange} />
            </div>

            <KpiGrid columns={4}>
                <KpiCard title="Lots received" value={m?.lots_received ?? "—"} icon={PackageCheck} isLoading={isLoading} />
                <KpiCard
                    title="Waiting for a decision"
                    value={m?.awaiting_decision ?? "—"}
                    subtitle={m?.oldest_wait_days != null ? `Oldest waiting ${m.oldest_wait_days} days` : undefined}
                    icon={Hourglass}
                    variant={(m?.oldest_wait_days ?? 0) > 5 ? "warning" : "default"}
                    link="/production/incoming"
                    isLoading={isLoading}
                />
                <KpiCard
                    title="Median days to a decision"
                    value={m?.median_days_to_decision ?? "—"}
                    subtitle={m?.median_inspection_hours != null
                        ? `Inspection itself: ${m.median_inspection_hours} h median · ${m.decided} decided`
                        : undefined}
                    icon={Clock}
                    isLoading={isLoading}
                />
                <KpiCard
                    title="Rejected"
                    value={m ? `${m.pieces_rejected} pcs` : "—"}
                    subtitle={m ? `${m.lots_rejected} lot${m.lots_rejected === 1 ? "" : "s"}${m.ppm_rejected != null ? ` · ${m.ppm_rejected.toLocaleString()} PPM` : ""}` : undefined}
                    icon={PackageX}
                    variant={(m?.lots_rejected ?? 0) > 0 ? "danger" : "default"}
                    isLoading={isLoading}
                />
            </KpiGrid>

            {/* Bars, not a line: these are whole lots on whole days — a smoothed curve
                between days would suggest half a delivery on the day in between. */}
            <ChartCard title="Lots received per day" description="Every day in the window; an empty day shows as one." isLoading={isLoading}>
                <StackedBarChart
                    data={(m?.receipts ?? []).map((r) => ({
                        category: new Date(r.date + "T00:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric" }),
                        lots: r.lots,
                    }))}
                    series={[{ dataKey: "lots", label: "Lots received", color: "var(--chart-1)" }]}
                    showLegend={false}
                    height={220}
                    yAxisFormatter={(v) => (Number.isInteger(v) ? String(v) : "")}
                />
            </ChartCard>

            <div className="grid gap-4 md:grid-cols-2">
                <ChartCard title="Held now, by reason" description="Lots waiting on a hold at receiving." isLoading={isLoading}>
                    {(m?.held_now.length ?? 0) === 0 ? (
                        <p className="flex items-center gap-2 text-sm text-muted-foreground">
                            <ShieldAlert className="h-4 w-4" /> Nothing is held.
                        </p>
                    ) : (
                        <SimpleHorizontalBarChart
                            data={m!.held_now.map((h) => ({ name: reasonLabel(h.reason), value: h.lots }))}
                            maxItems={8}
                        />
                    )}
                </ChartCard>
                <ChartCard title="Holds released" description="Holds lifted in the window, by what they were." isLoading={isLoading}>
                    {(m?.holds_released.length ?? 0) === 0 ? (
                        <p className="text-sm text-muted-foreground">None released in this window.</p>
                    ) : (
                        <SimpleHorizontalBarChart
                            data={m!.holds_released.map((h) => ({ name: reasonLabel(h.reason), value: h.lots }))}
                            maxItems={8}
                        />
                    )}
                </ChartCard>
            </div>
        </div>
    );
}
