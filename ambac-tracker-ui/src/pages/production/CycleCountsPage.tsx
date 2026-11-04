import { useState } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { queryOptions, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { FileSpreadsheet, ListChecks, TrendingUp } from "lucide-react";
import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import { Combobox } from "@/components/ui/combobox";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { usePermissionSet } from "@/hooks/useMyPermissions";
import {
    REASON_LABEL, accuracyTrendOptions, countAccuracyOptions, cycleCountsOptions, dueForCountOptions, missingUnitsOptions,
    toKeyOptions, useMarkKeyed, useResolveMissing, useStartCount,
    type CountAccuracy, type CycleCount, type DueForCount, type MissingUnit,
} from "@/hooks/useCycleCounts";
import { api } from "@/lib/api/generated";
import { apiErrorMessage } from "@/lib/api/describeApiError";
import { blobErrorMessage, downloadBlob } from "@/lib/download";

/**
 * Cycle counts — the working surface for counting stock (user decision 2026-11-04):
 *
 *  - **Due**: what to count next under its ABC class (schedule by item, walk by
 *    location), each with Count buttons that start the count straight from the row;
 *  - **Waiting for you**: submitted counts a lead applies (a reason per difference) or
 *    sends back; **In progress**: counts still being counted;
 *  - **Missing units**: units a count didn't find, until they turn up or someone says
 *    what became of them;
 *  - **To key into Glovia**: applied differences not yet carried into the ERP — one
 *    sheet across counts, then marked keyed;
 *  - **All counts**.
 *
 * A count is of one location, or of one material or part type wherever it's kept.
 */
export function CycleCountsPage() {
    const perms = usePermissionSet();
    const lead = perms.has("apply_cyclecount");
    const { data, isLoading } = useQuery(cycleCountsOptions());
    const counts = data?.results ?? [];
    const { data: due } = useQuery(dueForCountOptions());
    const { data: accuracy } = useQuery(countAccuracyOptions(90));
    const { data: missing } = useQuery(missingUnitsOptions());
    const { data: toKey } = useQuery(toKeyOptions());
    const [startOpen, setStartOpen] = useState(false);
    const [tab, setTab] = useState<string | null>(null);

    const waiting = counts.filter((c) => c.status === "SUBMITTED");
    const inProgress = counts.filter((c) => c.status === "OPEN");

    return (
        <div className="mx-auto max-w-5xl space-y-4 p-6">
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                    <h1 className="text-2xl font-semibold tracking-tight">Cycle counts</h1>
                    <p className="text-sm text-muted-foreground">
                        Count a location, or one item wherever it&rsquo;s kept. What&rsquo;s due follows each
                        item&rsquo;s count class.
                    </p>
                </div>
                <Button onClick={() => setStartOpen(true)}><ListChecks className="mr-1 h-4 w-4" /> Start a count</Button>
            </div>
            {accuracy && <AccuracyStrip accuracy={accuracy} />}

            {/* Until someone picks a tab, a lead with counts waiting lands on them — decided as
                the counts (and permissions) arrive, not frozen at the first render. */}
            <Tabs value={tab ?? (lead && waiting.length ? "waiting" : "due")} onValueChange={(v) => setTab(String(v))}>
                <TabsList className="flex-wrap">
                    <TabsTrigger value="due">Due{due?.length ? ` (${due.length})` : ""}</TabsTrigger>
                    <TabsTrigger value="waiting">Waiting for a lead{waiting.length ? ` (${waiting.length})` : ""}</TabsTrigger>
                    <TabsTrigger value="progress">In progress{inProgress.length ? ` (${inProgress.length})` : ""}</TabsTrigger>
                    <TabsTrigger value="missing">Missing units{missing?.length ? ` (${missing.length})` : ""}</TabsTrigger>
                    <TabsTrigger value="key">To key into Glovia{toKey?.length ? ` (${toKey.length})` : ""}</TabsTrigger>
                    <TabsTrigger value="all">All counts</TabsTrigger>
                </TabsList>
                <TabsContent value="due"><DueForCount rows={due ?? []} /></TabsContent>
                <TabsContent value="waiting">
                    <CountTable rows={waiting} loading={isLoading}
                        empty="Nothing waiting — submitted counts appear here for a lead to apply or send back." />
                </TabsContent>
                <TabsContent value="progress">
                    <CountTable rows={inProgress} loading={isLoading} empty="No count is being counted right now." />
                </TabsContent>
                <TabsContent value="missing"><MissingUnits rows={missing ?? []} canResolve={lead} /></TabsContent>
                <TabsContent value="key"><ToKey rows={toKey ?? []} canMark={lead} /></TabsContent>
                <TabsContent value="all"><CountTable rows={counts} loading={isLoading} empty="No counts yet." /></TabsContent>
            </Tabs>
            <StartCountDialog open={startOpen} onOpenChange={setStartOpen} />
        </div>
    );
}

// --- start ------------------------------------------------------------------------------

const locationsOptions = () =>
    queryOptions({
        queryKey: ["locations", "pick"],
        queryFn: () => api.api_StorageLocations_list({ queries: { limit: 500 } }),
    });
const materialsPickOptions = () =>
    queryOptions({
        queryKey: ["materials", "pick"],
        queryFn: () => api.api_Materials_list({ queries: { limit: 500 } }),
    });
const partTypesPickOptions = () =>
    queryOptions({
        queryKey: ["part-types", "select"],
        queryFn: () => api.api_PartTypes_select_list(),
    });

/** Start counting a location, or a material or part type wherever it's kept. */
function StartCountDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
    const navigate = useNavigate();
    const start = useStartCount();
    // Counts are scheduled by item, so an item count is the default; a location is the alternative.
    const [what, setWhat] = useState<"location" | "item">("item");
    const [location, setLocation] = useState<string | null>(null);
    const [item, setItem] = useState<string | null>(null);  // "MATERIAL:<id>" / "PART_TYPE:<id>"
    const [blind, setBlind] = useState(false);
    const { data: locs } = useQuery({ ...locationsOptions(), enabled: open });
    const { data: mats } = useQuery({ ...materialsPickOptions(), enabled: open && what === "item" });
    const { data: pts } = useQuery({ ...partTypesPickOptions(), enabled: open && what === "item" });
    const itemOptions = [
        ...((pts ?? []) as { id: string; name: string }[]).map((p) => ({ value: `PART_TYPE:${p.id}`, label: p.name, group: "Part types" })),
        ...(mats?.results ?? []).map((m) => ({ value: `MATERIAL:${m.id}`, label: m.name, group: "Materials" })),
    ];
    const go = () => {
        const body = what === "location"
            ? { location: location ?? "", blind }
            : item?.startsWith("MATERIAL:") ? { material: item.slice(9), blind } : { part_type: (item ?? "").slice(10), blind };
        start.mutate(body, {
            onSuccess: (c: CycleCount) => { onOpenChange(false); void navigate({ to: "/production/cycle-counts/$countId", params: { countId: c.id } }); },
            onError: (e) => toast.error(apiErrorMessage(e) ?? "Couldn't start the count"),
        });
    };
    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Start a count</DialogTitle>
                    <DialogDescription>
                        An item: that part type or material in every location it&rsquo;s kept. A location:
                        everything kept there.
                    </DialogDescription>
                </DialogHeader>
                <div className="space-y-3">
                    <div className="flex gap-2">
                        <Button size="sm" variant={what === "item" ? "default" : "outline"} onClick={() => setWhat("item")}>An item</Button>
                        <Button size="sm" variant={what === "location" ? "default" : "outline"} onClick={() => setWhat("location")}>A location</Button>
                    </div>
                    {what === "location" ? (
                        <Combobox value={location} onChange={setLocation}
                            options={(locs?.results ?? []).map((l) => ({ value: String(l.id), label: (l as { path?: string }).path ?? l.name }))}
                            placeholder="Pick a location" searchPlaceholder="Search locations…" emptyText="No location by that name." />
                    ) : (
                        <Combobox value={item} onChange={setItem} options={itemOptions}
                            placeholder="Pick a part type or material" searchPlaceholder="Search items…" emptyText="Nothing by that name." />
                    )}
                    <div className="flex items-center gap-2">
                        <Switch id="start-blind" checked={blind} onCheckedChange={setBlind} />
                        <Label htmlFor="start-blind" className="text-sm">Blind — hide the expected quantities while counting</Label>
                    </div>
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
                    <Button disabled={start.isPending || (what === "location" ? !location : !item)} onClick={go}>Start counting</Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

// --- lists -------------------------------------------------------------------------------

function CountTable({ rows, loading, empty }: { rows: CycleCount[]; loading: boolean; empty: string }) {
    return (
        <div className="overflow-x-auto rounded-lg border">
            <table className="w-full text-sm">
                <thead>
                    <tr className="border-b text-left text-muted-foreground">
                        <th className="px-3 py-2 font-medium">Count</th>
                        <th className="px-3 py-2 font-medium">Of</th>
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
                            <td className="px-3 py-2">
                                {c.scope_name}
                                {c.scope !== "LOCATION" && <span className="ml-1 text-xs text-muted-foreground">item, every location</span>}
                            </td>
                            <td className="px-3 py-2"><Badge variant={c.status === "APPLIED" ? "default" : "outline"}>{c.status_display}</Badge></td>
                            <td className="px-3 py-2 text-right tabular-nums">{c.status === "OPEN" ? "—" : c.variances.length}</td>
                            <td className="px-3 py-2 text-muted-foreground">{new Date(c.created_at).toLocaleDateString()} · {c.started_by_name ?? "—"}</td>
                        </tr>
                    ))}
                    {!loading && rows.length === 0 && (
                        <tr><td colSpan={5} className="px-3 py-8 text-center text-muted-foreground">{empty}</td></tr>
                    )}
                </tbody>
            </table>
        </div>
    );
}

