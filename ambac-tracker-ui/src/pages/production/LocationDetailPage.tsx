import { useRef, useState } from "react";
import { Link, useParams } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowDownToLine, ArrowUpFromLine, ScanLine, Tag } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useReportEmail } from "@/hooks/useReportEmail";
import { locationContentsOptions, useMoveLot, useMoveParts } from "@/hooks/useLocations";
import { resolveScan } from "@/lib/scan";

const errorOf = (err: unknown, fallback: string) =>
    (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? fallback;

/**
 * One location: what's in it, what moved in and out this week — and putting things
 * here. Scan a lot or a serial into the box and it moves here, whole; one scan, one
 * move, the field ready for the next.
 */
export function LocationDetailPage() {
    // The router hands the param back already decoded.
    const { name } = useParams({ strict: false }) as { name: string };
    const { data, isLoading } = useQuery(locationContentsOptions(name));
    const { downloadReport } = useReportEmail();
    const moveLot = useMoveLot();
    const moveParts = useMoveParts();
    const [code, setCode] = useState("");
    const [busy, setBusy] = useState(false);
    const input = useRef<HTMLInputElement>(null);

    const putHere = async () => {
        const q = code.trim();
        if (!q || busy) return;
        setBusy(true);
        try {
            const hit = await resolveScan(q);
            if (hit?.kind === "LOT") {
                const moved = await moveLot.mutateAsync({ id: hit.id, to: name });
                toast.success(`Lot ${moved.lot_number} → ${name}`);
            } else if (hit?.kind === "PART") {
                await moveParts.mutateAsync({ part_ids: [hit.id], to: name });
                toast.success(`${hit.label} → ${name}`);
            } else {
                toast.error(hit ? `That's a ${hit.kind.toLowerCase().replace("_", " ")}, not a lot or a unit.` : `Nothing matches “${q}”.`);
            }
        } catch (e) {
            toast.error(errorOf(e, "Could not move it"));
        } finally {
            setBusy(false);
            setCode("");
            input.current?.focus();
        }
    };

    return (
        <div className="mx-auto max-w-5xl space-y-4 p-6">
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                    <div className="text-sm text-muted-foreground">
                        <Link to="/production/locations" className="hover:underline">Locations</Link> / location
                    </div>
                    <h1 className="text-2xl font-semibold">{name}</h1>
                    <p className="text-sm text-muted-foreground">
                        {data ? `${data.lots.length} lot${data.lots.length === 1 ? "" : "s"} · ${data.parts.length} unit${data.parts.length === 1 ? "" : "s"}` : " "}
                    </p>
                </div>
                <Button size="sm" variant="outline"
                    onClick={() => void downloadReport("location_label", { names: [name], copies: 1, layout: "thermal" })}>
                    <Tag className="mr-1 h-4 w-4" /> Label
                </Button>
            </div>

            <div className="flex items-center gap-2 rounded-lg border bg-card p-3">
                <ScanLine className="h-5 w-5 shrink-0 text-muted-foreground" />
                <Input ref={input} value={code} onChange={(e) => setCode(e.target.value)} autoFocus disabled={busy}
                    onKeyDown={(e) => { if (e.key === "Enter") void putHere(); }}
                    placeholder={`Scan a lot or unit to put it in ${name}…`}
                    className="border-0 text-base shadow-none focus-visible:ring-0" />
                <Button onClick={() => void putHere()} disabled={busy || !code.trim()}>{busy ? "Moving…" : "Put here"}</Button>
            </div>

            {isLoading ? <div className="h-32 animate-pulse rounded bg-muted" /> : data && (
                <>
                    <Card>
                        <CardHeader className="pb-2"><CardTitle className="text-base">Lots</CardTitle></CardHeader>
                        <CardContent className="overflow-x-auto">
                            {data.lots.length === 0 ? <p className="text-sm text-muted-foreground">No lots here.</p> : (
                                <table className="w-full text-sm">
                                    <thead><tr className="border-b text-left text-muted-foreground">
                                        <th className="py-2 pr-3 font-medium">Lot</th><th className="py-2 pr-3 font-medium">Item</th>
                                        <th className="py-2 pr-3 text-right font-medium">On hand</th><th className="py-2 font-medium">Status</th>
                                    </tr></thead>
                                    <tbody>
                                        {data.lots.map((l) => (
                                            <tr key={l.id} className="border-b last:border-0">
                                                <td className="py-2 pr-3"><Link to="/production/material-lots/$lotId" params={{ lotId: l.id }} className="font-mono hover:underline">{l.lot_number}</Link></td>
                                                <td className="py-2 pr-3">{l.item_name || "—"}{l.owner_name && <span className="ml-1 text-xs text-sky-700">· {l.owner_name}&rsquo;s</span>}</td>
                                                <td className="py-2 pr-3 text-right tabular-nums">{l.quantity_remaining} {l.unit_of_measure}</td>
                                                <td className="py-2"><Badge variant="outline">{l.status.replace(/_/g, " ").toLowerCase()}</Badge></td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            )}
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader className="pb-2"><CardTitle className="text-base">Units</CardTitle></CardHeader>
                        <CardContent className="overflow-x-auto">
                            {data.parts.length === 0 ? <p className="text-sm text-muted-foreground">No serialised units here.</p> : (
                                <table className="w-full text-sm">
                                    <thead><tr className="border-b text-left text-muted-foreground">
                                        <th className="py-2 pr-3 font-medium">Serial</th><th className="py-2 pr-3 font-medium">Item</th>
                                        <th className="py-2 pr-3 font-medium">Work order</th><th className="py-2 font-medium">Status</th>
                                    </tr></thead>
                                    <tbody>
                                        {data.parts.map((p) => (
                                            <tr key={p.id} className="border-b last:border-0">
                                                <td className="py-2 pr-3 font-mono">{p.erp_id}</td>
                                                <td className="py-2 pr-3">{p.part_type ?? "—"}</td>
                                                <td className="py-2 pr-3">{p.work_order_id
                                                    ? <Link to="/workorder/$workOrderId" params={{ workOrderId: p.work_order_id }} className="hover:underline">{p.work_order}</Link>
                                                    : "—"}</td>
                                                <td className="py-2">{p.status}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            )}
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader className="pb-2"><CardTitle className="text-base">Moves, last 7 days</CardTitle></CardHeader>
                        <CardContent className="overflow-x-auto">
                            {data.moves.length === 0 ? <p className="text-sm text-muted-foreground">Nothing moved in or out.</p> : (
                                <table className="w-full text-sm">
                                    <tbody>
                                        {data.moves.map((m, i) => (
                                            <tr key={i} className="border-b last:border-0">
                                                <td className="py-2 pr-3 whitespace-nowrap text-muted-foreground tabular-nums">{new Date(m.at).toLocaleString()}</td>
                                                <td className="py-2 pr-3">
                                                    {m.direction === "IN"
                                                        ? <span className="inline-flex items-center gap-1 text-emerald-700"><ArrowDownToLine className="h-3.5 w-3.5" /> In</span>
                                                        : <span className="inline-flex items-center gap-1 text-amber-700"><ArrowUpFromLine className="h-3.5 w-3.5" /> Out</span>}
                                                </td>
                                                <td className="py-2 pr-3 font-mono">{m.kind === "LOT"
                                                    ? <Link to="/production/material-lots/$lotId" params={{ lotId: m.object_id }} className="hover:underline">{m.label}</Link>
                                                    : m.label}</td>
                                                <td className="py-2 pr-3 text-muted-foreground">{m.direction === "IN" ? "from" : "to"} {m.other || "no location"}</td>
                                                <td className="py-2 text-muted-foreground">{m.by ?? ""}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            )}
                        </CardContent>
                    </Card>
                </>
            )}
        </div>
    );
}
