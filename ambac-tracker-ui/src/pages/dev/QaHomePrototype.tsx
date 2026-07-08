/**
 * EXPERIMENT (mock data, /dev/qa-home): the "perfect" QA inspector home.
 * Companion to /dev/operator-home; grounded in the round-4 research
 * (eQMS dashboards + shop-floor QC tools, 2026-07).
 *
 * Design decisions this mock encodes:
 *  - TASK INBOX, not metrics dashboard (near-unanimous across eQMS: Veeva,
 *    Qualio, Intelex, ZenQMS — charts live in reports, not on home).
 *  - ONE flat inspection list + clickable filter-stat chips (Qualio pattern),
 *    never sectioned into half-empty panels, never grouped by work order.
 *  - First-piece requests are QUEUE-JUMPERS with machine-down semantics: a
 *    pinned banner with a live "machine waiting" timer, not a worklist row
 *    (andon TTR model — during this wait a machine + operator sit idle).
 *  - Four-state due dot per row (Veeva exactly): red overdue / orange soon /
 *    green ok / gray no date. Aging is bucketed, never "40 days" raw.
 *  - Sampling shown as the ANSWER ("n=13 · Ac 1"), never the code tables
 *    (1factory). Severity state is a labeled badge WITH the switch-back rule
 *    — no product surveyed shows the countdown to the inspector; open ground.
 *  - Blocked rows sink but stay counted, with a reason chip (gauge out for
 *    cal, awaiting CoC) — separates "inspector is slow" from "upstream owes
 *    something", which protects inspectors from bad metrics.
 *  - Receiving triage: "needed by WO-x" beats FIFO; supplier risk drives
 *    sampling depth (the severity badge), NOT queue position.
 *  - "My quality actions" is uniPoint To-Do semantics: row = deep link,
 *    re-assign from the row; plus a Veeva "available to claim" group for
 *    group-eligible approvals nobody has picked up.
 *  - Personal calibration nag ("gauges you used this week are due") pre-empts
 *    the point-of-use blocking gate.
 *  - Footer is passive self-confirmation, never throughput-vs-goal
 *    (inspector pace pressure incentivizes escapes).
 */
import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
    AlertTriangle, ArrowRight, CheckCircle2, ClipboardCheck, Clock, FlaskConical,
    Gauge, Inbox, PackageSearch, PauseCircle, PenLine, Ruler, Siren,
} from "lucide-react";

// ---------------------------------------------------------------------------
// MOCK — shapes are the wishlist for the real backing.
// ---------------------------------------------------------------------------

type InspType = "receiving" | "in-process" | "final" | "fpi";
type DueTone = "red" | "orange" | "green" | "gray";

type InspRow = {
    id: string; type: InspType; title: string; subject: string; wo?: string;
    horizon: "overdue" | "today" | "week";
    due: DueTone; dueLabel: string;
    /** The sampling ANSWER, precomputed — inspector never sees the tables. */
    plan?: string;
    severity?: { label: "Tightened" | "Reduced"; why: string };
    neededBy?: string;
    blocked?: string; // reason chip — row sinks but stays counted
    resume?: string;  // partially-captured plan → land exactly where they left off
};

const ROWS: InspRow[] = [
    { id: "i1", type: "receiving", title: "Nozzle blanks · Lot ACM-2241", subject: "Acme Machining", horizon: "overdue", due: "red", dueLabel: "due yesterday", plan: "n=32 · Ac 0", severity: { label: "Tightened", why: "Tightened since Jun 12 (2 rejected lots from Acme). 3 more accepted lots returns to Normal." }, neededBy: "needed by WO-2024-0042 — starts Thu" },
    { id: "i2", type: "in-process", title: "Nozzle Inspection · 6 pcs", subject: "Common Rail Injector", wo: "WO-2024-0042-A", horizon: "overdue", due: "red", dueLabel: "due 9:00", plan: "100% · 4 chars", resume: "7 of 13 samples · char 4/9" },
    { id: "i3", type: "receiving", title: "O-ring kits · Lot PSL-118", subject: "PrecisionSeal", horizon: "today", due: "orange", dueLabel: "due 14:00", plan: "n=5 · Ac 0", severity: { label: "Reduced", why: "Reduced since May 30 (10 straight accepted lots). One reject returns to Normal." } },
    { id: "i4", type: "final", title: "Final inspection · 4 pcs", subject: "Common Rail Injector", wo: "WO-2024-0039", horizon: "today", due: "orange", dueLabel: "due today", plan: "100% · 11 chars" },
    { id: "i5", type: "receiving", title: "Spring stock · Lot HWS-77", subject: "Hartford Wire", horizon: "today", due: "green", dueLabel: "due tomorrow", plan: "n=13 · Ac 1", blocked: "awaiting CoC from supplier" },
    { id: "i6", type: "in-process", title: "Seat grind check · 12 pcs", subject: "Injector Body", wo: "WO-2024-0048", horizon: "week", due: "green", dueLabel: "due Fri", plan: "n=8 · Ac 0", blocked: "bore gauge out for calibration" },
    { id: "i7", type: "final", title: "Final inspection · 8 pcs", subject: "Common Rail Injector", wo: "WO-2024-0051", horizon: "week", due: "gray", dueLabel: "no date", plan: "100% · 11 chars" },
];