/** Inventory record accuracy per class, and the commonest reasons records were off. */
function AccuracyStrip({ accuracy }: { accuracy: CountAccuracy }) {
    const [showTrend, setShowTrend] = useState(false);
    const cells = (["A", "B", "C"] as const).map((c) => ({ c, ...accuracy[c] }));
    const reasons = Object.entries(accuracy.by_reason ?? {}).sort((a, b) => b[1] - a[1]).slice(0, 3);
    return (
        <div className="space-y-1 rounded-lg border px-3 py-2 text-sm">
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
                <span className="text-muted-foreground">Count accuracy, last {accuracy.days} days:</span>
                {cells.map(({ c, pct, counted, hits }) => (
                    <span key={c} title={counted ? `${hits} of ${counted} counted lines within tolerance` : "Nothing counted"}>
                        <span className="font-medium">{c}</span>{" "}
                        <span className="tabular-nums">{pct == null ? "—" : `${pct}%`}</span>
                    </span>
                ))}
                <Button size="sm" variant="ghost" className="ml-auto h-7" aria-expanded={showTrend}
                    onClick={() => setShowTrend((s) => !s)}>
                    <TrendingUp className="mr-1 h-4 w-4" /> {showTrend ? "Hide trend" : "12-month trend"}
                </Button>
            </div>
            {reasons.length > 0 && (
                <div className="text-xs text-muted-foreground">
                    Off because: {reasons.map(([code, n]) => `${REASON_LABEL[code] ?? code} (${n})`).join(" · ")}
                </div>
            )}
            {showTrend && <AccuracyTrend />}
        </div>
    );
}

