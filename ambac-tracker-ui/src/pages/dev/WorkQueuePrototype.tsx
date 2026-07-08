/**
 * EXPERIMENT v3 (mock data, /dev/work-queue): the LIST tier AT SCALE —
 * designed for a shop with 100+ work orders in flight.
 *
 *   HOME (tiles)  →  LIST (this)  →  TRAVELER (WO detail, operator mode)
 *
 * Scale graduations applied (per the round-3 research + the 100-WO discussion):
 *  - SCOPE-FIRST: a searchable COMBOBOX (not a select) picks the work center /
 *    step, with live counts per scope — the primary navigation at scale
 *    (Odoo tabs / Epicor resource-group filter, but scalable past a dozen).
 *  - Filter rail: scope combobox + part-type combobox + late-only toggle +
 *    free search. Filters compose.
 *  - Readiness sections inside the scope: Ready now (late pinned, red edge) /
 *    Waiting on upstream (TIME-HORIZON buckets, capped) / Blocked (aging,
 *    owner-tagged — the accountability bucket).
 *  - "+N more" hints stand in for server-side pagination of the aggregate
 *    queue endpoint this page implies.
 *
 * QA lens: flat global-priority check queue with type-count chips (round-3
 * finding: never WO-grouped), now with Overdue/Today/This-week horizon headers.
 *
 * Everything renders from MOCK — actions toast instead of navigating.
 */
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList,
} from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
    Check, CheckCircle2, ChevronsUpDown, ClipboardCheck, Flame, Hourglass, Lock,
    PenLine, Search, ShieldAlert, Wrench,
} from "lucide-react";

// ---------------------------------------------------------------------------
// MOCK — sized to feel like 100+ WOs. Counts are per-scope totals; the cards
// below are the "first page" of each section.
// ---------------------------------------------------------------------------

const AREAS = [
    { id: "all", label: "All work centers", count: 137 },
    { id: "clean", label: "Cleaning Bay", count: 34 },
    { id: "recv", label: "Core Receiving", count: 15 },
    { id: "disasm", label: "Disassembly", count: 12 },
    { id: "grade", label: "Component Grading", count: 9 },
    { id: "inspect", label: "Inspection Bench", count: 12 },
    { id: "flow", label: "Flow Test Bench", count: 7 },
    { id: "asm", label: "Assembly Line", count: 19 },
    { id: "final", label: "Final Test", count: 8 },
    { id: "pack", label: "Packaging", count: 11 },
    { id: "osp", label: "Nitride Coating (OSP)", count: 10 },
] as const;

const PART_TYPES = [
    { id: "all", label: "All products" },
    { id: "cri", label: "Common Rail Injector" },
    { id: "body", label: "Injector Body" },
    { id: "noz", label: "Nozzle Assembly" },
    { id: "pump", label: "Fuel Pump M-Series" },
] as const;

type Op = {
    id: string; area: string; step: string; wo: string; partTypeId: string; partType: string;
    qty: number; due: string; priority: "high" | "normal";
    late?: boolean; certified: boolean; cert?: string;
};

const READY: Op[] = [
    { id: "r1", area: "inspect", step: "Nozzle Inspection", wo: "WO-2024-0042-A", partTypeId: "cri", partType: "Common Rail Injector", qty: 6, due: "Jul 11", priority: "high", late: true, certified: true },
    { id: "r2", area: "asm", step: "Assembly", wo: "WO-2024-0042-A", partTypeId: "cri", partType: "Common Rail Injector", qty: 4, due: "Jul 11", priority: "high", certified: true },
    { id: "r3", area: "flow", step: "Flow Testing", wo: "WO-SHOWCASE-01", partTypeId: "cri", partType: "Common Rail Injector", qty: 1, due: "Jul 12", priority: "high", certified: false, cert: "Flow Test Level 2" },
    { id: "r4", area: "clean", step: "Cleaning", wo: "WO-2024-0048", partTypeId: "body", partType: "Injector Body", qty: 12, due: "Jul 14", priority: "normal", certified: true },
    { id: "r5", area: "clean", step: "Cleaning", wo: "WO-2024-0063", partTypeId: "noz", partType: "Nozzle Assembly", qty: 30, due: "Jul 15", priority: "normal", certified: true },
    { id: "r6", area: "recv", step: "Core Receiving", wo: "WO-2024-0051", partTypeId: "cri", partType: "Common Rail Injector", qty: 8, due: "Jul 21", priority: "normal", certified: true },
    { id: "r7", area: "asm", step: "Assembly", wo: "WO-2024-0057", partTypeId: "pump", partType: "Fuel Pump M-Series", qty: 10, due: "Jul 17", priority: "normal", certified: true },
];
const READY_TOTAL = 61; // what the aggregate endpoint would report shop-wide