// The queue-jumper: a first piece is waiting and a machine sits idle behind it.
const FPI_CALL = { step: "Final Test", wo: "WO-2024-0042-A", machine: "Test Bench 2", operator: "Mike", waiting: "4m 32s" };

// uniPoint To-Do semantics: assigned-to-me rows, deep-linking, re-assignable.
const MY_ACTIONS = [
    { id: "a1", kind: "Approve", title: "Quarantine disposition · INJ-0042-011", due: "red" as DueTone, dueLabel: "overdue 2d" },
    { id: "a2", kind: "CAPA task", title: "Verify fix effectiveness · CAPA-2026-08", due: "orange" as DueTone, dueLabel: "due Thu" },
    { id: "a3", kind: "Review", title: "Doc rev C · Final Test Work Instruction", due: "green" as DueTone, dueLabel: "due next week" },
];

// Veeva "Available Tasks": group-eligible, unclaimed — Accept moves it to mine.
const CLAIMABLE = [
    { id: "c1", title: "NCR disposition · WO-2024-0033 seat leak", note: "eligible: QA group · unclaimed 3h" },
];

const GAUGE_NAG = { count: 2, detail: "Bore gauge #12 (due Fri) · Micrometer M-04 (due Mon)" };

const DUE_DOT: Record<DueTone, string> = {
    red: "bg-red-500", orange: "bg-orange-400", green: "bg-emerald-500", gray: "bg-muted-foreground/40",
};

const TYPE_META: Record<InspType, { label: string; icon: React.ComponentType<{ className?: string }> }> = {
    receiving: { label: "Receiving", icon: PackageSearch },
    "in-process": { label: "In-process", icon: Ruler },
    final: { label: "Final", icon: ClipboardCheck },
    fpi: { label: "First piece", icon: FlaskConical },
};

const HORIZON_LABEL = { overdue: "Overdue", today: "Today", week: "This week" } as const;

const say = (msg: string) => toast.info(msg, { description: "Prototype — no real action taken." });

