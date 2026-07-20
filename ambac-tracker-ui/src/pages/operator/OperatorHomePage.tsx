/**
 * Operator landing (persona-gated from Home; route: /production/operator).
 *
 * Promoted verbatim from the /dev/operator-home v4 prototype — same kiosk-tile
 * layout, grounded in the 2026-07 competitor survey (OPERATOR_EXPERIENCE_
 * DESIGN.md §6). What's LIVE vs PREVIEW today:
 *
 *  LIVE:    greeting · Scan (real WO/part resolve → WO detail) · In progress
 *           (my open StepExecutions via /api/StepExecutions/my_workload/;
 *           Resume → the operator runtime for that run) · clock cluster
 *           (TimeEntry clock_in/out; Break/Lunch pause labor as BREAK/LUNCH entries) ·
 *           Notifications (the in-app feed; "Got it" = mark-read).
 *  PREVIEW: every dimmed tile — UP NEXT hero, THEN queue, station scope (need
 *           the queue aggregate endpoint, the keystone);
 *           Report a problem / Can't run this (need the blocker aggregate);
 *           clock state / Break / Clock out (TimeEntry has clock_in/out but no
 *           clean "am I clocked in" read yet). Each renders its prototype mock
 *           content behind a blur+disable via <PreviewLock>, so the planned
 *           surface is legible without pretending it's wired.
 *
 * As each backend lands (queue aggregate first), swap the matching PreviewLock
 * for real data.
 */
import { useState } from "react";
import { toast } from "sonner";
import { useNavigate } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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

import { api } from "@/lib/api/generated";
import { useAuthUser, type AuthUser } from "@/hooks/useAuthUser";
import { ScanBox } from "@/components/home/home-blocks";
import { useNotificationFeed, useMarkNotificationRead } from "@/hooks/notificationFeed";

// ---------------------------------------------------------------------------
// MOCK — drives the PREVIEW (dimmed) tiles so the planned layout is legible.
// Shapes are the wishlist for the real backing (queue aggregate, blocker model,
// shift-notes model). LIVE tiles below don't touch this.
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
    // The visible first-piece loop: sent → seen → (approve/reject arrives as a state change).
    firstPiece: { step: "Final Test", part: "INJ-0042-018", sentAgo: "4m", ackBy: "Dana (QA)" },
    // Flags I raised — lifecycle visible so nobody walks the floor to ask "did anyone see this?"
    myFlags: [
        { id: "f0", label: "Tooling / fixture unavailable", wo: "WO-2024-0047", owner: "your lead", elapsed: "38m", seenBy: "Luis" },
    ] as MyFlag[],
    // Undo window after Complete (Toast recall) — fearless big-button taps.
    lastFinished: { step: "Final Test", part: "INJ-0042-017", ago: "8m" },
    today: { completed: 14, flagged: 1 },
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

const say = (msg: string) => toast.info(msg, { description: "Preview — this tile isn't wired to live data yet." });

/** A kiosk tile: bordered, filled, generous padding, whole-tile affordance. */
function Tile({ className = "", children }: { className?: string; children: React.ReactNode }) {
    return <div className={`rounded-xl border bg-card p-4 ${className}`}>{children}</div>;
}

/** Wraps a tile whose backend isn't built yet: dims + desaturates + disables it
 *  and stamps a "Preview" chip, so the planned layout reads as intentional, not
 *  broken. Grid span goes on `className`; the child keeps its own styling. */
function PreviewLock({ className = "", children }: { className?: string; children: React.ReactNode }) {
    return (
        <div className={`relative ${className}`}>
            <div className="pointer-events-none select-none opacity-45 saturate-[.5]">
                {children}
            </div>
            <Badge
                variant="secondary"
                className="absolute right-2 top-2 gap-1 border bg-background/80 text-[10px] font-medium shadow-sm backdrop-blur-sm"
            >
                <Lock className="h-3 w-3" /> Preview
            </Badge>
        </div>
    );
}

/** Route wrapper (/production/operator) — Home renders OperatorHomePage directly
 *  for the Operator persona; the named route lets leads/admins reach it too. */
export function OperatorHomeRoute() {
    const { data: user } = useAuthUser();
    if (!user) return null;
    return <OperatorHomePage user={user} />;
}

