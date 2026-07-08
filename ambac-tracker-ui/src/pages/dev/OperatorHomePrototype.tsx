/**
 * EXPERIMENT (mock data, /dev/operator-home): the "perfect" operator home.
 * Kiosk-tile layout (Plex/shop-terminal style); grounded in the 2026-07
 * three-round competitor survey. See /dev/work-queue for the list tier.
 *
 * v3 adds the DEVIATION/BLOCKER flow, per the design decisions:
 *  - UP NEXT carries a quiet "Can't run this?" escape → two-tap reason picker →
 *    the hero IMMEDIATELY swaps to the next ready item (redirect IS the capture;
 *    the blocker is born owned — the reason routes it to materials/lead/QA).
 *  - Blocked work is EXCLUDED from UP NEXT/THEN (global state), unlike the cert
 *    lock (personal state, shown dimmed) — with a trust caption so the queue
 *    never feels mysteriously thin.
 *  - Report-a-problem is a two-branch picker: machine problem (downtime event)
 *    vs can't-run-a-job (operation blocker). One tile, taxonomy hidden.
 *  - Resolutions arrive via shift notes; the job just reappears on priority.
 *  - All the aging/escalation/short-close machinery lives on LEAD surfaces,
 *    deliberately absent here.
 *
 * v4 folds in the round-4 competitor research (5 digests, 2026-07):
 *  - Aging tint by time-in-ready-state (Toast/Square KDS) — urgency without a
 *    scheduler; the clock starts when the job became ready.
 *  - Flag lifecycle (L2L Dispatch): flags I raised show routed→seen + elapsed,
 *    killing the "did anyone see this?" walk.
 *  - First-piece loop (ShopPulse FAI): sent-for-check is a visible state with
 *    QA acknowledgment, not dead air.
 *  - Shift notes carry per-note read-acknowledgment (Poka/Epic Brain).
 *  - Consequence preview on "Can't run this?" (DoorDash — lift the preview,
 *    never the acceptance-rate punishment).
 *  - Undo window after completion (Toast recall) — fearless big-button taps.
 *  - "+N with this setup" batching hint (Square all-day analog): a legitimate,
 *    visible reason to deviate from queue order.
 *  - Start forks setup→run (Epicor/ShopPulse); THEN-start is a quiet soft-skip.
 *  - Evidence-bearing empty state (readiness data > gig-app hotspots).
 *  - Cert locks show the path: needed cert + request sign-off (Augmentir/Plex).
 *  - "See everything ready" trust link (Fulcrum self-serve queue) + Break button.
 */
import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import {
    Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList,
} from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
    AlertTriangle, BookOpen, Check, ChevronsUpDown, Clock, Hand, Lock, Megaphone, PlayCircle, ScanLine, Timer, Wrench, XCircle,
} from "lucide-react";

// ---------------------------------------------------------------------------
// MOCK — shapes are the wishlist for the real backing.
// ---------------------------------------------------------------------------

type QueueOp = {
    id: string; area: string; wo: string; step: string; partType: string;
    qty: number; due: string; priority: "high" | "normal";
    estMinutes: number; done: number; of: number;
    certified: boolean; cert?: string;
    /** Time since this op became ready — the KDS aging clock (no scheduler needed). */
    readyFor: string; aging?: "amber" | "red";
    /** Other ready ops sharing this setup/fixture — the batching hint. */
    sameSetup?: number;
};

type MyFlag = {
    id: string; label: string; wo: string; owner: string;
    elapsed: string; seenBy: string | null;
};

// Work-center scopes with live ready-counts — at 100+ WOs this is what keeps
// UP NEXT drawn from YOUR pool. Persisted per user in the real version.
const AREAS = [
    { id: "all", label: "All work centers", count: 61 },
    { id: "inspect", label: "Inspection Bench", count: 12 },
    { id: "asm", label: "Assembly Line", count: 19 },
    { id: "flow", label: "Flow Test Bench", count: 7 },
    { id: "clean", label: "Cleaning Bay", count: 34 },
    { id: "recv", label: "Core Receiving", count: 15 },
] as const;