export function QaHomePrototype() {
    const [typeFilter, setTypeFilter] = useState<InspType | "all">("all");
    const [claimable, setClaimable] = useState(CLAIMABLE);

    const visible = ROWS.filter((r) => typeFilter === "all" || r.type === typeFilter);
    const counts = (t: InspType) => ROWS.filter((r) => r.type === t).length;
    const overdueCount = ROWS.filter((r) => r.horizon === "overdue").length;
    // Oldest-age per chip is what reveals rot that counts alone hide.
    const horizons = (["overdue", "today", "week"] as const).filter((h) => visible.some((r) => r.horizon === h));

    return (
        <div className="mx-auto max-w-4xl space-y-3 p-4">
            {/* Header — identity + the global quick-create (Qualio: exactly two verbs). */}
            <div className="flex items-center gap-3">
                <h1 className="min-w-0 flex-1 truncate text-2xl font-semibold tracking-tight">Good morning, Dana</h1>
                <Button variant="outline" className="h-11" onClick={() => say("Would open: Log a nonconformance (pre-filled, two fields)")}>
                    <PenLine className="mr-2 h-4 w-4" /> Log NC
                </Button>
                <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
                    <Clock className="h-4 w-4" /> Clocked in 06:52
                </span>
            </div>

            {/* FIRST-PIECE queue-jumper — andon semantics, not a worklist row. A
                machine and an operator are idle behind this; the timer is the point. */}
            <div className="flex items-center gap-3 rounded-xl border-2 border-red-300 bg-red-50 p-3 dark:border-red-900 dark:bg-red-950">
                <Siren className="h-8 w-8 shrink-0 text-red-600" />
                <div className="min-w-0 flex-1">
                    <div className="font-semibold">First piece waiting — {FPI_CALL.step}</div>
                    <div className="truncate text-sm text-muted-foreground">
                        <span className="font-mono">{FPI_CALL.wo}</span> · {FPI_CALL.machine} · sent by {FPI_CALL.operator}
                    </div>
                </div>
                <div className="shrink-0 text-right">
                    <div className="font-mono text-lg font-semibold text-red-600">{FPI_CALL.waiting}</div>
                    <div className="text-xs text-muted-foreground">machine waiting</div>
                </div>
                <Button size="lg" className="h-14 shrink-0" onClick={() => say("Would open the first-piece check (operator sees 'in progress' instantly)")}>
                    Start check
                </Button>
            </div>

            {/* THE INBOX — one flat list, filter-stat chips on top (Qualio), oldest-age
                micro-text under each chip (MachineTracking), horizons inside. */}
            <div className="rounded-xl border bg-card p-4">
                <div className="flex flex-wrap items-center gap-2">
                    <Inbox className="h-4 w-4 text-muted-foreground" />
                    <button
                        onClick={() => setTypeFilter("all")}
                        className={`rounded-full border px-3 py-1 text-sm transition-colors ${typeFilter === "all" ? "border-primary bg-primary/10 font-medium" : "hover:bg-accent"}`}
                    >
                        All {ROWS.length}
                    </button>
                    {/* Zero-count chips hide — an empty category is noise, not scope. */}
                    {(Object.keys(TYPE_META) as InspType[]).filter((t) => counts(t) > 0).map((t) => (
                        <button
                            key={t}
                            onClick={() => setTypeFilter(typeFilter === t ? "all" : t)}
                            className={`rounded-full border px-3 py-1 text-sm transition-colors ${typeFilter === t ? "border-primary bg-primary/10 font-medium" : "hover:bg-accent"}`}
                        >
                            {TYPE_META[t].label} {counts(t)}
                        </button>
                    ))}
                    {overdueCount > 0 && (
                        <span className="ml-auto rounded-full bg-red-100 px-3 py-1 text-sm font-medium text-red-700 dark:bg-red-900 dark:text-red-300">
                            Overdue {overdueCount}
                        </span>
                    )}
                </div>

                <div className="mt-3 space-y-3">
                    {horizons.map((h) => (
                        <div key={h}>
                            <div className={`text-xs font-medium uppercase tracking-wide ${h === "overdue" ? "text-red-600" : "text-muted-foreground"}`}>
                                {HORIZON_LABEL[h]}
                            </div>
                            <div className="mt-1 space-y-1">
                                {visible.filter((r) => r.horizon === h).map((r) => {
                                    const T = TYPE_META[r.type];
                                    return (
                                        <button
                                            key={r.id}
                                            onClick={() =>
                                                r.blocked
                                                    ? say(`Blocked: ${r.blocked} — would nudge the owner`)
                                                    : say(r.resume ? `Would resume capture at ${r.resume}` : `Would open the capture screen for ${r.title}`)
                                            }
                                            className={`flex w-full items-center gap-3 rounded-lg border p-2.5 text-left transition-colors hover:bg-accent ${r.blocked ? "opacity-55" : ""}`}
                                        >
                                            <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${DUE_DOT[r.due]}`} />
                                            <T.icon className="h-4 w-4 shrink-0 text-muted-foreground" />
                                            <span className="min-w-0 flex-1">
                                                <span className="flex items-center gap-2">
                                                    <span className="min-w-0 truncate text-sm font-medium">{r.title}</span>
                                                    {r.severity && (
                                                        <Badge
                                                            className={r.severity.label === "Tightened"
                                                                ? "bg-amber-100 text-amber-700 hover:bg-amber-100 dark:bg-amber-900 dark:text-amber-300"
                                                                : "bg-emerald-100 text-emerald-700 hover:bg-emerald-100 dark:bg-emerald-900 dark:text-emerald-300"}
                                                            onClick={(e) => { e.stopPropagation(); say(r.severity!.why); }}
                                                        >
                                                            {r.severity.label}
                                                        </Badge>
                                                    )}
                                                    {r.resume && (
                                                        <span className="flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400">
                                                            <PauseCircle className="h-3 w-3" /> {r.resume}
                                                        </span>
                                                    )}
                                                </span>
                                                <span className="block truncate text-xs text-muted-foreground">
                                                    {r.subject}{r.wo ? <> · <span className="font-mono">{r.wo}</span></> : null}
                                                    {r.neededBy ? <> · <b className="text-foreground/70">{r.neededBy}</b></> : null}
                                                    {r.blocked ? <> · <span className="text-amber-700 dark:text-amber-400">⏸ {r.blocked}</span></> : null}
                                                </span>
                                            </span>
                                            {r.plan && (
                                                <span className="shrink-0 rounded border px-1.5 py-0.5 font-mono text-xs text-muted-foreground">{r.plan}</span>
                                            )}
                                            <span className="w-24 shrink-0 text-right text-xs text-muted-foreground">{r.dueLabel}</span>
                                        </button>
                                    );
                                })}
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* MY QUALITY ACTIONS — uniPoint To-Do: deep links, re-assignable, due
                dots; plus the Veeva "available to claim" group so group-routed
                approvals never rot because everyone assumed someone else had it. */}
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                <div className="rounded-xl border bg-card p-4 md:col-span-2">
                    <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">My quality actions</div>
                    <div className="mt-2 space-y-1">
                        {MY_ACTIONS.map((a) => (
                            <div key={a.id} className="flex items-center gap-3 rounded-lg border p-2.5">
                                <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${DUE_DOT[a.due]}`} />
                                <span className="w-20 shrink-0 text-xs font-medium text-muted-foreground">{a.kind}</span>
                                <button className="min-w-0 flex-1 truncate text-left text-sm hover:underline" onClick={() => say(`Would open ${a.title}`)}>
                                    {a.title}
                                </button>
                                <span className="shrink-0 text-xs text-muted-foreground">{a.dueLabel}</span>
                                <Button size="sm" variant="ghost" className="h-7 shrink-0 px-2 text-xs" onClick={() => say("Would hand this to a colleague (re-assign from the row)")}>
                                    Reassign
                                </Button>
                            </div>
                        ))}
                        {claimable.length > 0 && (
                            <div className="pt-1">
                                <div className="text-xs text-muted-foreground">Available to claim — your group is eligible, nobody has it:</div>
                                {claimable.map((c) => (
                                    <div key={c.id} className="mt-1 flex items-center gap-3 rounded-lg border border-dashed p-2.5">
                                        <ArrowRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                                        <span className="min-w-0 flex-1">
                                            <span className="block truncate text-sm">{c.title}</span>
                                            <span className="block text-xs text-muted-foreground">{c.note}</span>
                                        </span>
                                        <Button size="sm" variant="outline" className="h-8 shrink-0" onClick={() => {
                                            setClaimable((cs) => cs.filter((x) => x.id !== c.id));
                                            toast.success("Claimed — moved to your actions.", { description: "Prototype — no real action taken." });
                                        }}>
                                            Accept
                                        </Button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                {/* Personal calibration nag — pre-empts the point-of-use blocking gate. */}
                <div className="flex flex-col justify-between rounded-xl border bg-card p-4">
                    <div>
                        <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                            <Gauge className="h-3.5 w-3.5" /> Your gauges
                        </div>
                        <div className="mt-2 text-sm">
                            <b>{GAUGE_NAG.count} gauges you used this week</b> are due for calibration within 7 days.
                        </div>
                        <div className="mt-1 text-xs text-muted-foreground">{GAUGE_NAG.detail}</div>
                    </div>
                    <Button variant="outline" className="mt-3 h-10 w-full" onClick={() => say("Would open the calibration queue filtered to these gauges")}>
                        Review
                    </Button>
                </div>
            </div>

            {/* Quiet state design: when everything above is empty, the page shows a
                green "audit-ready" confirmation — nobody in the market designs this. */}
            {ROWS.length === 0 && (
                <div className="flex items-center justify-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-6 text-emerald-700">
                    <CheckCircle2 className="h-5 w-5" /> All caught up — nothing due, nothing waiting. Audit-ready.
                </div>
            )}

            {/* Footer — passive self-confirmation, never throughput-vs-goal.
                Blocked-time attribution exonerates; pace pressure causes escapes. */}
            <div className="flex items-center justify-center gap-2 text-center text-sm text-muted-foreground">
                <span>Today: <b>6</b> inspections · <b>1</b> NC raised</span>
                <span>·</span>
                <button className="underline-offset-4 hover:underline" onClick={() => say("Would show blocked-time detail — 40m waiting on gauges/paperwork today")}>
                    <AlertTriangle className="mr-1 inline h-3.5 w-3.5 text-amber-600" />40m blocked
                </button>
            </div>
        </div>
    );
}

export default QaHomePrototype;
