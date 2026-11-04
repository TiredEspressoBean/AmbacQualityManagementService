import { Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import {
    countAccuracyOptions, cycleCountsOptions, dueForCountOptions, type CountAccuracy, type DueForCount,
} from "@/hooks/useCycleCounts";

/** Every count, newest first: which are still being counted, waiting to be applied, or done.
 *  Above them, what's due for counting under its ABC class (schedule by item, walk by
 *  location — services/mes/count_cadence) and how accurate recent counts have been. */
export function CycleCountsPage() {
    const { data, isLoading } = useQuery(cycleCountsOptions());
    const rows = data?.results ?? [];
    const { data: due } = useQuery(dueForCountOptions());
    const { data: accuracy } = useQuery(countAccuracyOptions(90));
    return (
        <div className="mx-auto max-w-5xl space-y-4 p-6">
            <div>
                <div className="text-sm text-muted-foreground"><Link to="/production/locations" className="hover:underline">Locations</Link> / counts</div>
                <h1 className="text-2xl font-semibold tracking-tight">Cycle counts</h1>
                <p className="text-sm text-muted-foreground">Start a count from a location&rsquo;s page.</p>
            </div>
            {accuracy && <AccuracyStrip accuracy={accuracy} />}
            <DueForCount rows={due ?? []} />
            <div className="overflow-x-auto rounded-lg border">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="border-b text-left text-muted-foreground">
                            <th className="px-3 py-2 font-medium">Count</th>
                            <th className="px-3 py-2 font-medium">Location</th>
                            <th className="px-3 py-2 font-medium">Status</th>
                            <th className="px-3 py-2 text-right font-medium">Differences</th>
                            <th className="px-3 py-2 font-medium">Started</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows.map((c) => (
                            <tr key={c.id} className="border-b last:border-0">
                                <td className="px-3 py-2">
                                    <Link to="/production/cycle-counts/$countId" params={{ countId: c.id }} className="font-mono hover:underline">{c.count_number}</Link>
                                    {c.blind && <Badge variant="outline" className="ml-2">Blind</Badge>}
                                </td>
                                <td className="px-3 py-2">{c.location_name}</td>
                                <td className="px-3 py-2"><Badge variant={c.status === "APPLIED" ? "default" : "outline"}>{c.status_display}</Badge></td>
                                <td className="px-3 py-2 text-right tabular-nums">{c.status === "OPEN" ? "—" : c.variances.length}</td>
                                <td className="px-3 py-2 text-muted-foreground">{new Date(c.created_at).toLocaleDateString()} · {c.started_by_name ?? "—"}</td>
                            </tr>
                        ))}
                        {!isLoading && rows.length === 0 && (
                            <tr><td colSpan={5} className="px-3 py-8 text-center text-muted-foreground">No counts yet.</td></tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

/** Inventory record accuracy per class: counted lines within their class's tolerance. */
function AccuracyStrip({ accuracy }: { accuracy: CountAccuracy }) {
    const cells = (["A", "B", "C"] as const).map((c) => ({ c, ...accuracy[c] }));
    return (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-lg border px-3 py-2 text-sm">
            <span className="text-muted-foreground">Count accuracy, last {accuracy.days} days:</span>
            {cells.map(({ c, pct, counted, hits }) => (
                <span key={c} title={counted ? `${hits} of ${counted} counted lines within tolerance` : "Nothing counted"}>
                    <span className="font-medium">{c}</span>{" "}
                    <span className="tabular-nums">{pct == null ? "—" : `${pct}%`}</span>
                </span>
            ))}
        </div>
    );
}

/** What's due for counting: an item whose stock somewhere hasn't been counted within its
 *  class's interval. Counting the locations named clears it. */
function DueForCount({ rows }: { rows: DueForCount[] }) {
    return (
        <div className="space-y-2">
            <h2 className="text-lg font-semibold">Due for count</h2>
            {rows.length === 0 ? (
                <p className="text-sm text-muted-foreground">Nothing due — every item&rsquo;s stock has been counted within its class&rsquo;s interval.</p>
            ) : (
                <div className="overflow-x-auto rounded-lg border">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b text-left text-muted-foreground">
                                <th className="px-3 py-2 font-medium">Item</th>
                                <th className="px-3 py-2 font-medium">Class</th>
                                <th className="px-3 py-2 font-medium">Due</th>
                                <th className="px-3 py-2 font-medium">Count at</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows.map((r) => (
                                <tr key={`${r.kind}:${r.id}`} className="border-b last:border-0 align-top">
                                    <td className="px-3 py-2">
                                        {r.name}
                                        <span className="ml-1 text-xs text-muted-foreground">{r.kind === "MATERIAL" ? "material" : "part type"}</span>
                                    </td>
                                    <td className="px-3 py-2"><Badge variant="outline">{r.abc_class}</Badge></td>
                                    <td className="px-3 py-2">
                                        {r.never_counted ? "Never counted"
                                            : r.days_overdue > 0 ? `${r.days_overdue} day${r.days_overdue === 1 ? "" : "s"} overdue`
                                                : "Due today"}
                                        <div className="text-xs text-muted-foreground">every {r.interval_days} days</div>
                                    </td>
                                    <td className="px-3 py-2">
                                        <div className="flex flex-wrap gap-x-3 gap-y-1">
                                            {r.locations.map((l) => (
                                                <Link key={l.location_id} to="/production/locations/$locationId"
                                                    params={{ locationId: l.location_id }} className="hover:underline">
                                                    {l.location}
                                                </Link>
                                            ))}
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
            <h2 className="pt-2 text-lg font-semibold">Counts</h2>
        </div>
    );
}