type WaitingOp = Op & { waitingOn: string; horizon: "today" | "week" };
const WAITING: WaitingOp[] = [
    { id: "w1", area: "final", step: "Final Test", wo: "WO-2024-0042-A", partTypeId: "cri", partType: "Common Rail Injector", qty: 6, due: "Jul 11", priority: "high", certified: true, waitingOn: "Nitride Coating (OSP) · back ~today", horizon: "today" },
    { id: "w2", area: "grade", step: "Component Grading", wo: "WO-2024-0066", partTypeId: "cri", partType: "Common Rail Injector", qty: 16, due: "Jul 16", priority: "normal", certified: true, waitingOn: "Disassembly — 16 pcs upstream", horizon: "today" },
    { id: "w3", area: "clean", step: "Cleaning", wo: "WO-2024-0059", partTypeId: "body", partType: "Injector Body", qty: 24, due: "Jul 18", priority: "normal", certified: true, waitingOn: "Component Grading — 24 pcs upstream", horizon: "week" },
];
const WAITING_TOTAL = 42;

type Blocked = {
    id: string; area: string; step: string; wo: string; reason: string; owner: string; ageDays: number;
};
const BLOCKED: Blocked[] = [
    { id: "b1", area: "inspect", step: "Nozzle Inspection", wo: "WO-2024-0044", reason: "Missing material — seal kit", owner: "Materials", ageDays: 4 },
    { id: "b2", area: "asm", step: "Assembly", wo: "WO-2024-0039", reason: "Tooling — torque fixture in repair", owner: "Lead", ageDays: 2 },
    { id: "b3", area: "flow", step: "Flow Testing", wo: "WO-2024-0031", reason: "Quality hold — pending MRB", owner: "QA", ageDays: 11 },
];

type CheckKind = "AWAITING_QA" | "SAMPLING" | "FPI";
type CheckRow = {
    id: string; kind: CheckKind; area: string; label: string; detail: string;
    wo: string; due: string; priority: "high" | "normal";
    horizon: "overdue" | "today" | "week";
};
const CHECKS: CheckRow[] = [
    { id: "c1", kind: "SAMPLING", area: "inspect", label: "Sampling check — Nozzle Inspection", detail: "1 sampled part without a PASS · aging 2 days", wo: "WO-2024-0042-A", due: "Jul 6", priority: "high", horizon: "overdue" },
    { id: "c2", kind: "AWAITING_QA", area: "flow", label: "2 parts awaiting QA — Flow Testing", detail: "INJ-0042-021, INJ-0042-017", wo: "WO-2024-0042-A", due: "Jul 8", priority: "high", horizon: "today" },
    { id: "c3", kind: "AWAITING_QA", area: "inspect", label: "1 part awaiting QA — Nozzle Inspection", detail: "INJ-SHOWCASE-001 · failed visual, 3D annotation required", wo: "WO-SHOWCASE-01", due: "Jul 8", priority: "high", horizon: "today" },
    { id: "c4", kind: "FPI", area: "final", label: "First-piece sign-off — Final Test", detail: "designated part INJ-0042-018", wo: "WO-2024-0042-A", due: "Jul 10", priority: "high", horizon: "week" },
    { id: "c5", kind: "SAMPLING", area: "clean", label: "Sampling check — Cleaning", detail: "2 sampled parts without a PASS", wo: "WO-2024-0048", due: "Jul 15", priority: "normal", horizon: "week" },
];

const PRIORITY_TONE: Record<string, string> = {
    high: "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300",
};
const CHECK_META: Record<CheckKind, { label: string; icon: typeof Search }> = {
    AWAITING_QA: { label: "Awaiting QA", icon: ClipboardCheck },
    SAMPLING: { label: "Sampling", icon: Search },
    FPI: { label: "First piece", icon: PenLine },
};
const HORIZON_LABEL = { overdue: "Overdue", today: "Due today", week: "This week" } as const;

const say = (msg: string) => toast.info(msg, { description: "Prototype — no real action taken." });

// ---------------------------------------------------------------------------
// Searchable combobox (Popover + Command) — the scale-proof scope picker.
// ---------------------------------------------------------------------------

