import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { FileSpreadsheet, FileText, ScanLine } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { api } from "@/lib/api/generated";
import { blobErrorMessage, downloadBlob } from "@/lib/download";
import { resolveScan } from "@/lib/scan";
import { useReportEmail } from "@/hooks/useReportEmail";
import { usePermissionSet } from "@/hooks/useMyPermissions";
import {
    COUNT_REASONS, REASON_LABEL, cycleCountOptions, useApplyCount, useRecordCount, useSendBackCount, useSubmitCount,
    type CountEntry,
} from "@/hooks/useCycleCounts";
import { apiErrorMessage } from "@/lib/api/describeApiError";

const errorOf = (err: unknown, fallback: string) =>
    apiErrorMessage(err) ?? fallback;

const WHAT: Record<string, { label: string; tone: string }> = {
    SHORT: { label: "Short", tone: "text-amber-700" },
    OVER: { label: "Over", tone: "text-sky-700" },
    MISSING: { label: "Not found", tone: "text-destructive" },
    FOUND_HERE: { label: "Found here", tone: "text-emerald-700" },
};

/** A line's allowed difference for its class, in its unit ("0" for units: any miss). */
const fmtTol = (v: { tolerance: number; unit: string }) =>
    `${Number.isInteger(v.tolerance) ? v.tolerance : v.tolerance.toFixed(2)} ${v.unit}`;

/**
 * Counting one location — or one item wherever it's kept — on a tablet. Enter what's
 * there for each lot, say of each unit whether it's there (a blank line is left
 * uncounted, never taken as missing), and scan anything found that isn't on the list (in
 * an item count, saying where). Save as you go; submit when done. A lead then gives each
 * difference a reason and applies the count — UQMES's quantities and locations are
 * corrected — and the differences wait to be keyed into the ERP.
 */
