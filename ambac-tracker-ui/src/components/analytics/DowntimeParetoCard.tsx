import { useQuery, queryOptions } from "@tanstack/react-query";
import { CheckCircle2, Wrench } from "lucide-react";
import { api } from "@/lib/api/generated";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const downtimeSummaryOptions = (days: number) =>
    queryOptions({
        queryKey: ["downtime-events", "summary", { days }] as const,
        queryFn: () => api.api_DowntimeEvents_summary_retrieve({ queries: { days } }),
    });

type Bucket = { key: string; label: string; hours: number; events: number };

function formatHours(h: number) {
    return h >= 10 ? `${Math.round(h)} h` : `${h.toFixed(1)} h`;
}

function Bars({ rows, colorClass, suffix }: {
    rows: Bucket[];
    colorClass: string;
    suffix?: (row: Bucket) => string;
}) {
    const max = rows[0]?.hours || 1;
    return (
        <div className="space-y-2">
            {rows.map((row) => (
                <div key={row.key || row.label} className="flex items-center gap-3">
                    <span className="text-xs text-muted-foreground w-36 truncate" title={row.label}>
                        {row.label}
                    </span>
                    <div className="flex-1 h-5 bg-muted/30 rounded overflow-hidden">
                        <div className={`h-full rounded ${colorClass}`} style={{ width: `${(row.hours / max) * 100}%` }} />
                    </div>
                    <span className="text-xs font-mono font-medium w-24 text-right">
                        {formatHours(row.hours)}
                        {suffix ? <span className="text-muted-foreground"> {suffix(row)}</span> : null}
                    </span>
                </div>
            ))}
        </div>
    );
}

/**
 * Downtime over the period: lost hours by category (the Six Big Losses shape) and by
 * machine, largest first. An event still open counts up to now. The share beside a
 * machine is of the period's calendar time, not of its scheduled time — this is lost
 * time, not OEE.
 */
export function DowntimeParetoCard({ days }: { days: number }) {
    const { data, isLoading } = useQuery(downtimeSummaryOptions(days));
    const periodHours = days * 24;

    return (
        <Card className="border-muted/40">
            <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                    <Wrench className="h-4 w-4" />
                    Downtime
                </CardTitle>
                <p className="text-xs text-muted-foreground">
                    {data
                        ? `${formatHours(data.total_hours)} lost across ${data.total_events} event${data.total_events === 1 ? "" : "s"} in ${days}d`
                        : `Last ${days}d`}
                    {data && data.open_events > 0 ? ` · ${data.open_events} still open (counted to now)` : ""}
                </p>
            </CardHeader>
            <CardContent>
                {isLoading ? (
                    <div className="h-[140px] flex items-center justify-center text-muted-foreground">Loading...</div>
                ) : !data || data.total_events === 0 ? (
                    <div className="h-[140px] flex items-center justify-center text-muted-foreground">
                        <div className="text-center">
                            <CheckCircle2 className="h-8 w-8 text-green-500 mx-auto mb-2" />
                            <p className="text-sm">No downtime recorded</p>
                        </div>
                    </div>
                ) : (
                    <div className="grid gap-6 md:grid-cols-2">
                        <div className="space-y-2">
                            <p className="text-xs font-medium">By cause</p>
                            <Bars rows={data.by_category} colorClass="bg-chart-3" />
                        </div>
                        <div className="space-y-2">
                            <p className="text-xs font-medium">By machine</p>
                            <Bars
                                rows={data.by_equipment.slice(0, 8)}
                                colorClass="bg-chart-4"
                                suffix={(row) => `· ${((row.hours / periodHours) * 100).toFixed(1)}%`}
                            />
                            <p className="text-[10px] text-muted-foreground">
                                Share of the period's calendar time the machine was down.
                            </p>
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