const CLASS_COLOR = { A: "var(--chart-1)", B: "var(--chart-2)", C: "var(--chart-3)" } as const;
const trendConfig: ChartConfig = {
    A: { label: "Class A", color: CLASS_COLOR.A },
    B: { label: "Class B", color: CLASS_COLOR.B },
    C: { label: "Class C", color: CLASS_COLOR.C },
};

/** Accuracy per class month by month, as each count was judged when applied. Dots, not
 *  just lines: most months count little, and a month with nothing counted is a gap. */
function AccuracyTrend() {
    const { data, isLoading } = useQuery(accuracyTrendOptions(12));
    if (isLoading || !data) return <div className="h-56" />;
    const rows = data.map((m) => ({
        month: m.month, A: m.A.pct, B: m.B.pct, C: m.C.pct,
        n: { A: m.A, B: m.B, C: m.C } as Record<"A" | "B" | "C", { counted: number; hits: number }>,
    }));
    if (rows.every((r) => r.A == null && r.B == null && r.C == null)) {
        return <p className="py-3 text-xs text-muted-foreground">No counts applied in the last 12 months.</p>;
    }
    const monthLabel = (v: string) => {
        const [y, m] = v.split("-").map(Number);
        return new Date(y, m - 1, 1).toLocaleDateString(undefined, { month: "short", year: "2-digit" });
    };
    return (
        <ChartContainer config={trendConfig} className="h-56 w-full pt-2">
            <LineChart data={rows} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="month" tickFormatter={monthLabel} tickLine={false} axisLine={false} tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 100]} tickFormatter={(v: number) => `${v}%`} tickLine={false} axisLine={false}
                    tick={{ fontSize: 11 }} width={40} />
                <ChartTooltip content={<ChartTooltipContent
                    labelFormatter={(v) => monthLabel(String(v))}
                    formatter={(value, name, item) => {
                        const cls = name as "A" | "B" | "C";
                        const t = (item.payload as (typeof rows)[number]).n[cls];
                        return `Class ${cls}: ${value}% (${t.hits} of ${t.counted} lines)`;
                    }} />} />
                {(["A", "B", "C"] as const).map((c) => (
                    <Line key={c} dataKey={c} stroke={CLASS_COLOR[c]} strokeWidth={2} type="monotone"
                        dot={{ r: 3 }} connectNulls={false} isAnimationActive={false} />
                ))}
            </LineChart>
        </ChartContainer>
    );
}