export function CycleCountPage() {
    const { countId } = useParams({ strict: false }) as { countId: string };
    const { data: c, isLoading } = useQuery(cycleCountOptions(countId));
    const record = useRecordCount();
    const submit = useSubmitCount();
    const apply = useApplyCount();
    // A lead applying lines outside their class's tolerance says why (warned, not blocked).
    const [applyNote, setApplyNote] = useState("");
    // The lead's reason per difference, keyed "LOT:<id>" / "PART:<id>" — every one needs one.
    const [reasons, setReasons] = useState<Record<string, string>>({});
    // An item count spans locations: where something found was.
    const [foundAt, setFoundAt] = useState("");
    const sendBack = useSendBackCount();
    const [recountOpen, setRecountOpen] = useState(false);
    const [recountReason, setRecountReason] = useState("");
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
        // Not on the list: something found. Saved at once, so it joins the count — in an
        // item count, at the location the counter named.
        const kind = hit.kind as "LOT" | "PART";
        const itemCount = !c.location;
        if (itemCount && !foundAt.trim()) {
            toast.error("Say where you found it first (the location box).");
            return;
        }
        let counted: string | null = kind === "PART" ? "1" : null;
        if (kind === "LOT") {
            const lot = await api.api_MaterialLots_retrieve({ params: { id: hit.id } });
            counted = String(lot.quantity_remaining ?? "");
        }
        record.mutate({ id: c.id, entries: [...entries(), {
            kind, id: hit.id, counted, ...(itemCount ? { found_at: foundAt.trim() } : {}),
        }] }, {
            onSuccess: () => toast.success(itemCount
                ? `${hit.label} found at ${foundAt.trim()} — added to the count.`
                : `${hit.label} found here — added to the count.`),
            onError: (e) => toast.error(errorOf(e, "Could not add it")),
        });
        scanRef.current?.focus();
    };

    const uncounted = c.lines.filter((l) => (draft[`${l.kind}:${l.id}`] ?? "") === "").length;
    const misses = c.variances.filter((v) => !v.within_tolerance).length;
    const unreasoned = c.variances.filter((v) => !reasons[`${v.kind}:${v.id}`]).length;
    // An item count lists where each line was kept; a location count is one place.
    const showWhere = !c.location;

    return (
        <div className="mx-auto max-w-5xl space-y-4 p-6">
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                    <div className="text-sm text-muted-foreground">
                        {c.location
                            ? <Link to="/production/locations/$locationId" params={{ locationId: c.location }} className="hover:underline">{c.location_name}</Link>
                            : <span>{c.scope_name} <span className="text-xs">(every location it&rsquo;s kept)</span></span>}
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
                    {c.apply_note && (
                        <p className="text-sm text-muted-foreground">
                            Applied with lines outside tolerance: &ldquo;{c.apply_note}&rdquo;
                        </p>
                    )}
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
                    {!c.location && (
                        <Input value={foundAt} onChange={(e) => setFoundAt(e.target.value)}
                            placeholder="Found at (location)" aria-label="Where it was found"
                            className="w-48 shrink-0" />
                    )}
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
                                        {showWhere && <th className="py-2 pr-3 font-medium">Kept at</th>}
                                        {!c.blind && <th className="py-2 pr-3 text-right font-medium">Expected</th>}
                                        <th className="py-2 font-medium">Counted</th>
                                    </tr></thead>
                                    <tbody>
                                        {lots.map((l) => (
                                            <tr key={l.id} className="border-b last:border-0">
                                                <td className="py-2 pr-3 font-mono">{l.label}{l.found_here && <Badge variant="outline" className="ml-2">found here</Badge>}</td>
                                                <td className="py-2 pr-3">{l.item || "—"}</td>
                                                {showWhere && <td className="py-2 pr-3">{l.found_here ? "found" : (l.system_location || "—")}</td>}
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
                                                <td className="w-44 py-2">
                                                    {/* Two answers, and no answer: a unit nobody looked for is
                                                        left uncounted, never taken as missing. */}
                                                    <div className="flex gap-1" role="group" aria-label={`Is ${u.label} here?`}>
                                                        {([["1", "Here"], ["0", "Not here"]] as const).map(([v, label]) => {
                                                            const on = (draft[`PART:${u.id}`] ?? "") === v;
                                                            return (
                                                                <Button key={v} size="sm" variant={on ? "default" : "outline"} aria-pressed={on}
                                                                    onClick={() => setDraft((d) => ({ ...d, [`PART:${u.id}`]: on ? "" : v }))}>
                                                                    {label}
                                                                </Button>
                                                            );
                                                        })}
                                                    </div>
                                                </td>
                                                <td className="py-2 pr-3 font-mono">{u.label}{u.found_here && <Badge variant="outline" className="ml-2">found here</Badge>}</td>
                                                <td className="py-2">{u.item || "—"}</td>
                                                {showWhere && <td className="py-2 pl-3 text-muted-foreground">{u.found_here ? "found" : (u.system_location || "—")}</td>}
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
                            <span className="text-sm text-amber-700">
                                {uncounted} not counted yet — left blank, they&rsquo;re left out of the count and their stock isn&rsquo;t touched. Enter 0 for a spot you found empty.
                            </span>
                        )}
                    </div>
                </>
            ) : (
                <Card>
                    <CardHeader className="pb-2"><CardTitle className="text-base">Differences</CardTitle></CardHeader>
                    <CardContent className="space-y-3 overflow-x-auto">
                        {(c.not_counted ?? 0) > 0 && (
                            <p className="text-sm text-amber-700">
                                {c.not_counted} {c.not_counted === 1 ? "line was" : "lines were"} not counted — left out of the differences; applying won&rsquo;t change {c.not_counted === 1 ? "it" : "them"}.
                            </p>
                        )}
                        {c.variances.length === 0 ? (
                            <p className="text-sm text-muted-foreground">Everything counted matched.</p>
                        ) : (
                            <table className="w-full text-sm">
                                <thead><tr className="border-b text-left text-muted-foreground">
                                    <th className="py-2 pr-3 font-medium">Lot / serial</th><th className="py-2 pr-3 font-medium">Item</th>
                                    <th className="py-2 pr-3 text-right font-medium">Expected</th><th className="py-2 pr-3 text-right font-medium">Counted</th>
                                    <th className="py-2 pr-3 text-right font-medium">Difference</th><th className="py-2 pr-3 font-medium">What</th>
                                    <th className="py-2 pr-3 font-medium">Tolerance</th>
                                    <th className="py-2 font-medium">Why</th>
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
                                            <td className={`py-2 pr-3 ${WHAT[v.variance]?.tone ?? ""}`}>
                                                {WHAT[v.variance]?.label ?? v.variance}
                                                {v.variance === "FOUND_HERE" && v.system_location ? <span className="text-xs text-muted-foreground"> · UQMES had it at {v.system_location}</span> : null}
                                            </td>
                                            {/* Within its ABC class's tolerance, or a miss to recount. */}
                                            <td className="py-2 text-xs">
                                                {v.within_tolerance
                                                    ? <span className="text-muted-foreground">Class {v.abc_class} · within ±{fmtTol(v)}</span>
                                                    : <span className="font-medium text-amber-700 dark:text-amber-400">Class {v.abc_class} · outside{v.kind === "LOT" ? ` ±${fmtTol(v)}` : ""}</span>}
                                            </td>
                                            {/* Why the record was off: picked when applying, shown after. */}
                                            <td className="py-2 pl-3 text-xs">
                                                {c.status === "SUBMITTED" && perms.has("apply_cyclecount") ? (
                                                    <Select value={reasons[`${v.kind}:${v.id}`] ?? ""}
                                                        onValueChange={(val) => val && setReasons((r) => ({ ...r, [`${v.kind}:${v.id}`]: val }))}>
                                                        <SelectTrigger className="h-8 w-56" aria-label={`Why, ${v.label}`}>
                                                            <SelectValue placeholder="Pick a reason" />
                                                        </SelectTrigger>
                                                        <SelectContent>
                                                            {COUNT_REASONS.map((r) => <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>)}
                                                        </SelectContent>
                                                    </Select>
                                                ) : (REASON_LABEL[v.reason ?? ""] ?? "—")}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                        {c.status === "SUBMITTED" && perms.has("apply_cyclecount") && misses > 0 && (
                            <div className="space-y-1.5 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm dark:border-amber-800 dark:bg-amber-950/30">
                                <p className="font-medium text-amber-800 dark:text-amber-300">
                                    {misses} {misses === 1 ? "line is" : "lines are"} outside tolerance for {misses === 1 ? "its" : "their"} class.
                                </p>
                                <p className="text-xs text-muted-foreground">
                                    Usually that&rsquo;s a recount: send it back. If you&rsquo;ve checked and the difference is real, say why to apply it.
                                </p>
                                <Input value={applyNote} onChange={(e) => setApplyNote(e.target.value)}
                                    placeholder="Why it's real — e.g. checked the shelf: 5 seals scrapped and not booked"
                                    aria-label="Why the difference is real" />
                            </div>
                        )}
                        {c.status === "SUBMITTED" && (perms.has("apply_cyclecount") ? (
                            <div className="flex flex-wrap items-center gap-2">
                                <Button disabled={apply.isPending || unreasoned > 0 || (misses > 0 && !applyNote.trim())}
                                    title={unreasoned > 0 ? "Give each difference a reason first" : undefined}
                                    onClick={() => apply.mutate({ id: c.id, note: applyNote.trim(), reasons }, {
                                        onSuccess: () => { setApplyNote(""); toast.success("Count applied — UQMES's quantities and locations are corrected."); },
                                        onError: (e) => toast.error(errorOf(e, "Could not apply the count")),
                                    })}>
                                    {apply.isPending ? "Applying…" : "Apply to UQMES"}
                                </Button>
                                <Button variant="outline" disabled={sendBack.isPending} onClick={() => setRecountOpen(true)}>
                                    Send back for recount
                                </Button>
                                <span className="text-xs text-muted-foreground">
                                    Lot quantities move by the difference counted, and things found here are moved here. Units not found are left for you to chase.
                                    Key the same differences into your ERP.
                                </span>
                                <Dialog open={recountOpen} onOpenChange={setRecountOpen}>
                                    <DialogContent>
                                        <DialogHeader>
                                            <DialogTitle>Send {c.count_number} back for a recount</DialogTitle>
                                            <DialogDescription>
                                                It reopens with what was entered, for the counter to correct and submit again.
                                                Nothing is applied. Your reason is kept on the count&rsquo;s record.
                                            </DialogDescription>
                                        </DialogHeader>
                                        <Input value={recountReason} onChange={(e) => setRecountReason(e.target.value)} autoFocus
                                            placeholder="Why — e.g. CC-A looks keyed wrong; recount Rack 3" aria-label="Reason for the recount" />
                                        <DialogFooter>
                                            <Button variant="outline" onClick={() => setRecountOpen(false)} disabled={sendBack.isPending}>Cancel</Button>
                                            <Button disabled={!recountReason.trim() || sendBack.isPending}
                                                onClick={() => sendBack.mutate({ id: c.id, reason: recountReason.trim() }, {
                                                    onSuccess: () => {
                                                        toast.success("Sent back — it's open for a recount, with what was entered.");
                                                        setRecountOpen(false);
                                                        setRecountReason("");
                                                    },
                                                    onError: (e) => toast.error(errorOf(e, "Could not send it back")),
                                                })}>
                                                {sendBack.isPending ? "Sending…" : "Send back"}
                                            </Button>
                                        </DialogFooter>
                                    </DialogContent>
                                </Dialog>
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