const INITIAL_QUEUE: QueueOp[] = [
    { id: "op1", area: "inspect", wo: "WO-2024-0042-A", step: "Nozzle Inspection", partType: "Common Rail Injector", qty: 6, due: "Jul 11", priority: "high", estMinutes: 12, done: 2, of: 8, certified: true, readyFor: "3h", sameSetup: 2 },
    { id: "op2", area: "asm", wo: "WO-2024-0042-A", step: "Assembly", partType: "Common Rail Injector", qty: 4, due: "Jul 11", priority: "high", estMinutes: 9, done: 0, of: 8, certified: true, readyFor: "6h", aging: "amber" },
    { id: "op3", area: "flow", wo: "WO-SHOWCASE-01", step: "Flow Testing", partType: "Common Rail Injector", qty: 1, due: "Jul 12", priority: "high", estMinutes: 20, done: 0, of: 1, certified: false, cert: "Flow Test Level 2", readyFor: "30m" },
    { id: "op4", area: "clean", wo: "WO-2024-0048", step: "Cleaning", partType: "Injector Body", qty: 12, due: "Jul 18", priority: "normal", estMinutes: 6, done: 4, of: 16, certified: true, readyFor: "2d", aging: "red" },
    { id: "op5", area: "recv", wo: "WO-2024-0051", step: "Core Receiving", partType: "Common Rail Injector", qty: 8, due: "Jul 21", priority: "normal", estMinutes: 5, done: 0, of: 8, certified: true, readyFor: "1h" },
];

const MOCK = {
    operator: { name: "Mike", clockedInAt: "06:58", elapsed: "2h 14m" },
    inProgress: {
        part: "INJ-0042-018", step: "Final Test", wo: "WO-2024-0042-A", startedAgo: "25m",
        estTotal: "~45m est", done: 3, of: 6,
    },
    // The visible first-piece loop: sent → seen → (approve/reject arrives as a state change).
    firstPiece: { step: "Final Test", part: "INJ-0042-018", sentAgo: "4m", ackBy: "Dana (QA)" },
    // Flags I raised — lifecycle visible so nobody walks the floor to ask "did anyone see this?"
    myFlags: [
        { id: "f0", label: "Tooling / fixture unavailable", wo: "WO-2024-0047", owner: "your lead", elapsed: "38m", seenBy: "Luis" },
    ] as MyFlag[],
    // Undo window after Complete (Toast recall) — fearless big-button taps.
    lastFinished: { step: "Final Test", part: "INJ-0042-017", ago: "8m" },
    today: { completed: 14, flagged: 1 },
    shiftNotes: [
        { id: "n1", from: "Your lead", note: "Prioritize WO-2024-0042 before lunch — customer pickup at 2pm." },
        { id: "n2", from: "Materials", note: "WO-2024-0051 kitted — Core Receiving is back in your queue." },
    ],
};

// Blocker reasons double as the routing table (reason → owner queue).
const BLOCK_REASONS = [
    { key: "material", label: "Missing material", owner: "Materials" },
    { key: "tooling", label: "Tooling / fixture unavailable", owner: "your lead" },
    { key: "quality", label: "Quality hold", owner: "QA" },
    { key: "other", label: "Something else", owner: "your lead" },
] as const;

const MACHINE_REASONS = ["Machine down / fault", "Needs maintenance", "Setup / changeover issue", "Other"] as const;

const PRIORITY_TONE: Record<string, string> = {
    high: "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300",
};

// KDS-style aging edge: urgency lives on the artifact, read by peripheral vision.
const AGING_EDGE: Record<string, string> = {
    amber: "border-l-4 border-l-amber-400",
    red: "border-l-4 border-l-red-500",
};

const say = (msg: string) => toast.info(msg, { description: "Prototype — no real action taken." });

/** A kiosk tile: bordered, filled, generous padding, whole-tile affordance. */
function Tile({ className = "", children }: { className?: string; children: React.ReactNode }) {
    return <div className={`rounded-xl border bg-card p-4 ${className}`}>{children}</div>;
}