function Combobox({
    value, onChange, options, placeholder, width = "w-60",
}: {
    value: string;
    onChange: (v: string) => void;
    options: ReadonlyArray<{ id: string; label: string; count?: number }>;
    placeholder: string;
    width?: string;
}) {
    const [open, setOpen] = useState(false);
    const current = options.find((o) => o.id === value);
    return (
        <Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
                <Button variant="outline" role="combobox" aria-expanded={open} className={`h-12 justify-between ${width}`}>
                    <span className="truncate">
                        {current?.label ?? placeholder}
                        {current?.count != null && <span className="ml-1.5 text-muted-foreground">({current.count})</span>}
                    </span>
                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
            </PopoverTrigger>
            <PopoverContent className="w-64 p-0" align="start">
                <Command>
                    <CommandInput placeholder={placeholder} />
                    <CommandList>
                        <CommandEmpty>Nothing matches.</CommandEmpty>
                        <CommandGroup>
                            {options.map((o) => (
                                <CommandItem key={o.id} value={o.label} onSelect={() => { onChange(o.id); setOpen(false); }}>
                                    <Check className={`mr-2 h-4 w-4 ${o.id === value ? "opacity-100" : "opacity-0"}`} />
                                    <span className="min-w-0 flex-1 truncate">{o.label}</span>
                                    {o.count != null && <span className="ml-2 text-xs text-muted-foreground">{o.count}</span>}
                                </CommandItem>
                            ))}
                        </CommandGroup>
                    </CommandList>
                </Command>
            </PopoverContent>
        </Popover>
    );
}

// ---------------------------------------------------------------------------
// Operator lens — scoped readiness sections + blocked bucket.
// ---------------------------------------------------------------------------

function OpCard({ o }: { o: Op }) {
    return (
        <div className={`flex items-center gap-3 rounded-xl border p-3 ${o.late ? "border-l-4 border-l-red-500" : ""} ${o.certified ? "" : "opacity-60"}`}>
            <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                    <span className="truncate text-base font-medium">{o.step}</span>
                    {!o.certified && <Lock className="h-4 w-4 shrink-0 text-muted-foreground" />}
                    {o.late && <Badge variant="destructive">late</Badge>}
                    {PRIORITY_TONE[o.priority] && <Badge className={PRIORITY_TONE[o.priority]}>{o.priority}</Badge>}
                </div>
                <div className="truncate text-sm text-muted-foreground">
                    {o.partType} · <span className="font-mono">{o.wo}</span> · <b className="text-foreground">{o.qty}</b> pcs · due {o.due}
                    {o.certified ? "" : ` · needs ${o.cert}`}
                </div>
                {"waitingOn" in o && (
                    <div className="mt-0.5 flex items-center gap-1.5 truncate text-xs text-muted-foreground">
                        <Hourglass className="h-3 w-3 shrink-0" /> waiting on {(o as WaitingOp).waitingOn}
                    </div>
                )}
            </div>
            <Button variant="ghost" size="sm" onClick={() => say(`Would open the traveler for ${o.wo}`)}>Traveler</Button>
            {"waitingOn" in o ? (
                <Button size="lg" className="h-12" variant="outline" onClick={() => say(`Would open prep for ${o.step} (instructions, setup sheet)`)}>Prep</Button>
            ) : (
                <Button size="lg" className="h-12" disabled={!o.certified} onClick={() => say(`Would open Start Work for ${o.step} on ${o.wo}`)}>Start</Button>
            )}
        </div>
    );
}

