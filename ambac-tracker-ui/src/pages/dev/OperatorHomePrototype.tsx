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
    { id: "op1", area: "inspect", wo: "WO-2024-0042-A", step: "Nozzle Inspection", partType: "Common Rail Injector", qty: 6, due: "Jul 11", priority: "high", estMinutes: 12, done: 2, of: 8, certified: true },
    { id: "op2", area: "asm", wo: "WO-2024-0042-A", step: "Assembly", partType: "Common Rail Injector", qty: 4, due: "Jul 11", priority: "high", estMinutes: 9, done: 0, of: 8, certified: true },
    { id: "op3", area: "flow", wo: "WO-SHOWCASE-01", step: "Flow Testing", partType: "Common Rail Injector", qty: 1, due: "Jul 12", priority: "high", estMinutes: 20, done: 0, of: 1, certified: false, cert: "Flow Test Level 2" },
    { id: "op4", area: "clean", wo: "WO-2024-0048", step: "Cleaning", partType: "Injector Body", qty: 12, due: "Jul 18", priority: "normal", estMinutes: 6, done: 4, of: 16, certified: true },
    { id: "op5", area: "recv", wo: "WO-2024-0051", step: "Core Receiving", partType: "Common Rail Injector", qty: 8, due: "Jul 21", priority: "normal", estMinutes: 5, done: 0, of: 8, certified: true },
];

const MOCK = {
    operator: { name: "Mike", clockedInAt: "06:58", elapsed: "2h 14m" },
    inProgress: {
        part: "INJ-0042-018", step: "Final Test", wo: "WO-2024-0042-A", startedAgo: "25m",
        done: 3, of: 6,
    },
    today: { completed: 14, flagged: 1 },
    shiftNotes: [
        { from: "Your lead", note: "Prioritize WO-2024-0042 before lunch — customer pickup at 2pm." },
        { from: "Materials", note: "WO-2024-0051 kitted — Core Receiving is back in your queue." },
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

    /** The deviation flow: two taps → blocker born owned → hero swaps to next. */
    const blockUpNext = (reason: (typeof BLOCK_REASONS)[number]) => {
        if (!upNext) return;
        setBlockOpen(false);
        setQueue((q) => q.filter((o) => o.id !== upNext.id));
        setBlockedCount((n) => n + 1);
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
                <Button variant="outline" size="lg" className="h-12" onClick={() => say("Would clock you out")}>
                    Clock out
                </Button>
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
                                <span className="ml-auto">due {upNext.due}</span>
                            </div>
                            <div className="mt-3 flex-1">
                                <div className="text-3xl font-semibold leading-tight">{upNext.step}</div>
                                <div className="mt-1 text-sm text-muted-foreground">
                                    {upNext.partType} · <span className="font-mono">{upNext.wo}</span>
                                </div>
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
                                <Button size="lg" className="h-16 flex-1 text-lg" onClick={() => say(`Would start the first piece at ${upNext.step} in the runtime`)}>
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
                        <div className="flex flex-1 flex-col items-center justify-center gap-2 text-muted-foreground">
                            <Wrench className="h-8 w-8" />
                            <p className="text-sm">Queue clear{area !== "all" ? " at this work center" : ""} — see your lead or widen the scope.</p>
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
                            started {MOCK.inProgress.startedAgo} ago · {MOCK.inProgress.done} of {MOCK.inProgress.of} done
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

                {/* SHIFT NOTES tile — inbound handoff; blocker RESOLUTIONS arrive here too. */}
                <Tile className="md:col-span-2 border-blue-200 bg-blue-50 dark:border-blue-900 dark:bg-blue-950">
                    <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-blue-700 dark:text-blue-300">
                        <Megaphone className="h-3.5 w-3.5" /> Shift notes
                    </div>
                    <div className="mt-2 space-y-1.5 text-sm">
                        {MOCK.shiftNotes.map((n) => (
                            <div key={n.from}><b>{n.from}:</b> {n.note}</div>
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
                                        ? say(`Would start ${q.step} on ${q.wo}`)
                                        : say(`Not certified for this operation (needs ${q.cert}) — a lead can reassign, or open the training.`)
                                }
                                className={`rounded-lg border p-3 text-left transition-colors hover:bg-accent ${q.certified ? "" : "opacity-60"}`}
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
                                    {q.wo} · {q.qty} pcs{q.certified ? "" : ` · needs ${q.cert}`}
                                </div>
                            </button>
                        ))}
                    </div>
                    {/* Trust caption: the queue is never mysteriously thin. */}
                    {blockedCount > 0 && (
                        <button
                            className="mt-2 text-xs text-muted-foreground underline-offset-4 hover:underline"
                            onClick={() => say("Would open the queue's Blocked bucket")}
                        >
                            {blockedCount} job{blockedCount === 1 ? "" : "s"} blocked — owners notified
                        </button>
                    )}
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

            {/* Footer — the only "metric": your own day. */}
            <p className="text-center text-sm text-muted-foreground">
                Today: <b>{MOCK.today.completed}</b> parts completed · <b>{MOCK.today.flagged}</b> flagged for QA
            </p>

            {/* "Can't run this?" — two taps: reason → hero swaps. The blocker is
                born owned (reason routes it) and lands in the queue's Blocked bucket. */}
            <Dialog open={blockOpen} onOpenChange={setBlockOpen}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle>Can't run {upNext?.step}?</DialogTitle>
                        <DialogDescription>
                            Pick why — the right person gets it, and you'll get your next job immediately.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="grid grid-cols-1 gap-2">
                        {BLOCK_REASONS.map((r) => (
                            <Button key={r.key} size="lg" variant="outline" className="h-14 justify-start text-base"
                                onClick={() => blockUpNext(r)}>
                                <XCircle className="mr-3 h-5 w-5 text-muted-foreground" /> {r.label}
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
