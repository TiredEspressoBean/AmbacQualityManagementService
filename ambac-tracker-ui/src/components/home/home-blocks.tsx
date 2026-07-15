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
import { ArrowRight, CheckSquare, PackageSearch, ScanLine, Wrench } from "lucide-react";
import type { AuthUser } from "@/hooks/useAuthUser";
import { useMyCapaTasks } from "@/hooks/useMyCapaTasks";
import { useMyPendingApprovals } from "@/hooks/useMyPendingApprovals";
import { useIncomingInspection } from "@/hooks/useIncomingInspection";
import { StartWorkDialog } from "@/components/workorder/StartWorkDialog";

// ---------------------------------------------------------------------------
// Scan box — traveler-first entry. Accepts keyboard-wedge scanners (they type
// the code + Enter) and manual typing; resolves a WO ERP id or part ERP id and
// navigates to the work order's control page (ops + inspection live there).
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
// Registry + persona resolution
// ---------------------------------------------------------------------------

type BlockDef = {
    id: string;
    /** Tenant-group names (GROUP_PRESETS display names) this block serves. */
    groups: string[];
    Component: (props: { user: AuthUser }) => React.ReactNode;
};

const EVERYONE = ["Operator", "Shift Lead", "QA Inspector", "QA Manager", "Production Manager", "Tenant Admin"];

const BLOCKS: BlockDef[] = [
    { id: "scan", groups: EVERYONE, Component: () => <ScanBox /> },
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
    { id: "quality-actions", groups: EVERYONE, Component: ({ user }) => <MyQualityActionsBlock user={user} /> },
];

/** Per-persona block ordering — the first matched persona wins, so the top
 *  card (after the scan box) is the user's main job. */
const PERSONA_ORDER: Array<{ group: string; order: string[] }> = [
    { group: "Operator", order: ["scan", "wo-queue", "quality-actions"] },
    { group: "Shift Lead", order: ["scan", "wo-queue", "inspection", "quality-actions"] },
    { group: "QA Inspector", order: ["scan", "inspection", "quality-actions"] },
    { group: "QA Manager", order: ["scan", "inspection", "quality-actions", "wo-queue"] },
    { group: "Production Manager", order: ["scan", "wo-queue", "quality-actions"] },
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
