import { useState } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { MapPin, Tag } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { useReportEmail } from "@/hooks/useReportEmail";
import { locationSummaryOptions } from "@/hooks/useLocations";
import { locationFromScan, resolveScan } from "@/lib/scan";

/**
 * Where stock is. Every location holding something, and every one on the managed list,
 * with what's in each. Scan a location's label (or type its name) to open it; print
 * labels for the ones that don't have one yet.
 */
export function LocationsPage() {
    const navigate = useNavigate();
    const { data, isLoading } = useQuery(locationSummaryOptions());
    const { downloadReport } = useReportEmail();
    const [code, setCode] = useState("");
    const [filter, setFilter] = useState("");
    const [picked, setPicked] = useState<Set<string>>(new Set());

    const open = async () => {
        const q = code.trim();
        if (!q) return;
        const hit = await resolveScan(q).catch(() => null);
        setCode("");
        if (hit?.kind === "LOCATION") { void navigate({ to: "/production/locations/$name", params: { name: hit.label } }); return; }
        if (hit?.path) { void navigate({ to: hit.path as never }); return; }
        // A typed location that is only free text (never on the managed list) still opens.
        void navigate({ to: "/production/locations/$name", params: { name: locationFromScan(q) } });
    };

    // "Not on the list" only means something once there is a list.
    const anyManaged = (data ?? []).some((r) => r.managed);
    const rows = (data ?? []).filter((r) => r.name.toLowerCase().includes(filter.toLowerCase()));
    const toggle = (n: string) =>
        setPicked((s) => { const x = new Set(s); if (x.has(n)) x.delete(n); else x.add(n); return x; });

    return (
        <div className="mx-auto max-w-5xl space-y-4 p-6">
            <div>
                <h1 className="text-2xl font-semibold tracking-tight">Locations</h1>
                <p className="text-sm text-muted-foreground">
                    Where lots and units are. Moves are recorded — open a location to see what came and went.
                </p>
            </div>

            <div className="flex items-center gap-2 rounded-lg border bg-card p-3">
                <MapPin className="h-5 w-5 shrink-0 text-muted-foreground" />
                <Input value={code} onChange={(e) => setCode(e.target.value)} autoFocus
                    onKeyDown={(e) => { if (e.key === "Enter") void open(); }}
                    placeholder="Scan a location label, or type its name…"
                    className="border-0 text-base shadow-none focus-visible:ring-0" />
                <Button onClick={() => void open()} disabled={!code.trim()}>Open</Button>
            </div>

            <div className="flex flex-wrap items-center gap-2">
                <Input placeholder="Filter…" value={filter} onChange={(e) => setFilter(e.target.value)} className="max-w-xs" />
                <Link to="/production/cycle-counts" className="ml-auto text-sm hover:underline">Cycle counts</Link>
                <Button size="sm" variant="outline" disabled={picked.size === 0}
                    onClick={() => void downloadReport("location_label", { names: [...picked], copies: 1, layout: picked.size > 2 ? "sheet" : "thermal" })
                        .then(() => toast.success(`Labels for ${picked.size} location${picked.size === 1 ? "" : "s"}.`))}>
                    <Tag className="mr-1 h-4 w-4" /> Print labels{picked.size ? ` (${picked.size})` : ""}
                </Button>
            </div>

            <div className="overflow-x-auto rounded-lg border">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="border-b text-left text-muted-foreground">
                            <th className="w-8 px-3 py-2" />
                            <th className="px-3 py-2 font-medium">Location</th>
                            <th className="px-3 py-2 text-right font-medium">Lots</th>
                            <th className="px-3 py-2 text-right font-medium">Units</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows.map((r) => (
                            <tr key={r.name} className="border-b last:border-0">
                                <td className="px-3 py-2"><Checkbox checked={picked.has(r.name)} onCheckedChange={() => toggle(r.name)} aria-label={`Label for ${r.name}`} /></td>
                                <td className="px-3 py-2">
                                    <Link to="/production/locations/$name" params={{ name: r.name }} className="font-medium hover:underline">{r.name}</Link>
                                    {!r.managed && anyManaged && <Badge variant="outline" className="ml-2 text-xs">typed, not on the list</Badge>}
                                    {r.description && <div className="text-xs text-muted-foreground">{r.description}</div>}
                                </td>
                                <td className="px-3 py-2 text-right tabular-nums">{r.lots || "—"}</td>
                                <td className="px-3 py-2 text-right tabular-nums">{r.parts || "—"}</td>
                            </tr>
                        ))}
                        {!isLoading && rows.length === 0 && (
                            <tr><td colSpan={4} className="px-3 py-8 text-center text-muted-foreground">
                                No locations yet. Set them up in Data Management → Storage Locations, or they appear here as stock is put away.
                            </td></tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
