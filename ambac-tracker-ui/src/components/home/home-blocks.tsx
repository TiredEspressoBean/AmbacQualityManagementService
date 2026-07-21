/**
 * Role-based home blocks — the "what needs me right now" landing surface.
 *
 * Model: a stack of SELF-GATING blocks (the sidebar pattern) ordered by the
 * user's primary tenant group. Grounded in the 2026-07 survey of comparable
 * MES/QMS landing screens (Fulcrum/Epicor/Plex/QT9/uniPoint/…) plus two hard
 * constraints: UQMES has NO scheduler/dispatch and NO reliable workstation
 * model, so nothing here may depend on either.
 *
 *  - ScanBox: travelers are the dispatch system in an unscheduled shop —
 *    scan/type a WO or part number and land on that WO's detail page, where
 *    Start Work + the Digital Traveler live (OPERATOR_EXPERIENCE_DESIGN §8:
 *    "scan and all Start buttons land here"). The /control page is the
 *    lead/manager surface and has no run action.
 *  - Work-order queue: competitors' operator queues list JOBS, not serials
 *    (Fulcrum/Epicor/Global Shop/Katana), so the row unit is the work order in
 *    priority/due order; per-part detail lives on the WO control page.
 *  - QA lands on two panes, never merged (industry pattern): the inspection
 *    queue + a personal "my quality actions" inbox. Dispositions appear there
 *    via their real, existing `assigned_to` workflow (the auto-create signal
 *    assigns a QA user) — NOT the unbuilt scheduling system.
 */
import { useMemo, useState } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api/generated";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
    AlertTriangle, ArrowRight, CalendarClock, CheckSquare, ClipboardCheck, FileCheck,
    FileText, FileWarning, Gauge, GitBranch, Inbox, Megaphone, PackageSearch, ScanLine,
    Truck, Wrench,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { AuthUser } from "@/hooks/useAuthUser";
import { AttentionList } from "@/components/analytics";
import { useMyCapaTasks } from "@/hooks/useMyCapaTasks";
import { useMyPendingApprovals } from "@/hooks/useMyPendingApprovals";
import { useIncomingInspection } from "@/hooks/useIncomingInspection";
import { useNeedsAttention } from "@/hooks/useNeedsAttention";
import { useDashboardKpis } from "@/hooks/useDashboardKpis";
import { useClaimableApprovals } from "@/hooks/useClaimableApprovals";
import { useClaimApproval } from "@/hooks/useClaimApproval";
import { useDocumentStats } from "@/hooks/useDocumentStats";
import { useTrainingMatrix } from "@/hooks/useTrainingMatrix";
import {
    useProcessChangeRequests, useProcessChangeOrders, useProcessChangeNotices,
} from "@/hooks/useProcessChangeArtifacts";
import { useOSPShipments, useReadyToShip } from "@/hooks/useOutsideProcess";
import { StartWorkDialog } from "@/components/workorder/StartWorkDialog";

/** Normalize a list endpoint's envelope (paginated `{count,results}` or a bare
 *  array) to a row count — the change-control hooks return an untyped envelope. */
function countRows(data: unknown): number {
    if (Array.isArray(data)) return data.length;
    const r = data as { count?: number; results?: unknown[] } | undefined;
    return r?.count ?? r?.results?.length ?? 0;
}

// ---------------------------------------------------------------------------
// Scan box — traveler-first entry. Accepts keyboard-wedge scanners (they type
// the code + Enter) and manual typing; resolves a WO ERP id or part ERP id and
// navigates to the work order detail page (Start Work + Digital Traveler +
// Documents live there — the operator work surface, per design doc §8).
// ---------------------------------------------------------------------------