function OperatorLens({ area, partType, lateOnly, q }: { area: string; partType: string; lateOnly: boolean; q: string }) {
    const match = (o: Op) =>
        (area === "all" || o.area === area) &&
        (partType === "all" || o.partTypeId === partType) &&
        (!lateOnly || o.late === true) &&
        (!q || `${o.step} ${o.wo} ${o.partType}`.toLowerCase().includes(q.toLowerCase()));

    const ready = READY.filter(match);
    const waiting = WAITING.filter((w) => match(w) && !lateOnly);
    const blocked = BLOCKED.filter((b) => (area === "all" || b.area === area) && (!q || `${b.step} ${b.wo} ${b.reason}`.toLowerCase().includes(q.toLowerCase())));
    const waitToday = waiting.filter((w) => w.horizon === "today");
    const waitWeek = waiting.filter((w) => w.horizon === "week");

    return (
        <div className="space-y-5">
            <section className="space-y-2">
                <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    <Wrench className="h-3.5 w-3.5" /> Ready now
                    <Badge variant="secondary">{area === "all" && !lateOnly && !q && partType === "all" ? READY_TOTAL : ready.length}</Badge>
                </div>
                {ready.map((o) => <OpCard key={o.id} o={o} />)}
                {ready.length === 0 && <p className="text-sm text-muted-foreground">Nothing ready in this scope.</p>}
                {area === "all" && !lateOnly && !q && partType === "all" && ready.length < READY_TOTAL && (
                    <button className="text-xs text-muted-foreground underline-offset-4 hover:underline" onClick={() => say("Would load the next page from the queue endpoint")}>
                        +{READY_TOTAL - ready.length} more — showing highest priority first
                    </button>
                )}
            </section>

            {!lateOnly && (
                <section className="space-y-2">
                    <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                        <Hourglass className="h-3.5 w-3.5" /> Waiting on upstream
                        <Badge variant="secondary">{area === "all" && !q && partType === "all" ? WAITING_TOTAL : waiting.length}</Badge>
                        <span className="font-normal normal-case">— stage ahead</span>
                    </div>
                    {waitToday.length > 0 && (
                        <>
                            <div className="text-[11px] font-medium text-muted-foreground">Arriving today</div>
                            {waitToday.map((o) => <OpCard key={o.id} o={o} />)}
                        </>
                    )}
                    {waitWeek.length > 0 && (
                        <>
                            <div className="text-[11px] font-medium text-muted-foreground">This week</div>
                            {waitWeek.map((o) => <OpCard key={o.id} o={o} />)}
                        </>
                    )}
                    {waiting.length === 0 && <p className="text-sm text-muted-foreground">Nothing inbound in this scope.</p>}
                    {area === "all" && !q && partType === "all" && (
                        <button className="text-xs text-muted-foreground underline-offset-4 hover:underline" onClick={() => say("Would expand the horizon (next 2 weeks)")}>
                            +{WAITING_TOTAL - waiting.length} more beyond this week
                        </button>
                    )}
                </section>
            )}

            <section className="space-y-2">
                <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    <ShieldAlert className="h-3.5 w-3.5" /> Blocked
                    <Badge variant="secondary">{blocked.length}</Badge>
                    <span className="font-normal normal-case">— owned, aging, escalating</span>
                </div>
                {blocked.map((b) => (
                    <div key={b.id} className={`flex items-center gap-3 rounded-xl border p-3 ${b.ageDays >= 7 ? "border-l-4 border-l-red-500" : "border-l-4 border-l-amber-400"}`}>
                        <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2">
                                <span className="truncate text-sm font-medium">{b.step}</span>
                                <Badge variant={b.ageDays >= 7 ? "destructive" : "outline"}>{b.ageDays}d</Badge>
                            </div>
                            <div className="truncate text-xs text-muted-foreground">
                                {b.reason} · <span className="font-mono">{b.wo}</span> · owner: <b>{b.owner}</b>
                            </div>
                        </div>
                        <Button variant="ghost" size="sm" onClick={() => say(`Would open the traveler for ${b.wo}`)}>Traveler</Button>
                        <Button size="sm" variant="outline" onClick={() => say(`Would nudge ${b.owner} (escalation event)`)}>Nudge</Button>
                    </div>
                ))}
                {blocked.length === 0 && <p className="text-sm text-muted-foreground">Nothing blocked in this scope.</p>}
            </section>
        </div>
    );
}

// ---------------------------------------------------------------------------
// QA lens — flat global-priority check queue, horizon headers, type chips.
// ---------------------------------------------------------------------------

