import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { FileSpreadsheet, FileText, ScanLine } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api/generated";
import { blobErrorMessage, downloadBlob } from "@/lib/download";
import { resolveScan } from "@/lib/scan";
import { useReportEmail } from "@/hooks/useReportEmail";
import { usePermissionSet } from "@/hooks/useMyPermissions";
import {
    cycleCountOptions, useApplyCount, useRecordCount, useSubmitCount, type CountEntry,
} from "@/hooks/useCycleCounts";

const errorOf = (err: unknown, fallback: string) =>
    (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? fallback;

const WHAT: Record<string, { label: string; tone: string }> = {
    SHORT: { label: "Short", tone: "text-amber-700" },
    OVER: { label: "Over", tone: "text-sky-700" },
    MISSING: { label: "Not found", tone: "text-destructive" },
    FOUND_HERE: { label: "Found here", tone: "text-emerald-700" },
};

/**
 * Counting one location, on a tablet. Enter what's there for each lot, tick each unit
 * that's present, and scan anything here that isn't on the list. Save as you go; submit
 * when the location is done. A lead then applies the count — UQMES's quantities and
 * locations are corrected — and the differences go to the ERP to be keyed.
 */
export function CycleCountPage() {
    const { countId } = useParams({ strict: false }) as { countId: string };
    const { data: c, isLoading } = useQuery(cycleCountOptions(countId));
    const record = useRecordCount();
    const submit = useSubmitCount();
    const apply = useApplyCount();
    const perms = usePermissionSet();
    const { downloadReport } = useReportEmail();
    const [draft, setDraft] = useState<Record<string, string>>({});
    const [scan, setScan] = useState("");
    const scanRef = useRef<HTMLInputElement>(null);

    // Seed the inputs from what's saved, once per load.
    useEffect(() => {
        if (!c) return;
        setDraft(Object.fromEntries(c.lines.map((l) => [`${l.kind}:${l.id}`, l.counted == null ? "" : String(l.counted)])));
    }, [c?.id, c?.updated_at]); // eslint-disable-line react-hooks/exhaustive-deps

    const open = c?.status === "OPEN";
    const lots = useMemo(() => (c?.lines ?? []).filter((l) => l.kind === "LOT"), [c]);
    const units = useMemo(() => (c?.lines ?? []).filter((l) => l.kind === "PART"), [c]);

    if (isLoading || !c) return <div className="mx-auto max-w-5xl p-6"><div className="h-40 animate-pulse rounded bg-muted" /></div>;

    const entries = (): CountEntry[] => c.lines.map((l) => {
        const v = draft[`${l.kind}:${l.id}`] ?? "";
        return { kind: l.kind as "LOT" | "PART", id: l.id, counted: v === "" ? null : v };
    });
    const save = (then?: () => void) => record.mutate({ id: c.id, entries: entries() }, {
        onSuccess: () => { toast.success("Count saved."); then?.(); },
        onError: (e) => toast.error(errorOf(e, "Could not save the count")),
    });

    const onScan = async () => {
        const code = scan.trim();
        if (!code) return;
        setScan("");
        const hit = await resolveScan(code).catch(() => null);
        if (!hit || (hit.kind !== "LOT" && hit.kind !== "PART")) {
            toast.error(hit ? "That isn't a lot or a unit." : `Nothing matches “${code}”.`);
            return;
        }
        const key = `${hit.kind}:${hit.id}`;
        if (key in draft) {
            if (hit.kind === "PART") setDraft((d) => ({ ...d, [key]: "1" }));
            else document.getElementById(`count-${hit.id}`)?.focus();
            return;
        }
        // Not on the list: something found here. Saved at once, so it joins the count.
        const kind = hit.kind as "LOT" | "PART";
        let counted: string | null = kind === "PART" ? "1" : null;
        if (kind === "LOT") {
            const lot = await api.api_MaterialLots_retrieve({ params: { id: hit.id } });
            counted = String(lot.quantity_remaining ?? "");
        }
        record.mutate({ id: c.id, entries: [...entries(), { kind, id: hit.id, counted }] }, {
            onSuccess: () => toast.success(`${hit.label} found here — added to the count.`),
            onError: (e) => toast.error(errorOf(e, "Could not add it")),
        });
        scanRef.current?.focus();
    };

    const uncounted = c.lines.filter((l) => (draft[`${l.kind}:${l.id}`] ?? "") === "").length;

    return (
        <div className="mx-auto max-w-5xl space-y-4 p-6">
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                    <div className="text-sm text-muted-foreground">
                        <Link to="/production/locations/$name" params={{ name: c.location }} className="hover:underline">{c.location}</Link>
                        {" / "}<Link to="/production/cycle-counts" className="hover:underline">counts</Link>
                    </div>
                    <h1 className="flex flex-wrap items-center gap-2 text-2xl font-semibold">
                        <span className="font-mono">{c.count_number}</span>
                        <Badge variant={c.status === "APPLIED" ? "default" : "outline"}>{c.status_display}</Badge>
                        {c.blind && <Badge variant="outline">Blind</Badge>}
                    </h1>
                    <p className="text-sm text-muted-foreground">
                        Started by {c.started_by_name ?? "—"}
                        {c.submitted_by_name ? ` · submitted by ${c.submitted_by_name}` : ""}
                        {c.applied_by_name ? ` · applied by ${c.applied_by_name}` : ""}
                    </p>
                </div>
                <div className="flex flex-wrap gap-2">
                    <Button size="sm" variant="outline" onClick={() => void downloadReport("cycle_count_sheet", { count_id: c.id })}>
                        <FileText className="mr-1 h-4 w-4" /> Count sheet
                    </Button>
                    {!open && (
                        <>
                            <Button size="sm" variant="outline" onClick={() => void downloadReport("cycle_count_report", { count_id: c.id })}>
                                <FileText className="mr-1 h-4 w-4" /> Differences
                            </Button>
                            <Button size="sm" variant="outline"
                                onClick={async () => {
                                    try {
                                        const resp = await api.axios.get(`/api/CycleCounts/${c.id}/differences-xlsx/`, { responseType: "blob" });
                                        downloadBlob(resp.data, `${c.count_number}_differences.xlsx`);
                                    } catch (e) {
                                        toast.error(await blobErrorMessage(e, "Couldn't build the differences sheet."));
                                    }
                                }}>
                                <FileSpreadsheet className="mr-1 h-4 w-4" /> For the ERP
                            </Button>
                        </>
                    )}
                </div>
            </div>

            {open && (
                <div className="flex items-center gap-2 rounded-lg border bg-card p-3">
                    <ScanLine className="h-5 w-5 shrink-0 text-muted-foreground" />
                    <Input ref={scanRef} value={scan} onChange={(e) => setScan(e.target.value)} autoFocus
                        onKeyDown={(e) => { if (e.key === "Enter") void onScan(); }}
                        placeholder="Scan a lot or unit — on the list it's found, off it it's added"
                        className="border-0 text-base shadow-none focus-visible:ring-0" />
                </div>
            )}

            {open ? (
                <>
                    <Card>
                        <CardHeader className="pb-2"><CardTitle className="text-base">Lots — how many are here?</CardTitle></CardHeader>
                        <CardContent className="overflow-x-auto">
                            {lots.length === 0 ? <p className="text-sm text-muted-foreground">No lots expected here.</p> : (
                                <table className="w-full text-sm">
                                    <thead><tr className="border-b text-left text-muted-foreground">
                                        <th className="py-2 pr-3 font-medium">Lot</th><th className="py-2 pr-3 font-medium">Item</th>
                                        {!c.blind && <th className="py-2 pr-3 text-right font-medium">Expected</th>}
                                        <th className="py-2 font-medium">Counted</th>
                                    </tr></thead>
                                    <tbody>
                                        {lots.map((l) => (
                                            <tr key={l.id} className="border-b last:border-0">
                                                <td className="py-2 pr-3 font-mono">{l.label}{l.found_here && <Badge variant="outline" className="ml-2">found here</Badge>}</td>
                                                <td className="py-2 pr-3">{l.item || "—"}</td>
                                                {!c.blind && <td className="py-2 pr-3 text-right tabular-nums">{l.expected} {l.unit}</td>}
                                                <td className="py-2">
                                                    <div className="flex items-center gap-1.5">
                                                        <Input id={`count-${l.id}`} aria-label={`Counted, ${l.label}`} className="h-9 w-28" type="number" min={0} inputMode="decimal"
                                                            value={draft[`LOT:${l.id}`] ?? ""}
                                                            onChange={(e) => setDraft((d) => ({ ...d, [`LOT:${l.id}`]: e.target.value }))} />
                                                        <span className="text-xs text-muted-foreground">{l.unit}</span>
                                                    </div>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            )}
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader className="pb-2"><CardTitle className="text-base">Units — is each one here?</CardTitle></CardHeader>
                        <CardContent className="overflow-x-auto">
                            {units.length === 0 ? <p className="text-sm text-muted-foreground">No serialised units expected here.</p> : (
                                <table className="w-full text-sm">
                                    <tbody>
                                        {units.map((u) => (
                                            <tr key={u.id} className="border-b last:border-0">
                                                <td className="w-8 py-2">
                                                    <Checkbox checked={(draft[`PART:${u.id}`] ?? "") === "1"} aria-label={`${u.label} is here`}
                                                        onCheckedChange={(v) => setDraft((d) => ({ ...d, [`PART:${u.id}`]: v ? "1" : "0" }))} />
                                                </td>
                                                <td className="py-2 pr-3 font-mono">{u.label}{u.found_here && <Badge variant="outline" className="ml-2">found here</Badge>}</td>
                                                <td className="py-2">{u.item || "—"}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            )}
                        </CardContent>
                    </Card>

                    <div className="flex flex-wrap items-center gap-2">
                        <Button variant="outline" disabled={record.isPending} onClick={() => save()}>Save</Button>
                        <Button disabled={record.isPending || submit.isPending}
                            onClick={() => save(() => submit.mutate(c.id, {
                                onSuccess: () => toast.success("Count submitted."),
                                onError: (e) => toast.error(errorOf(e, "Could not submit")),
                            }))}>
                            Submit count
                        </Button>
                        {uncounted > 0 && (
                            <span className="text-sm text-amber-700">{uncounted} not counted yet — submitting records them as not here.</span>
                        )}
                    </div>
                </>
            ) : (
                <Card>
                    <CardHeader className="pb-2"><CardTitle className="text-base">Differences</CardTitle></CardHeader>
                    <CardContent className="space-y-3 overflow-x-auto">
                        {c.variances.length === 0 ? (
                            <p className="text-sm text-muted-foreground">Everything counted matched.</p>
                        ) : (
                            <table className="w-full text-sm">
                                <thead><tr className="border-b text-left text-muted-foreground">
                                    <th className="py-2 pr-3 font-medium">Lot / serial</th><th className="py-2 pr-3 font-medium">Item</th>
                                    <th className="py-2 pr-3 text-right font-medium">Expected</th><th className="py-2 pr-3 text-right font-medium">Counted</th>
                                    <th className="py-2 pr-3 text-right font-medium">Difference</th><th className="py-2 font-medium">What</th>
                                </tr></thead>
                                <tbody>
                                    {c.variances.map((v) => (
                                        <tr key={`${v.kind}:${v.id}`} className="border-b last:border-0">
                                            <td className="py-2 pr-3 font-mono">{v.kind === "LOT"
                                                ? <Link to="/production/material-lots/$lotId" params={{ lotId: v.id }} className="hover:underline">{v.label}</Link>
                                                : v.label}</td>
                                            <td className="py-2 pr-3">{v.item || "—"}</td>
                                            <td className="py-2 pr-3 text-right tabular-nums">{v.expected} {v.unit}</td>
                                            <td className="py-2 pr-3 text-right tabular-nums">{v.counted} {v.unit}</td>
                                            <td className="py-2 pr-3 text-right tabular-nums">{v.difference > 0 ? `+${v.difference}` : v.difference}</td>
                                            <td className={`py-2 ${WHAT[v.variance]?.tone ?? ""}`}>
                                                {WHAT[v.variance]?.label ?? v.variance}
                                                {v.variance === "FOUND_HERE" && v.system_location ? <span className="text-xs text-muted-foreground"> · UQMES had it at {v.system_location}</span> : null}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                        {c.status === "SUBMITTED" && (perms.has("apply_cyclecount") ? (
                            <div className="flex flex-wrap items-center gap-2">
                                <Button disabled={apply.isPending}
                                    onClick={() => apply.mutate(c.id, {
                                        onSuccess: () => toast.success("Count applied — UQMES's quantities and locations are corrected."),
                                        onError: (e) => toast.error(errorOf(e, "Could not apply the count")),
                                    })}>
                                    {apply.isPending ? "Applying…" : "Apply to UQMES"}
                                </Button>
                                <span className="text-xs text-muted-foreground">
                                    Lot quantities move by the difference counted, and things found here are moved here. Units not found are left for you to chase.
                                    Key the same differences into your ERP.
                                </span>
                            </div>
                        ) : (
                            <p className="text-xs text-muted-foreground">A lead applies the count to UQMES.</p>
                        ))}
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