export function ScanBox({ autoFocus = true }: { autoFocus?: boolean } = {}) {
    const navigate = useNavigate();
    const [code, setCode] = useState("");
    const [busy, setBusy] = useState(false);

    const resolve = async () => {
        const q = code.trim();
        if (!q || busy) return;
        setBusy(true);
        try {
            // Work order first (traveler headers carry the WO number), then part.
            const wos = (await api.api_WorkOrders_list({ queries: { search: q, limit: 5 } } as never)) as {
                results?: Array<{ id: string; ERP_id?: string | null }>;
            };
            const wo = (wos.results ?? []).find((w) => (w.ERP_id ?? "").toLowerCase() === q.toLowerCase())
                ?? ((wos.results?.length ?? 0) === 1 ? wos.results![0] : undefined);
            if (wo) {
                navigate({ to: "/workorder/$workOrderId", params: { workOrderId: String(wo.id) } });
                return;
            }
            const parts = (await api.api_Parts_list({ queries: { search: q, limit: 5 } } as never)) as {
                results?: Array<{ id: string; ERP_id?: string | null; work_order?: string | null }>;
            };
            const part = (parts.results ?? []).find((p) => (p.ERP_id ?? "").toLowerCase() === q.toLowerCase())
                ?? ((parts.results?.length ?? 0) === 1 ? parts.results![0] : undefined);
            if (part?.work_order) {
                navigate({ to: "/workorder/$workOrderId", params: { workOrderId: String(part.work_order) } });
                return;
            }
            toast.error(`Nothing found for "${q}"`, {
                description: "Scan or type a work order or part number (ERP id).",
            });
        } catch {
            toast.error("Lookup failed — try again.");
        } finally {
            setBusy(false);
            setCode("");
        }
    };

    return (
        <div className="flex items-center gap-2 rounded-lg border bg-card p-3">
            <ScanLine className="h-5 w-5 shrink-0 text-muted-foreground" />
            <Input
                value={code}
                onChange={(e) => setCode(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") void resolve(); }}
                placeholder="Scan or type a work order / part number…"
                className="border-0 shadow-none focus-visible:ring-0 text-base"
                autoFocus={autoFocus}
            />
            <Button onClick={() => void resolve()} disabled={busy || !code.trim()}>
                {busy ? "Looking up…" : "Go"}
            </Button>
        </div>
    );
}

// ---------------------------------------------------------------------------
// Work-order queue (operator primary). Research-backed unit: competitors'
// operator queues list JOBS (Fulcrum "every job in the shop", Epicor Work
// Queue, Global Shop dispatch list, Katana MO-priority) — not serials. With no
// work-center model, the shop-wide WO list in priority/due order IS the queue;
// per-part detail lives one click away on the WO control page.
// ---------------------------------------------------------------------------

// WorkOrderPriority is IntegerChoices: 1=Urgent, 2=High, 3=Normal, 4=Low
// (lower number = higher priority — the number IS the sort rank).
const PRIORITY_LABEL: Record<number, string> = { 1: "urgent", 2: "high", 3: "normal", 4: "low" };
const PRIORITY_TONE: Record<number, string> = {
    1: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300",
    2: "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300",
};

type QueueWo = {
    id: string;
    ERP_id?: string | null;
    priority?: number | null;
    quantity?: number | null;
    expected_completion?: string | null;
    related_order_info?: { name?: string | null } | null;
};

function WorkOrderQueue({ variant }: { variant: "operator" | "lead" }) {
    const { data: wosResp, isLoading } = useQuery({
        queryKey: ["home", "wo-queue"],
        queryFn: () =>
            api.api_WorkOrders_list({
                queries: { workorder_status: "IN_PROGRESS", limit: 50 },
            } as never) as Promise<{ results?: QueueWo[] }>,
        staleTime: 15_000,
    });

    const wos = useMemo(() => {
        const all = (wosResp?.results ?? []).slice();
        all.sort((a, b) => {
            const pa = a.priority ?? 3;
            const pb = b.priority ?? 3;
            if (pa !== pb) return pa - pb;
            // Then soonest due first; no due date sorts last.
            const da = a.expected_completion ?? "9999";
            const db = b.expected_completion ?? "9999";
            return da.localeCompare(db);
        });
        return all;
    }, [wosResp]);

    return (
        <Card>
            <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                    <Wrench className="h-4 w-4 text-muted-foreground" />
                    Work orders
                    <Badge variant="secondary" className="ml-1">{wos.length}</Badge>
                    {variant === "lead" && (
                        <Link to="/workorders" className="ml-auto">
                            <Button size="sm" variant="ghost">Control center <ArrowRight className="ml-1 h-4 w-4" /></Button>
                        </Link>
                    )}
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
                {isLoading ? (
                    <p className="text-sm text-muted-foreground">Loading work orders…</p>
                ) : wos.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No work orders in progress.</p>
                ) : (
                    wos.slice(0, 6).map((w) => (
                        <div key={w.id} className="flex items-center gap-3 rounded-md border p-2.5">
                            <div className="min-w-0 flex-1">
                                <div className="flex items-center gap-2">
                                    <span className="truncate font-mono text-sm font-medium">{w.ERP_id ?? w.id}</span>
                                    {w.priority != null && PRIORITY_TONE[w.priority] && (
                                        <Badge className={PRIORITY_TONE[w.priority]}>{PRIORITY_LABEL[w.priority]}</Badge>
                                    )}
                                </div>
                                <div className="truncate text-xs text-muted-foreground">
                                    {w.related_order_info?.name ?? "—"}
                                    {w.quantity != null ? ` · ${w.quantity} pcs` : ""}
                                    {w.expected_completion ? ` · due ${w.expected_completion.slice(0, 10)}` : ""}
                                </div>
                            </div>
                            {variant === "operator" ? (
                                // Straight into doing work — the control page is a
                                // lead/supervisor surface, not an operator one.
                                <StartWorkDialog workOrderId={String(w.id)} />
                            ) : (
                                <Link to="/workorder/$workOrderId/control" params={{ workOrderId: String(w.id) }}>
                                    <Button size="sm">Open</Button>
                                </Link>
                            )}
                        </div>
                    ))
                )}
                {wos.length > 6 && (
                    <p className="text-xs text-muted-foreground">
                        +{wos.length - 6} more{variant === "lead" ? " in the control center" : ""}.
                    </p>
                )}
            </CardContent>
        </Card>
    );
}

// ---------------------------------------------------------------------------
// Inspection queue (QA pane 1) — the real incoming worklist.
// ---------------------------------------------------------------------------

function InspectionQueueBlock() {
    const { data: rows = [], isLoading } = useIncomingInspection();
    // SENT = still at the vendor; everything else is actionable inbound work.
    const actionable = rows.filter((r) => r.status !== "SENT");
    const held = rows.filter((r) => r.status === "QUARANTINE").length;
    return (
        <Card>
            <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                    <PackageSearch className="h-4 w-4 text-muted-foreground" />
                    Inspection queue
                    <Badge variant="secondary" className="ml-1">{actionable.length}</Badge>
                    {held > 0 && (
                        <Badge className="bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300">
                            {held} held
                        </Badge>
                    )}
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
                {isLoading ? (
                    <p className="text-sm text-muted-foreground">Loading…</p>
                ) : actionable.length === 0 ? (
                    <p className="text-sm text-muted-foreground">Nothing awaiting inbound inspection.</p>
                ) : (
                    actionable.slice(0, 5).map((r) => (
                        <div key={`${r.source}:${r.id}`} className="flex items-center gap-3 rounded-md border p-2.5 text-sm">
                            <div className="min-w-0 flex-1">
                                <div className="truncate font-mono text-xs">{r.reference}</div>
                                <div className="truncate text-xs text-muted-foreground">
                                    {r.item}{r.supplier ? ` · ${r.supplier}` : ""}
                                </div>
                            </div>
                            <Badge variant="outline">{r.status_display}</Badge>
                        </div>
                    ))
                )}
                <Link to="/production/incoming">
                    <Button className="w-full" variant="default">
                        Start inspecting <ArrowRight className="ml-1 h-4 w-4" />
                    </Button>
                </Link>
            </CardContent>
        </Card>
    );
}

// ---------------------------------------------------------------------------
// My quality actions (QA pane 2) — merged personal inbox: approvals + CAPA
// tasks + dispositions assigned to me (a real, existing workflow field — the
// disposition auto-create signal assigns a QA user). Overdue flagged in red.
// ---------------------------------------------------------------------------

function MyQualityActionsBlock({ user }: { user: AuthUser }) {
    const { data: approvals = [] } = useMyPendingApprovals();
    const { data: tasks = [] } = useMyCapaTasks();
    const { data: dispResp } = useQuery({
        queryKey: ["home", "my-dispositions", user.pk],
        enabled: user.pk != null,
        queryFn: () =>
            api.api_QuarantineDispositions_list({
                queries: { assigned_to: user.pk, current_state: "OPEN", limit: 10 },
            } as never) as Promise<{ results?: Array<{ id: string; disposition_number: string }> }>,
        staleTime: 30_000,
    });

    const openTasks = (tasks ?? []).filter((t) => t.status !== "COMPLETED");
    const overdue = openTasks.filter((t) => t.due_date && new Date(t.due_date) < new Date()).length;
    const dispositions = dispResp?.results ?? [];
    const total = approvals.length + openTasks.length + dispositions.length;

    return (
        <Card>
            <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                    <CheckSquare className="h-4 w-4 text-muted-foreground" />
                    My quality actions
                    {total > 0 && <Badge variant="secondary" className="ml-1">{total}</Badge>}
                    {overdue > 0 && <Badge variant="destructive">{overdue} overdue</Badge>}
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
                <div className="grid grid-cols-3 gap-3 text-center">
                    <div className="rounded-md border p-2">
                        <div className="text-xl font-semibold tabular-nums">{approvals.length}</div>
                        <div className="text-xs text-muted-foreground">Approvals</div>
                    </div>
                    <div className="rounded-md border p-2">
                        <div className={`text-xl font-semibold tabular-nums ${overdue > 0 ? "text-destructive" : ""}`}>
                            {openTasks.length}
                        </div>
                        <div className="text-xs text-muted-foreground">CAPA tasks</div>
                    </div>
                    <div className="rounded-md border p-2">
                        <div className="text-xl font-semibold tabular-nums">{dispositions.length}</div>
                        <div className="text-xs text-muted-foreground">My dispositions</div>
                    </div>
                </div>
                <div className="flex gap-2">
                    <Link to="/inbox" className="flex-1">
                        <Button className="w-full" variant="outline">
                            Open inbox <ArrowRight className="ml-1 h-4 w-4" />
                        </Button>
                    </Link>
                    {dispositions.length > 0 && (
                        <Link to="/production/dispositions" className="flex-1">
                            <Button className="w-full" variant="outline">Dispositions</Button>
                        </Link>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}

// ---------------------------------------------------------------------------
// Compact stat primitives — the QUIET "reference" counterpart to an act-now
// list block. A stat is ~64px tall (vs the shared KpiCard's ~240px), lays out
// as an even-fill strip (no orphaned dead cell), reads muted at zero so real
// counts pop, and colors only a non-zero value. Reference blocks use these;
// act-now blocks (needs-attention, queues) keep full Card+list chrome — that
// contrast is what carries the act-now vs reference hierarchy.
// ---------------------------------------------------------------------------

function StatTile({
    label, value, icon: Icon, link, variant = "default",
}: {
    label: string;
    value: number | string;
    icon: LucideIcon;
    link: string;
    variant?: "default" | "warning" | "danger";
}) {
    const isZero = value === 0 || value === "0" || value === "0%";
    const valueClass = isZero
        ? "text-muted-foreground/50"
        : variant === "danger"
            ? "text-red-600 dark:text-red-400"
            : variant === "warning"
                ? "text-amber-600 dark:text-amber-400"
                : "text-foreground";
    return (
        <Link
            to={link}
            className="min-w-[130px] flex-1 rounded-lg border bg-card px-3 py-2.5 transition-colors hover:bg-accent"
        >
            <div className="flex items-center justify-between gap-2">
                <span className="truncate text-xs text-muted-foreground">{label}</span>
                <Icon className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
            </div>
            <div className={`mt-0.5 text-2xl font-semibold tabular-nums ${valueClass}`}>{value}</div>
        </Link>
    );
}

/** Even-fill row of stat tiles: flex-1 tiles stretch to fill the last row, so a
 *  count that doesn't divide the grid never leaves an orphaned empty cell. */
function StatSection({ title, children }: { title: string; children: React.ReactNode }) {
    return (
        <div>
            <div className="mb-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">{title}</div>
            <div className="flex flex-wrap gap-2">{children}</div>
        </div>
    );
}

/** Graceful all-clear state for a primary block whose data is zero — next-step
 *  scent instead of a row of dead zeros (the "dead page" first-login problem). */
function EmptyBlock({ icon: Icon, title, message, to, cta }: {
    icon: LucideIcon; title: string; message: string; to: string; cta: string;
}) {
    return (
        <Card>
            <CardContent className="flex flex-col items-center gap-2 py-8 text-center">
                <Icon className="h-8 w-8 text-muted-foreground/60" />
                <div className="text-sm font-medium">{title}</div>
                <p className="max-w-xs text-xs text-muted-foreground">{message}</p>
                <Link to={to}>
                    <Button variant="outline" size="sm" className="mt-1">
                        {cta} <ArrowRight className="ml-1 h-3.5 w-3.5" />
                    </Button>
                </Link>
            </CardContent>
        </Card>
    );
}

// ---------------------------------------------------------------------------
// Needs attention (manager/lead triage feed) — the backend computes what's
// urgent (`/api/dashboard/needs_attention/`) so the block never goes stale;
// each item deep-links to the surface that resolves it.
// ---------------------------------------------------------------------------

function NeedsAttentionBlock() {
    const { data } = useNeedsAttention();
    const items = (data?.data ?? []).slice(0, 6);
    return (
        <Card>
            <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                    <AlertTriangle className="h-4 w-4 text-muted-foreground" />
                    Needs attention
                    {items.length > 0 && <Badge variant="secondary" className="ml-1">{items.length}</Badge>}
                </CardTitle>
            </CardHeader>
            <CardContent>
                <AttentionList
                    items={items.map((i) => ({
                        severity: i.severity,
                        message: i.message,
                        count: i.count,
                        link: i.link,
                        linkParams: i.linkParams,
                    }))}
                    emptyMessage="All clear — nothing needs attention right now."
                />
            </CardContent>
        </Card>
    );
}

// ---------------------------------------------------------------------------
// Quality KPIs (manager oversight) — the tenant-wide dashboard headline
// numbers, each a deep link to where you act on them.
// ---------------------------------------------------------------------------

function QualityKpisBlock() {
    const { data } = useDashboardKpis();
    const overdue = data?.overdue_capas ?? 0;
    return (
        <StatSection title="Quality">
            <StatTile label="Open NCRs" value={data?.open_ncrs ?? 0} icon={FileWarning} link="/quality/ncrs" />
            <StatTile label="In quarantine" value={data?.parts_in_quarantine ?? 0} icon={PackageSearch} link="/production/dispositions" />
            <StatTile label="Active CAPAs" value={data?.active_capas ?? 0} icon={ClipboardCheck} link="/quality/capas" />
            <StatTile label="Overdue CAPAs" value={overdue} icon={AlertTriangle} link="/quality/capas" variant={overdue > 0 ? "danger" : "default"} />
            <StatTile label="First pass yield" value={`${data?.current_fpy ?? 0}%`} icon={Gauge} link="/analysis" />
        </StatSection>
    );
}

// ---------------------------------------------------------------------------
// Competency coverage (HR / quality oversight) — the training-matrix headline
// risks: skills nobody can do, skills only ONE person can do (bus factor), and
// certs about to lapse. Each tile deep-links into the matrix to act on it.
// ---------------------------------------------------------------------------

function CompetencyCoverageBlock() {
    const { data, isError } = useTrainingMatrix();
    if (isError || !data) return null;
    const coverage = data.coverage ?? [];
    // No training types configured yet → nothing meaningful to show.
    if (coverage.length === 0) return null;

    const uncovered = coverage.filter((c) => c.qualified_count === 0).length;
    const spof = coverage.filter((c) => c.qualified_count === 1).length;
    const expiring = coverage.reduce((n, c) => n + (c.expiring_count ?? 0), 0);

    return (
        <StatSection title="Competency coverage">
            <StatTile
                label="Uncovered skills" value={uncovered} icon={AlertTriangle}
                link="/quality/training/matrix"
                variant={uncovered > 0 ? "danger" : "default"}
            />
            <StatTile
                label="Single-operator skills" value={spof} icon={Wrench}
                link="/quality/training/matrix"
                variant={spof > 0 ? "warning" : "default"}
            />
            <StatTile
                label="Expiring soon" value={expiring} icon={CalendarClock}
                link="/quality/training/matrix"
                variant={expiring > 0 ? "warning" : "default"}
            />
        </StatSection>
    );
}

// ---------------------------------------------------------------------------
// Available to claim (approver queue) — group-eligible approvals nobody has
// picked up yet. Hidden when empty so it never clutters the stack.
// ---------------------------------------------------------------------------

function AvailableToClaimBlock() {
    const { data: claimable = [] } = useClaimableApprovals();
    const claim = useClaimApproval();
    if (claimable.length === 0) return null;
    return (
        <Card>
            <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                    <Inbox className="h-4 w-4 text-muted-foreground" />
                    Available to claim
                    <Badge variant="secondary" className="ml-1">{claimable.length}</Badge>
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
                {claimable.slice(0, 5).map((c) => (
                    <div key={c.id} className="flex items-center gap-3 rounded-md border p-2.5">
                        <div className="min-w-0 flex-1">
                            <div className="truncate text-sm">
                                {c.approval_number} · {c.reason || c.approval_type}
                            </div>
                            {c.due_date && (
                                <div className="text-xs text-muted-foreground">due {c.due_date.slice(0, 10)}</div>
                            )}
                        </div>
                        <Button
                            size="sm" variant="outline" className="shrink-0"
                            disabled={claim.isPending}
                            onClick={() =>
                                claim.mutate(c.id, {
                                    onSuccess: () => toast.success("Claimed — moved to your approvals."),
                                    onError: () => toast.error("Could not claim (someone may have beaten you to it)."),
                                })
                            }
                        >
                            Accept
                        </Button>
                    </div>
                ))}
            </CardContent>
        </Card>
    );
}

// ---------------------------------------------------------------------------
// Documents (Document Controller) — the controlled-doc work queue: what needs
// my sign-off, what's pending, what's due for its periodic review.
// ---------------------------------------------------------------------------

function DocumentsBlock() {
    const { data } = useDocumentStats();
    const needsMe = data?.needs_my_approval ?? 0;
    const pending = data?.pending_approval ?? 0;
    const dueReview = data?.due_for_review ?? 0;
    const released = data?.released ?? 0;
    if (needsMe + pending + dueReview + released === 0) {
        return (
            <EmptyBlock
                icon={FileCheck} title="Documents"
                message="Nothing needs your sign-off or review right now."
                to="/documents" cta="Open documents"
            />
        );
    }
    return (
        <StatSection title="Documents">
            <StatTile label="Needs my approval" value={needsMe} icon={ClipboardCheck} link="/documents" variant={needsMe > 0 ? "warning" : "default"} />
            <StatTile label="Pending approval" value={pending} icon={FileText} link="/documents" />
            <StatTile label="Due for review" value={dueReview} icon={CalendarClock} link="/documents/list" variant={dueReview > 0 ? "warning" : "default"} />
            <StatTile label="Released" value={released} icon={FileCheck} link="/documents/list" />
        </StatSection>
    );
}

// ---------------------------------------------------------------------------
// Change control (Engineering) — the PCR/PCO/PCN pipeline, each a link into
// the change-control workspace. Counts only for now (the artifact hooks return
// an untyped envelope); row detail lands when the list surface is typed.
// ---------------------------------------------------------------------------

function ChangeControlBlock() {
    const { data: pcrs } = useProcessChangeRequests();
    const { data: pcos } = useProcessChangeOrders();
    const { data: pcns } = useProcessChangeNotices();
    const r = countRows(pcrs), o = countRows(pcos), n = countRows(pcns);
    if (r + o + n === 0) {
        return (
            <EmptyBlock
                icon={GitBranch} title="Change control"
                message="No change requests, orders, or notices in flight."
                to="/quality/change-control" cta="Open change control"
            />
        );
    }
    return (
        <StatSection title="Change control">
            <StatTile label="Change requests" value={r} icon={GitBranch} link="/quality/change-control" />
            <StatTile label="Change orders" value={o} icon={FileText} link="/quality/change-control" />
            <StatTile label="Change notices" value={n} icon={Megaphone} link="/quality/change-control" />
        </StatSection>
    );
}

// ---------------------------------------------------------------------------
// Outside processing at risk (Production oversight) — parts out at vendors and
// parts staged to ship. Hidden when there's no subcontract activity.
// ---------------------------------------------------------------------------

function OutsideProcessingBlock() {
    const { data: sent } = useOSPShipments({ status: "SENT" });
    const { data: ready = [] } = useReadyToShip();
    const out = countRows(sent);
    const readyCount = ready.length;
    if (out === 0 && readyCount === 0) return null;
    return (
        <StatSection title="Outside processing">
            <StatTile label="Out at vendors" value={out} icon={Truck} link="/production/outside-processing" />
            <StatTile label="Ready to ship" value={readyCount} icon={PackageSearch} link="/production/outside-processing" variant={readyCount > 0 ? "warning" : "default"} />
        </StatSection>
    );
}

// ---------------------------------------------------------------------------
// Registry + persona resolution
// ---------------------------------------------------------------------------

type BlockDef = {
    id: string;
    /** Tenant-group names (GROUP_PRESETS display names) this block serves. */
    groups: string[];
    Component: (props: { user: AuthUser }) => React.ReactNode;
};

// Every internal "doer" role (excludes external Auditor/Customer, and platform
// System Admin which sees all blocks via `seesAll`). Gates the universal blocks.
const EVERYONE = [
    "Operator", "Shift Lead", "QA Inspector", "QA Manager", "Production Manager",
    "Tenant Admin", "Document Controller", "Engineering",
];

const BLOCKS: BlockDef[] = [
    { id: "scan", groups: EVERYONE, Component: () => <ScanBox /> },
    { id: "needs-attention", groups: ["QA Manager", "Production Manager", "Shift Lead", "Tenant Admin"], Component: () => <NeedsAttentionBlock /> },
    { id: "quality-kpis", groups: ["QA Manager", "Production Manager", "Tenant Admin"], Component: () => <QualityKpisBlock /> },
    { id: "competency-coverage", groups: ["QA Manager", "Production Manager", "Tenant Admin"], Component: () => <CompetencyCoverageBlock /> },
    {
        id: "wo-queue",
        groups: ["Operator", "Shift Lead", "Production Manager", "Tenant Admin"],
        Component: ({ user }) => {
            const names = new Set((user.groups ?? []).map((g) => g.name));
            const isLead = user.is_staff || names.has("Shift Lead") || names.has("Production Manager") || names.has("Tenant Admin");
            return <WorkOrderQueue variant={isLead ? "lead" : "operator"} />;
        },
    },
    { id: "inspection", groups: ["QA Inspector", "Shift Lead", "QA Manager", "Tenant Admin"], Component: () => <InspectionQueueBlock /> },
    { id: "production-osp", groups: ["Production Manager", "Shift Lead", "Tenant Admin"], Component: () => <OutsideProcessingBlock /> },
    { id: "documents", groups: ["Document Controller", "Tenant Admin"], Component: () => <DocumentsBlock /> },
    { id: "change-control", groups: ["Engineering", "Tenant Admin"], Component: () => <ChangeControlBlock /> },
    { id: "available-to-claim", groups: ["QA Manager", "Production Manager", "Shift Lead", "Tenant Admin"], Component: () => <AvailableToClaimBlock /> },
    { id: "quality-actions", groups: EVERYONE, Component: ({ user }) => <MyQualityActionsBlock user={user} /> },
];

/** Per-persona block ordering — the first matched persona wins, so the top
 *  card is the user's main job. Managers/leads lead with oversight (triage +
 *  KPIs); doers lead with scan/queue; authoring roles lead with their domain. */
const PERSONA_ORDER: Array<{ group: string; order: string[] }> = [
    // Operator + QA Inspector are intercepted in Home to full-surface pages;
    // their order here is a fallback only.
    { group: "Operator", order: ["scan", "wo-queue", "quality-actions"] },
    { group: "QA Inspector", order: ["scan", "inspection", "quality-actions"] },
    { group: "QA Manager", order: ["needs-attention", "quality-kpis", "competency-coverage", "available-to-claim", "inspection", "quality-actions", "scan"] },
    { group: "Production Manager", order: ["needs-attention", "quality-kpis", "competency-coverage", "wo-queue", "production-osp", "available-to-claim", "quality-actions", "scan"] },
    { group: "Shift Lead", order: ["scan", "wo-queue", "needs-attention", "inspection", "production-osp", "available-to-claim", "quality-actions"] },
    { group: "Document Controller", order: ["documents", "quality-actions", "scan"] },
    { group: "Engineering", order: ["change-control", "quality-actions", "scan"] },
    { group: "Tenant Admin", order: ["needs-attention", "quality-kpis", "competency-coverage", "wo-queue", "inspection", "documents", "change-control", "available-to-claim", "production-osp", "quality-actions", "scan"] },
];

/** The user's primary persona (first PERSONA_ORDER match), or null. Home uses
 *  this to swap the whole landing for persona-specific surfaces (QA gets the
 *  inspection task inbox instead of the block stack). */
export function primaryPersona(user: AuthUser): string | null {
    const names = new Set((user.groups ?? []).map((g) => g.name));
    return PERSONA_ORDER.find((p) => names.has(p.group))?.group ?? null;
}

export function resolveHomeBlocks(user: AuthUser): BlockDef[] {
    // auth/user returns tenant-scoped groups (UserRole memberships) in `groups`
    // (TenantAwareUserDetailsSerializer) — the only group field on the payload.
    const names = new Set((user.groups ?? []).map((g) => g.name));
    // Platform staff / tenant admins see every block (support + demo view).
    const seesAll = user.is_staff || names.has("Tenant Admin") || names.has("System Admin");

    let visible = seesAll
        ? [...BLOCKS]
        : BLOCKS.filter((b) => b.groups.some((g) => names.has(g)));

    const persona = PERSONA_ORDER.find((p) => names.has(p.group));
    if (persona) {
        const rank = (id: string) => {
            const i = persona.order.indexOf(id);
            return i === -1 ? persona.order.length : i;
        };
        visible = [...visible].sort((a, b) => rank(a.id) - rank(b.id));
    }
    return visible;
}