export function OperatorHomePage({ user }: { user: AuthUser }) {
    const navigate = useNavigate();

    // LIVE — the operator's own open runs (assigned, not yet exited).
    const { data: workload } = useQuery({
        queryKey: ["step-executions", "my-workload"],
        queryFn: () => api.api_StepExecutions_my_workload_list({ queries: { limit: 5 } }),
    });
    const runs = workload?.results ?? [];
    const activeRun = runs.find((r) => r.status === "IN_PROGRESS") ?? runs[0] ?? null;

    // LIVE — clock state: my one open time entry (end_time is null).
    const queryClient = useQueryClient();
    const { data: openEntryPage } = useQuery({
        queryKey: ["time-entries", "open", user.pk],
        queryFn: () => api.api_TimeEntries_list({
            queries: { user: user.pk, end_time__isnull: true, ordering: "-start_time", limit: 1 },
        }),
    });
    const openEntry = openEntryPage?.results?.[0] ?? null;
    const onLunch = openEntry?.entry_type === "LUNCH";
    const paused = openEntry?.entry_type === "BREAK" || onLunch;
    const clockText = !openEntry
        ? "Not clocked in"
        : paused
            ? `On ${onLunch ? "lunch" : "break"} · ${formatDistanceToNow(new Date(openEntry.start_time))}`
            : `Clocked in · ${formatDistanceToNow(new Date(openEntry.start_time))}`;

    // The clock as a one-open-entry state machine (TimeEntry is the labor-costing
    // record): clock in → SHIFT; Break/Lunch close the open entry then open a
    // BREAK/LUNCH pause; End break resumes SHIFT; Clock out closes and reopens
    // nothing. Clocking onto an actual job (a PRODUCTION entry) happens in the
    // runtime when the operator Starts/Resumes work.
    const clockAction = useMutation({
        mutationFn: async (
            action:
                | { kind: "clockin" }
                | { kind: "pause"; type: "BREAK" | "LUNCH" }
                | { kind: "resume" }
                | { kind: "clockout" }
        ) => {
            if (action.kind !== "clockin" && openEntry) {
                await api.api_TimeEntries_clock_out_create({}, { params: { id: String(openEntry.id) } });
            }
            if (action.kind === "clockin" || action.kind === "resume") {
                return api.api_TimeEntries_clock_in_create({ entry_type: "SHIFT" });
            }
            if (action.kind === "pause") {
                return api.api_TimeEntries_clock_in_create({ entry_type: action.type });
            }
            return null; // clockout — nothing reopened
        },
        onSuccess: (_data, action) => {
            queryClient.invalidateQueries({ queryKey: ["time-entries", "open", user.pk] });
            if (action.kind === "clockin") toast.success("Clocked in.");
            else if (action.kind === "pause") toast.success(action.type === "LUNCH" ? "On lunch — labor paused." : "On break — labor paused.");
            else if (action.kind === "resume") toast.success("Welcome back — back on shift.");
            else toast.success("Clocked out.");
        },
        onError: () => toast.error("Couldn't update your clock — try again."),
    });

    // LIVE — inbound awareness: the in-app notification feed (unread only).
    // "Got it" marks the item read (shared cache with the header bell).
    const { data: feedItems } = useNotificationFeed({ unread: true, limit: 8 });
    const markRead = useMarkNotificationRead();
    const unread = feedItems ?? [];

    // PREVIEW state — drives the dimmed tiles so the layout is legible.
    const [queue, setQueue] = useState<QueueOp[]>(INITIAL_QUEUE);
    const [blockedCount, setBlockedCount] = useState(2); // pre-existing blocked jobs (global)
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

    const hour = new Date().getHours();
    const greeting = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";

    /** The deviation flow: two taps → blocker born owned → hero swaps to next. */
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
            {/* Header — identity is live; scope + clock are preview. */}
            <div className="flex items-center gap-3">
                <h1 className="min-w-0 flex-1 truncate text-2xl font-semibold tracking-tight">
                    {greeting}{user.first_name ? `, ${user.first_name}` : ""}
                </h1>
                {/* Station scope — still Preview (needs the queue aggregate's per-scope counts). */}
                <PreviewLock className="shrink-0">
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
                </PreviewLock>
                {/* Clock cluster — LIVE: TimeEntry clock_in/out; Break/Lunch pause labor. */}
                <div className="flex shrink-0 items-center gap-3">
                    <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
                        <Clock className="h-4 w-4" /> {clockText}
                    </span>
                    {!openEntry ? (
                        <Button size="lg" className="h-12" disabled={clockAction.isPending}
                            onClick={() => clockAction.mutate({ kind: "clockin" })}>
                            Clock in
                        </Button>
                    ) : paused ? (
                        <>
                            <Button variant="outline" size="lg" className="h-12" disabled={clockAction.isPending}
                                onClick={() => clockAction.mutate({ kind: "resume" })}>
                                End {onLunch ? "lunch" : "break"}
                            </Button>
                            <Button variant="ghost" size="lg" className="h-12" disabled={clockAction.isPending}
                                onClick={() => clockAction.mutate({ kind: "clockout" })}>
                                Clock out
                            </Button>
                        </>
                    ) : (
                        <>
                            <Button variant="outline" size="lg" className="h-12" disabled={clockAction.isPending}
                                onClick={() => clockAction.mutate({ kind: "pause", type: "BREAK" })}>
                                Break
                            </Button>
                            <Button variant="outline" size="lg" className="h-12" disabled={clockAction.isPending}
                                onClick={() => clockAction.mutate({ kind: "pause", type: "LUNCH" })}>
                                Lunch
                            </Button>
                            <Button variant="outline" size="lg" className="h-12" disabled={clockAction.isPending}
                                onClick={() => clockAction.mutate({ kind: "clockout" })}>
                                Clock out
                            </Button>
                        </>
                    )}
                </div>
            </div>

            {/* Orient the viewer: what's real vs. planned. */}
            <p className="text-xs text-muted-foreground">
                Preview build — <b className="text-foreground">Scan</b>, <b className="text-foreground">In progress</b>, <b className="text-foreground">Notifications</b>, and the <b className="text-foreground">clock</b> (in/out/break/lunch) are live.
                Dimmed tiles show the planned layout; they light up as the queue service and blocker model land.
            </p>

            {/* FIRST-PIECE loop — needs the FPI operator-side read. */}
            <PreviewLock>
                <div className="flex items-center gap-2 rounded-lg border border-orange-200 bg-orange-50 px-3 py-2 text-sm dark:border-orange-900 dark:bg-orange-950">
                    <Timer className="h-4 w-4 shrink-0 text-orange-600" />
                    <span className="min-w-0 truncate">
                        <b>{MOCK.firstPiece.step}</b> · first piece sent for check {MOCK.firstPiece.sentAgo} ago
                    </span>
                    <span className="ml-auto shrink-0 text-muted-foreground">Seen by {MOCK.firstPiece.ackBy}</span>
                </div>
            </PreviewLock>

            {/* Tile grid — Up Next dominates (2×2); everything else is one tile. */}
            <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
                {/* UP NEXT — the hero. Needs the queue aggregate endpoint (ranked
                    readiness). Preview until then. */}
                <PreviewLock className="md:col-span-2 md:row-span-2">
                    <Tile className="h-full border-2 border-primary/40 flex flex-col">
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
                </PreviewLock>

                {/* RESUME — LIVE: my open StepExecution(s). */}
                <Tile className="flex flex-col justify-between">
                    <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                        <Timer className="h-3.5 w-3.5 text-blue-600" /> In progress
                    </div>
                    {activeRun ? (
                        <>
                            <div className="my-2 min-w-0">
                                <div className="truncate font-medium">{activeRun.step_name}</div>
                                <div className="truncate font-mono text-xs text-muted-foreground">{activeRun.part_erp_id}</div>
                                <div className="text-xs text-muted-foreground">
                                    {activeRun.status === "IN_PROGRESS" ? "Running" : "Assigned"}
                                    {activeRun.entered_at ? ` · started ${formatDistanceToNow(new Date(activeRun.entered_at))} ago` : ""}
                                    {runs.length > 1 ? ` · +${runs.length - 1} more open` : ""}
                                </div>
                            </div>
                            <Button
                                className="h-12 w-full"
                                onClick={() => navigate({
                                    to: "/operator/steps/$stepId/substeps",
                                    params: { stepId: String(activeRun.step) },
                                    search: {
                                        part: String(activeRun.part),
                                        execution: String(activeRun.id),
                                        workOrder: undefined,
                                        material_lot: undefined,
                                        osp_shipment: undefined,
                                        at: undefined,
                                        unit: undefined,
                                        queue: undefined,
                                        debug: undefined,
                                    },
                                })}
                            >
                                Resume
                            </Button>
                        </>
                    ) : (
                        <>
                            <p className="my-2 text-sm text-muted-foreground">
                                No open run. Scan a traveler to pick up where you left off.
                            </p>
                            <Button className="h-12 w-full" variant="outline" disabled>Resume</Button>
                        </>
                    )}
                </Tile>

                {/* SCAN — LIVE: real WO/part resolve → WO detail. */}
                <Tile className="flex flex-col gap-2">
                    <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                        <ScanLine className="h-3.5 w-3.5" /> Scan
                    </div>
                    <ScanBox />
                </Tile>

                {/* NOTIFICATIONS — LIVE: the in-app notification feed (awareness
                    surface). "Got it" marks the item read. */}
                <Tile className="md:col-span-2 border-blue-200 bg-blue-50 dark:border-blue-900 dark:bg-blue-950">
                    <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-blue-700 dark:text-blue-300">
                        <Megaphone className="h-3.5 w-3.5" /> Notifications
                        {unread.length > 0 && (
                            <Badge className="bg-blue-600 text-white hover:bg-blue-600">{unread.length} new</Badge>
                        )}
                    </div>
                    <div className="mt-2 space-y-1.5 text-sm">
                        {unread.length === 0 && (
                            <p className="text-muted-foreground">All caught up — nothing new.</p>
                        )}
                        {unread.map((n) => (
                            <div key={n.id} className="flex items-start gap-2">
                                <div className="min-w-0 flex-1">
                                    <b>{n.rendered_subject}</b>
                                    {n.rendered_body_text ? <span className="text-muted-foreground"> — {n.rendered_body_text}</span> : null}
                                    {n.rendered_action_url ? (
                                        <a href={n.rendered_action_url} className="ml-1 whitespace-nowrap text-blue-700 underline-offset-4 hover:underline dark:text-blue-300">Open</a>
                                    ) : null}
                                </div>
                                <Button
                                    size="sm" variant="ghost" className="h-7 shrink-0 px-2 text-xs"
                                    disabled={markRead.isPending}
                                    onClick={() => markRead.mutate(n.id)}
                                >
                                    Got it
                                </Button>
                            </div>
                        ))}
                    </div>
                </Tile>

                {/* THEN — the rest of the queue. Needs the queue aggregate. Preview. */}
                <PreviewLock className="md:col-span-2">
                    <Tile className="h-full">
                        <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Then</div>
                        <div className="mt-2 grid grid-cols-2 gap-2">
                            {rest.map((q, i) => (
                                <button
                                    key={q.id}
                                    onClick={() =>
                                        q.certified
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
                                onClick={() => say("Would open the full ready queue (the work-queue list)")}
                            >
                                See everything ready (23)
                            </button>
                        </div>
                    </Tile>
                </PreviewLock>

                {/* PROBLEM + LEAD — need the blocker aggregate + downtime dialog. Preview. */}
                <PreviewLock>
                    <Tile className="h-full flex items-stretch p-0">
                        <button
                            onClick={() => { setProblemBranch(null); setProblemOpen(true); }}
                            className="flex w-full flex-col items-center justify-center gap-2 rounded-xl p-4 transition-colors hover:bg-accent"
                        >
                            <AlertTriangle className="h-8 w-8 text-amber-600" />
                            <span className="text-sm font-medium">Report a problem</span>
                        </button>
                    </Tile>
                </PreviewLock>
                <PreviewLock>
                    <Tile className="h-full flex items-stretch p-0">
                        <button
                            onClick={() => say("Would ping your shift lead")}
                            className="flex w-full flex-col items-center justify-center gap-2 rounded-xl p-4 transition-colors hover:bg-accent"
                        >
                            <Hand className="h-8 w-8" />
                            <span className="text-sm font-medium">Call my lead</span>
                        </button>
                    </Tile>
                </PreviewLock>
            </div>

            {/* YOUR FLAGS — needs the blocker lifecycle. Preview. */}
            {flags.length > 0 && (
                <PreviewLock>
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
                </PreviewLock>
            )}

            {/* Undo window — needs completion events. Preview. */}
            <PreviewLock>
                <p className="text-center text-xs text-muted-foreground">
                    Finished {MOCK.lastFinished.ago} ago: {MOCK.lastFinished.step} · <span className="font-mono">{MOCK.lastFinished.part}</span>
                    <button className="ml-2 underline-offset-4 hover:underline" onClick={() => say("Would reopen that run (undo window)")}>Undo</button>
                    <span className="mx-1">·</span>
                    <button className="underline-offset-4 hover:underline" onClick={() => say("Would flag that part for QA")}>Flag</button>
                </p>
            </PreviewLock>

            {/* Day recap — needs the per-operator day aggregate. Preview. */}
            <PreviewLock className="mx-auto w-fit">
                <button
                    className="block text-center text-sm text-muted-foreground underline-offset-4 hover:underline"
                    onClick={() => say("Would open your day recap — per-job list with times and flags")}
                >
                    Today: <b>{MOCK.today.completed}</b> parts completed · <b>{MOCK.today.flagged}</b> flagged for QA
                </button>
            </PreviewLock>

            {/* Preview dialogs — triggers live under glass, so these never open in
                the shell; kept so the planned flow stays visible in the source. */}
            <Dialog open={blockOpen} onOpenChange={setBlockOpen}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle>Can't run {upNext?.step}?</DialogTitle>
                        <DialogDescription>
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

export default OperatorHomePage;