/** What's due for counting: an item whose stock somewhere hasn't been counted within its
 *  class's interval. Count the item everywhere it's kept, or one of its locations whole. */
function DueForCount({ rows }: { rows: DueForCount[] }) {
    const navigate = useNavigate();
    const start = useStartCount();
    const begin = (body: { location?: string; material?: string; part_type?: string }) =>
        start.mutate({ ...body, blind: false }, {
            onSuccess: (c: CycleCount) => void navigate({ to: "/production/cycle-counts/$countId", params: { countId: c.id } }),
            onError: (e) => toast.error(apiErrorMessage(e) ?? "Couldn't start the count"),
        });
    if (rows.length === 0) {
        return <p className="py-4 text-sm text-muted-foreground">Nothing due — every item&rsquo;s stock has been counted within its class&rsquo;s interval.</p>;
    }
    return (
        <div className="overflow-x-auto rounded-lg border">
            <table className="w-full text-sm">
                <thead>
                    <tr className="border-b text-left text-muted-foreground">
                        <th className="px-3 py-2 font-medium">Item</th>
                        <th className="px-3 py-2 font-medium">Class</th>
                        <th className="px-3 py-2 font-medium">Due</th>
                        <th className="px-3 py-2 font-medium">Count</th>
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
                                <div className="flex flex-wrap items-center gap-1.5">
                                    <Button size="sm" disabled={start.isPending}
                                        title={`Count ${r.name} in every location it's kept`}
                                        onClick={() => begin(r.kind === "MATERIAL" ? { material: String(r.id) } : { part_type: String(r.id) })}>
                                        Count this item
                                    </Button>
                                    {r.locations.length > 0 && <span className="text-xs text-muted-foreground">or a whole location:</span>}
                                    {r.locations.map((l) => (
                                        <Button key={l.location_id} size="sm" variant="ghost" disabled={start.isPending}
                                            title={`Count everything at ${l.location}`}
                                            onClick={() => begin({ location: String(l.location_id) })}>
                                            {l.location}
                                        </Button>
                                    ))}
                                </div>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

/** Units a count didn't find, until they turn up or someone says what became of them. */
function MissingUnits({ rows, canResolve }: { rows: MissingUnit[]; canResolve: boolean }) {
    const resolve = useResolveMissing();
    const [notes, setNotes] = useState<Record<string, string>>({});
    if (rows.length === 0) {
        return <p className="py-4 text-sm text-muted-foreground">Nothing missing — every unit a count didn&rsquo;t find has turned up or been accounted for.</p>;
    }
    return (
        <div className="space-y-2">
            <p className="text-xs text-muted-foreground">
                A unit comes off this list when it turns up — moved, placed or found in a later count — when it leaves for
                good, or when you say what became of it.
            </p>
            <div className="overflow-x-auto rounded-lg border">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="border-b text-left text-muted-foreground">
                            <th className="px-3 py-2 font-medium">Unit</th>
                            <th className="px-3 py-2 font-medium">Expected at</th>
                            <th className="px-3 py-2 font-medium">Not found in</th>
                            <th className="px-3 py-2 font-medium">What became of it</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows.map((m) => {
                            const key = `${m.count_id}:${m.part_id}`;
                            return (
                                <tr key={key} className="border-b last:border-0 align-top">
                                    <td className="px-3 py-2"><span className="font-mono">{m.serial}</span><div className="text-xs text-muted-foreground">{m.item}</div></td>
                                    <td className="px-3 py-2">{m.expected_at || "—"}</td>
                                    <td className="px-3 py-2">
                                        <Link to="/production/cycle-counts/$countId" params={{ countId: String(m.count_id) }} className="font-mono hover:underline">{m.count_number}</Link>
                                        <div className="text-xs text-muted-foreground">{new Date(m.applied_at).toLocaleDateString()}{m.reason ? ` · ${REASON_LABEL[m.reason] ?? m.reason}` : ""}</div>
                                    </td>
                                    <td className="px-3 py-2">
                                        {canResolve ? (
                                            <div className="flex gap-1.5">
                                                <Input value={notes[key] ?? ""} onChange={(e) => setNotes((n) => ({ ...n, [key]: e.target.value }))}
                                                    placeholder="e.g. Found in rework; shipped unbooked" aria-label={`What became of ${m.serial}`} className="h-8" />
                                                <Button size="sm" disabled={!notes[key]?.trim() || resolve.isPending}
                                                    onClick={() => resolve.mutate({ countId: String(m.count_id), part: String(m.part_id), note: notes[key].trim() }, {
                                                        onSuccess: () => toast.success(`${m.serial} accounted for.`),
                                                        onError: (e) => toast.error(apiErrorMessage(e) ?? "Couldn't save it"),
                                                    })}>
                                                    Resolve
                                                </Button>
                                            </div>
                                        ) : <span className="text-muted-foreground">Still missing</span>}
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

/** Applied differences not yet carried into the ERP: one sheet across counts, then marked
 *  keyed once someone has entered them in Glovia. */
function ToKey({ rows, canMark }: { rows: CycleCount[]; canMark: boolean }) {
    const mark = useMarkKeyed();
    if (rows.length === 0) {
        return <p className="py-4 text-sm text-muted-foreground">Nothing to key — every applied count&rsquo;s differences are in the ERP.</p>;
    }
    const lines = rows.reduce((n, c) => n + c.variances.length, 0);
    return (
        <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm">{lines} difference{lines === 1 ? "" : "s"} from {rows.length} count{rows.length === 1 ? "" : "s"} to key into Glovia.</span>
                <Button size="sm" variant="outline" onClick={async () => {
                    try {
                        const resp = await api.axios.get("/api/CycleCounts/to-key-xlsx/", { responseType: "blob" });
                        downloadBlob(resp.data, "count_differences_to_key.xlsx");
                    } catch (e) {
                        toast.error(await blobErrorMessage(e, "Couldn't build the sheet."));
                    }
                }}>
                    <FileSpreadsheet className="mr-1 h-4 w-4" /> Download the sheet
                </Button>
                {canMark && (
                    <Button size="sm" disabled={mark.isPending}
                        onClick={() => mark.mutate(rows.map((c) => c.id), {
                            onSuccess: () => toast.success("Marked keyed into the ERP."),
                            onError: (e) => toast.error(apiErrorMessage(e) ?? "Couldn't mark them"),
                        })}>
                        Mark all keyed
                    </Button>
                )}
            </div>
            <CountTable rows={rows} loading={false} empty="" />
        </div>
    );
}
