import { Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { cycleCountsOptions } from "@/hooks/useCycleCounts";

/** Every count, newest first: which are still being counted, waiting to be applied, or done. */
export function CycleCountsPage() {
    const { data, isLoading } = useQuery(cycleCountsOptions());
    const rows = data?.results ?? [];
    return (
        <div className="mx-auto max-w-5xl space-y-4 p-6">
            <div>
                <div className="text-sm text-muted-foreground"><Link to="/production/locations" className="hover:underline">Locations</Link> / counts</div>
                <h1 className="text-2xl font-semibold tracking-tight">Cycle counts</h1>
                <p className="text-sm text-muted-foreground">Start a count from a location&rsquo;s page.</p>
            </div>
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
                                <td className="px-3 py-2">{c.location}</td>
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