function QaLens({ area, q }: { area: string; q: string }) {
    const [kindFilter, setKindFilter] = useState<CheckKind | "ALL">("ALL");
    const counts = useMemo(() => {
        const c: Record<CheckKind, number> = { AWAITING_QA: 0, SAMPLING: 0, FPI: 0 };
        for (const r of CHECKS) c[r.kind]++;
        return c;
    }, []);

    const rows = CHECKS.filter(
        (r) =>
            (kindFilter === "ALL" || r.kind === kindFilter) &&
            (area === "all" || r.area === area) &&
            (!q || `${r.label} ${r.wo} ${r.detail}`.toLowerCase().includes(q.toLowerCase())),
    );
    const byHorizon = (h: CheckRow["horizon"]) => rows.filter((r) => r.horizon === h);

    return (
        <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
                <Button size="sm" variant={kindFilter === "ALL" ? "default" : "outline"} onClick={() => setKindFilter("ALL")}>
                    All <Badge variant="secondary" className="ml-1.5">{CHECKS.length}</Badge>
                </Button>
                {(Object.keys(CHECK_META) as CheckKind[]).map((k) => (
                    <Button key={k} size="sm" variant={kindFilter === k ? "default" : "outline"} onClick={() => setKindFilter(k)}>
                        {CHECK_META[k].label} <Badge variant="secondary" className="ml-1.5">{counts[k]}</Badge>
                    </Button>
                ))}
            </div>

            {(["overdue", "today", "week"] as const).map((h) => {
                const group = byHorizon(h);
                if (group.length === 0) return null;
                return (
                    <section key={h} className="space-y-2">
                        <div className={`text-[11px] font-medium uppercase tracking-wide ${h === "overdue" ? "text-red-600 dark:text-red-400" : "text-muted-foreground"}`}>
                            {HORIZON_LABEL[h]} · {group.length}
                        </div>
                        {group.map((r) => {
                            const Icon = CHECK_META[r.kind].icon;
                            return (
                                <div key={r.id} className={`flex items-center gap-3 rounded-xl border p-3 ${h === "overdue" ? "border-l-4 border-l-red-500" : ""}`}>
                                    <Icon className="h-4 w-4 shrink-0 text-muted-foreground" />
                                    <div className="min-w-0 flex-1">
                                        <div className="flex items-center gap-2">
                                            <span className="truncate text-sm font-medium">{r.label}</span>
                                            {h === "overdue" && <Badge variant="destructive">overdue</Badge>}
                                            {PRIORITY_TONE[r.priority] && <Badge className={PRIORITY_TONE[r.priority]}>{r.priority}</Badge>}
                                        </div>
                                        <div className="truncate text-xs text-muted-foreground">
                                            {r.detail} · <span className="font-mono">{r.wo}</span> · due {r.due}
                                        </div>
                                    </div>
                                    <Button variant="ghost" size="sm" onClick={() => say(`Would open the traveler for ${r.wo}`)}>Traveler</Button>
                                    <Button size="lg" className="h-11" variant={r.kind === "FPI" ? "outline" : "default"}
                                        onClick={() => say(`Would open the ${r.kind === "FPI" ? "FPI sign-off" : "inspection runtime"} for this check`)}>
                                        {r.kind === "FPI" ? "Sign off" : "Inspect"}
                                    </Button>
                                </div>
                            );
                        })}
                    </section>
                );
            })}
            {rows.length === 0 && <p className="p-4 text-sm text-muted-foreground">Nothing matches.</p>}
        </div>
    );
}

// ---------------------------------------------------------------------------
// Page — lens tabs + composable filter rail (scope combobox first).
// ---------------------------------------------------------------------------

export function WorkQueuePrototype() {
    const [lens, setLens] = useState<"work" | "checks">("work");
    const [area, setArea] = useState<string>("all");
    const [partType, setPartType] = useState<string>("all");
    const [lateOnly, setLateOnly] = useState(false);
    const [q, setQ] = useState("");

    return (
        <div className="mx-auto max-w-3xl space-y-4 p-4">
            <div>
                <h1 className="text-2xl font-semibold tracking-tight">Queue</h1>
                <p className="text-sm text-muted-foreground">
                    Scope first, then readiness. Top of Ready = the right next job in this scope.
                </p>
            </div>

            <div className="flex items-center gap-2">
                <Button size="lg" className="h-12" variant={lens === "work" ? "default" : "outline"} onClick={() => setLens("work")}>
                    <Wrench className="mr-2 h-4 w-4" /> Work queue
                </Button>
                <Button size="lg" className="h-12" variant={lens === "checks" ? "default" : "outline"} onClick={() => setLens("checks")}>
                    <CheckCircle2 className="mr-2 h-4 w-4" /> Checks due
                    <Badge variant="secondary" className="ml-2">{CHECKS.length}</Badge>
                </Button>
            </div>

            {/* Filter rail — scope is primary; everything composes. */}
            <div className="flex flex-wrap items-center gap-2">
                <Combobox value={area} onChange={setArea} options={AREAS} placeholder="Work center / step…" />
                {lens === "work" && (
                    <>
                        <Combobox value={partType} onChange={setPartType} options={PART_TYPES} placeholder="Product…" width="w-52" />
                        <Button size="lg" className="h-12" variant={lateOnly ? "destructive" : "outline"} onClick={() => setLateOnly((v) => !v)}>
                            <Flame className="mr-1.5 h-4 w-4" /> Late only
                        </Button>
                    </>
                )}
                <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search step, WO…" className="h-12 min-w-40 flex-1" />
            </div>

            {lens === "work"
                ? <OperatorLens area={area} partType={partType} lateOnly={lateOnly} q={q} />
                : <QaLens area={area} q={q} />}
        </div>
    );
}

export default WorkQueuePrototype;