export function OperatorHomePrototype() {
    const [code, setCode] = useState("");
    // The ready queue is stateful so "Can't run this?" visibly swaps the hero.
    const [queue, setQueue] = useState<QueueOp[]>(INITIAL_QUEUE);
    const [blockedCount, setBlockedCount] = useState(2); // pre-existing blocked jobs (global)
    const [notes, setNotes] = useState(MOCK.shiftNotes);
    const [flags, setFlags] = useState<MyFlag[]>(MOCK.myFlags);
    const [blockOpen, setBlockOpen] = useState(false);
    const [problemOpen, setProblemOpen] = useState(false);
    const [problemBranch, setProblemBranch] = useState<"machine" | "job" | null>(null);
    const [area, setArea] = useState<string>("all");
    const [areaOpen, setAreaOpen] = useState(false);

    const scoped = area === "all" ? queue : queue.filter((o) => o.area === area);
    const upNext = scoped[0];
    const rest = scoped.slice(1);
    const areaLabel = AREAS.find((a) => a.id === area);

    const scan = () => {
        if (!code.trim()) return;
        say(`Would open the operator work surface for "${code.trim()}"`);
        setCode("");
    };

    /** The deviation flow: two taps → blocker born owned → hero swaps to next.
     *  The flag lands in "your flags" with a visible routed→seen lifecycle. */
    const blockUpNext = (reason: (typeof BLOCK_REASONS)[number]) => {
        if (!upNext) return;
        setBlockOpen(false);
        setQueue((q) => q.filter((o) => o.id !== upNext.id));
        setBlockedCount((n) => n + 1);
        setFlags((f) => [
            ...f,
            { id: upNext.id, label: reason.label, wo: upNext.wo, owner: reason.owner, elapsed: "just now", seenBy: null },
        ]);
        const next = scoped[1];
        toast.success(`${upNext.step} flagged — ${reason.owner} notified.`, {
            description: next ? `Up next: ${next.step} (${next.wo}).` : "Queue is clear.",
        });
    };

    return (
        <div className="mx-auto max-w-5xl space-y-3 p-4">
            {/* Header — identity + clock state. */}
            <div className="flex items-center gap-3">
                <h1 className="min-w-0 flex-1 truncate text-2xl font-semibold tracking-tight">
                    Good morning, {MOCK.operator.name}
                </h1>
                {/* Station scope — the relevance filter, explicit. At 100+ WOs this
                    keeps UP NEXT drawn from YOUR pool; persisted per user for real. */}
                <Popover open={areaOpen} onOpenChange={setAreaOpen}>
                    <PopoverTrigger asChild>
                        <Button variant="outline" role="combobox" aria-expanded={areaOpen} className="h-12 w-56 justify-between">
                            <span className="truncate">
                                {areaLabel?.label ?? "All work centers"}
                                <span className="ml-1.5 text-muted-foreground">({areaLabel?.count ?? 0})</span>
                            </span>
                            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                        </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-64 p-0" align="end">
                        <Command>
                            <CommandInput placeholder="Work center…" />
                            <CommandList>
                                <CommandEmpty>Nothing matches.</CommandEmpty>
                                <CommandGroup>
                                    {AREAS.map((a) => (
                                        <CommandItem key={a.id} value={a.label} onSelect={() => { setArea(a.id); setAreaOpen(false); }}>
                                            <Check className={`mr-2 h-4 w-4 ${a.id === area ? "opacity-100" : "opacity-0"}`} />
                                            <span className="min-w-0 flex-1 truncate">{a.label}</span>
                                            <span className="ml-2 text-xs text-muted-foreground">{a.count}</span>
                                        </CommandItem>
                                    ))}
                                </CommandGroup>
                            </CommandList>
                        </Command>
                    </PopoverContent>
                </Popover>
                <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
                    <Clock className="h-4 w-4" /> Clocked in {MOCK.operator.clockedInAt} · {MOCK.operator.elapsed}
                </span>
                <Button variant="outline" size="lg" className="h-12" onClick={() => say("Would pause your active labor session (break)")}>
                    Break
                </Button>
                <Button variant="outline" size="lg" className="h-12" onClick={() => say("Would show your day recap, then clock you out")}>
                    Clock out
                </Button>
            </div>

            {/* FIRST-PIECE loop — the setup→run gate as a visible state (ShopPulse
                FAI pattern): sent → seen by QA → approved/rejected arrives here. */}
            <div className="flex items-center gap-2 rounded-lg border border-orange-200 bg-orange-50 px-3 py-2 text-sm dark:border-orange-900 dark:bg-orange-950">
                <Timer className="h-4 w-4 shrink-0 text-orange-600" />
                <span className="min-w-0 truncate">
                    <b>{MOCK.firstPiece.step}</b> · first piece sent for check {MOCK.firstPiece.sentAgo} ago
                </span>
                <span className="ml-auto shrink-0 text-muted-foreground">Seen by {MOCK.firstPiece.ackBy}</span>
            </div>

            {/* Tile grid — Up Next dominates (2×2); everything else is one tile. */}
            <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
                {/* UP NEXT — the hero tile. */}
                <Tile className="border-2 border-primary/40 md:col-span-2 md:row-span-2 flex flex-col">
                    {upNext ? (
                        <>
                            <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                                Up next
                                {PRIORITY_TONE[upNext.priority] && <Badge className={PRIORITY_TONE[upNext.priority]}>{upNext.priority}</Badge>}
                                <span className="ml-auto">ready {upNext.readyFor} · due {upNext.due}</span>
                            </div>
                            <div className="mt-3 flex-1">
                                <div className="text-3xl font-semibold leading-tight">{upNext.step}</div>
                                <div className="mt-1 text-sm text-muted-foreground">
                                    {upNext.partType} · <span className="font-mono">{upNext.wo}</span>
                                </div>
                                {/* Setup-batching hint — the legitimate reason to deviate from queue order. */}
                                {upNext.sameSetup && (
                                    <button
                                        className="mt-1.5 inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs text-muted-foreground transition-colors hover:bg-accent"
                                        onClick={() => say(`Would show the ${upNext.sameSetup} other ready jobs sharing this setup`)}
                                    >
                                        +{upNext.sameSetup} more with this setup
                                    </button>
                                )}
                                <div className="mt-2 text-sm text-muted-foreground">
                                    <b className="text-foreground">{upNext.qty}</b> pcs waiting · ~{upNext.estMinutes} min each
                                </div>
                                <div className="mt-3">
                                    <div className="h-2 overflow-hidden rounded-full bg-muted">
                                        <div className="h-full rounded-full bg-primary" style={{ width: (upNext.done / upNext.of) * 100 + "%" }} />
                                    </div>
                                    <div className="mt-1 text-xs text-muted-foreground">{upNext.done} of {upNext.of} done on this order</div>
                                </div>
                            </div>
                            <div className="mt-4 flex gap-2">
                                <Button size="lg" className="h-16 flex-1 text-lg" onClick={() => say(`Would start SETUP at ${upNext.step} — run begins after the first-piece check`)}>
                                    <PlayCircle className="mr-2 h-6 w-6" /> Start
                                </Button>
                                <Button size="lg" variant="outline" className="h-16" onClick={() => say("Would open the work instructions for this step")}>
                                    <BookOpen className="mr-2 h-5 w-5" /> Instructions
                                </Button>
                            </div>
                            {/* The deviation escape — quiet, but one tap away. */}
                            <button
                                className="mt-2 self-start text-sm text-muted-foreground underline-offset-4 hover:underline"
                                onClick={() => setBlockOpen(true)}
                            >
                                Can't run this?
                            </button>
                        </>
                    ) : (
                        <div className="flex flex-1 flex-col items-center justify-center gap-2 text-center text-muted-foreground">
                            <Wrench className="h-8 w-8" />
                            {/* Evidence-bearing empty state: cause + horizon, never a dead end.
                                Readiness derivation means we can NAME what's coming and where it is. */}
                            <p className="text-sm font-medium text-foreground">
                                Nothing ready{area !== "all" ? " at this work center" : ""}
                            </p>
                            <p className="max-w-xs text-xs">
                                2 jobs on the way: WO-2024-0042 at Nozzle Inspection (started 25m ago) · WO-2024-0048 in Cleaning
                            </p>
                            {area !== "all" && (
                                <Button variant="outline" size="sm" onClick={() => setArea("all")}>Widen scope</Button>
                            )}
                        </div>
                    )}
                </Tile>

                {/* RESUME tile. */}
                <Tile className="flex flex-col justify-between">
                    <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                        <Timer className="h-3.5 w-3.5 text-blue-600" /> In progress
                    </div>
                    <div className="my-2 min-w-0">
                        <div className="truncate font-medium">{MOCK.inProgress.step}</div>
                        <div className="truncate font-mono text-xs text-muted-foreground">{MOCK.inProgress.part}</div>
                        <div className="text-xs text-muted-foreground">
                            {/* Actual-vs-estimate is the one pace signal derivable without
                                machine data: labor clock vs routing estimate. */}
                            {MOCK.inProgress.startedAgo} of {MOCK.inProgress.estTotal} · {MOCK.inProgress.done} of {MOCK.inProgress.of} done
                        </div>
                    </div>
                    <Button className="h-12 w-full" onClick={() => say("Would resume the open run in the operator runtime")}>
                        Resume
                    </Button>
                </Tile>

                {/* SCAN tile. */}
                <Tile className="flex flex-col justify-between">
                    <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                        <ScanLine className="h-3.5 w-3.5" /> Scan
                    </div>
                    <Input
                        value={code}
                        onChange={(e) => setCode(e.target.value)}
                        onKeyDown={(e) => { if (e.key === "Enter") scan(); }}
                        placeholder="Traveler / part…"
                        className="my-2 h-12 text-base"
                        autoFocus
                    />
                    <Button variant="outline" className="h-12 w-full" disabled={!code.trim()} onClick={scan}>
                        Go
                    </Button>
                </Tile>

                {/* SHIFT NOTES tile — inbound handoff; blocker RESOLUTIONS arrive here
                    too. Per-note "Got it" (Poka/Epic ack): the acknowledgment is logged,
                    so "the system told a human" is a recorded event, not a pixel. */}
                <Tile className="md:col-span-2 border-blue-200 bg-blue-50 dark:border-blue-900 dark:bg-blue-950">
                    <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-blue-700 dark:text-blue-300">
                        <Megaphone className="h-3.5 w-3.5" /> Shift notes
                        {notes.length > 0 && (
                            <Badge className="bg-blue-600 text-white hover:bg-blue-600">{notes.length} new</Badge>
                        )}
                    </div>
                    <div className="mt-2 space-y-1.5 text-sm">
                        {notes.length === 0 && (
                            <p className="text-muted-foreground">All caught up — every note acknowledged.</p>
                        )}
                        {notes.map((n) => (
                            <div key={n.id} className="flex items-start gap-2">
                                <div className="min-w-0 flex-1"><b>{n.from}:</b> {n.note}</div>
                                <Button
                                    size="sm" variant="ghost" className="h-7 shrink-0 px-2 text-xs"
                                    onClick={() => setNotes((ns) => ns.filter((x) => x.id !== n.id))}
                                >
                                    Got it
                                </Button>
                            </div>
                        ))}
                    </div>
                </Tile>

                {/* THEN — the rest of the queue. Blocked work is EXCLUDED (global);
                    cert-locked is shown dimmed (personal). */}
                <Tile className="md:col-span-2">
                    <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Then</div>
                    <div className="mt-2 grid grid-cols-2 gap-2">
                        {rest.map((q, i) => (
                            <button
                                key={q.id}
                                onClick={() =>
                                    q.certified
                                        // Starting a THEN tile instead of UP NEXT is a soft skip —
                                        // logged quietly for coaching, never blocked or scored.
                                        ? say(`Would start ${q.step} on ${q.wo} (top pick passed — noted quietly)`)
                                        : say(`Needs ${q.cert} — would send a sign-off request to your lead`)
                                }
                                className={`rounded-lg border p-3 text-left transition-colors hover:bg-accent ${q.certified ? "" : "opacity-60"} ${q.aging ? AGING_EDGE[q.aging] : ""}`}
                            >
                                <div className="flex items-center gap-2">
                                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-muted text-xs font-semibold">{i + 2}</span>
                                    <span className="min-w-0 flex-1 truncate text-sm font-medium">{q.step}</span>
                                    {!q.certified && <Lock className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />}
                                    {PRIORITY_TONE[q.priority] && (
                                        <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${PRIORITY_TONE[q.priority]}`}>{q.priority}</span>
                                    )}
                                </div>
                                <div className="mt-1 truncate font-mono text-xs text-muted-foreground">
                                    {q.wo} · {q.qty} pcs · waiting {q.readyFor}{q.certified ? "" : ` · needs ${q.cert}`}
                                </div>
                            </button>
                        ))}
                    </div>
                    {/* Trust captions: the queue is never mysteriously thin, and the
                        full self-serve list (Fulcrum pattern) is one tap away — the
                        browsable queue is what makes a system-picked hero acceptable. */}
                    <div className="mt-2 flex items-center gap-4">
                        {blockedCount > 0 && (
                            <button
                                className="text-xs text-muted-foreground underline-offset-4 hover:underline"
                                onClick={() => say("Would open the queue's Blocked bucket")}
                            >
                                {blockedCount} job{blockedCount === 1 ? "" : "s"} blocked — owners notified
                            </button>
                        )}
                        <button
                            className="ml-auto text-xs text-muted-foreground underline-offset-4 hover:underline"
                            onClick={() => say("Would open the full ready queue (the /dev/work-queue list)")}
                        >
                            See everything ready (23)
                        </button>
                    </div>
                </Tile>

                {/* PROBLEM + LEAD tiles. */}
                <Tile className="flex items-stretch p-0">
                    <button
                        onClick={() => { setProblemBranch(null); setProblemOpen(true); }}
                        className="flex w-full flex-col items-center justify-center gap-2 rounded-xl p-4 transition-colors hover:bg-accent"
                    >
                        <AlertTriangle className="h-8 w-8 text-amber-600" />
                        <span className="text-sm font-medium">Report a problem</span>
                    </button>
                </Tile>
                <Tile className="flex items-stretch p-0">
                    <button
                        onClick={() => say("Would ping your shift lead")}
                        className="flex w-full flex-col items-center justify-center gap-2 rounded-xl p-4 transition-colors hover:bg-accent"
                    >
                        <Hand className="h-8 w-8" />
                        <span className="text-sm font-medium">Call my lead</span>
                    </button>
                </Tile>
            </div>

            {/* YOUR FLAGS — the L2L-dispatch lifecycle: routed → seen → resolved.
                Answers "did anyone see this?" without walking the floor. */}
            {flags.length > 0 && (
                <div className="space-y-1 rounded-lg border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
                    {flags.map((f) => (
                        <div key={f.id} className="flex items-center gap-2">
                            <AlertTriangle className="h-3 w-3 shrink-0 text-amber-600" />
                            <span className="min-w-0 flex-1 truncate">
                                <b className="text-foreground">{f.label}</b> · {f.wo} → {f.owner}
                            </span>
                            <span className="shrink-0">
                                {f.seenBy ? `Seen by ${f.seenBy}` : "Routed — not seen yet"} · {f.elapsed}
                            </span>
                        </div>
                    ))}
                </div>
            )}

            {/* Undo window (Toast recall): mistakes stay cheap, so the big
                buttons get pressed without hesitation. */}
            <p className="text-center text-xs text-muted-foreground">
                Finished {MOCK.lastFinished.ago} ago: {MOCK.lastFinished.step} · <span className="font-mono">{MOCK.lastFinished.part}</span>
                <button className="ml-2 underline-offset-4 hover:underline" onClick={() => say("Would reopen that run (undo window)")}>Undo</button>
                <span className="mx-1">·</span>
                <button className="underline-offset-4 hover:underline" onClick={() => say("Would flag that part for QA")}>Flag</button>
            </p>

            {/* Footer — the only "metric": your own day. Tappable → per-job recap
                (self-audit mirror, not a leaderboard). */}
            <button
                className="mx-auto block text-center text-sm text-muted-foreground underline-offset-4 hover:underline"
                onClick={() => say("Would open your day recap — per-job list with times and flags")}
            >
                Today: <b>{MOCK.today.completed}</b> parts completed · <b>{MOCK.today.flagged}</b> flagged for QA
            </button>

            {/* "Can't run this?" — two taps: reason → hero swaps. The blocker is
                born owned (reason routes it) and lands in the queue's Blocked bucket. */}
            <Dialog open={blockOpen} onOpenChange={setBlockOpen}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle>Can't run {upNext?.step}?</DialogTitle>
                        <DialogDescription>
                            {/* Consequence preview (DoorDash lesson): show what happens
                                BEFORE the tap — transparency, never score threats. */}
                            Pick why. It routes straight to the owner, leaves your queue, and your next job appears immediately.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="grid grid-cols-1 gap-2">
                        {BLOCK_REASONS.map((r) => (
                            <Button key={r.key} size="lg" variant="outline" className="h-14 text-base"
                                onClick={() => blockUpNext(r)}>
                                <XCircle className="mr-3 h-5 w-5 shrink-0 text-muted-foreground" />
                                <span className="flex-1 text-left">{r.label}</span>
                                <span className="text-xs font-normal text-muted-foreground">→ {r.owner}</span>
                            </Button>
                        ))}
                    </div>
                </DialogContent>
            </Dialog>

            {/* Report a problem — two-branch picker; taxonomy stays hidden. */}
            <Dialog open={problemOpen} onOpenChange={(v) => { setProblemOpen(v); if (!v) setProblemBranch(null); }}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle>Report a problem</DialogTitle>
                        <DialogDescription>
                            {problemBranch === null ? "What kind of problem?" : problemBranch === "machine" ? "What's wrong with the machine?" : "Why can't the job run?"}
                        </DialogDescription>
                    </DialogHeader>
                    {problemBranch === null ? (
                        <div className="grid grid-cols-1 gap-2">
                            <Button size="lg" variant="outline" className="h-16 justify-start text-base" onClick={() => setProblemBranch("machine")}>
                                <Wrench className="mr-3 h-5 w-5 text-muted-foreground" /> Machine problem
                            </Button>
                            <Button size="lg" variant="outline" className="h-16 justify-start text-base" onClick={() => setProblemBranch("job")}>
                                <XCircle className="mr-3 h-5 w-5 text-muted-foreground" /> Can't run a job
                            </Button>
                        </div>
                    ) : problemBranch === "machine" ? (
                        <div className="grid grid-cols-1 gap-2">
                            {MACHINE_REASONS.map((r) => (
                                <Button key={r} size="lg" variant="outline" className="h-14 justify-start text-base"
                                    onClick={() => { setProblemOpen(false); setProblemBranch(null); say(`Would open a downtime event: "${r}" (maintenance notified)`); }}>
                                    {r}
                                </Button>
                            ))}
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 gap-2">
                            {BLOCK_REASONS.map((r) => (
                                <Button key={r.key} size="lg" variant="outline" className="h-14 justify-start text-base"
                                    onClick={() => { setProblemOpen(false); setProblemBranch(null); say(`Would open a job blocker: "${r.label}" (${r.owner} notified)`); }}>
                                    {r.label}
                                </Button>
                            ))}
                        </div>
                    )}
                </DialogContent>
            </Dialog>
        </div>
    );
}

export default OperatorHomePrototype;
