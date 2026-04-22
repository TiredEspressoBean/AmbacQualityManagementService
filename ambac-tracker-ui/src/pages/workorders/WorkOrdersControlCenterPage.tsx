import { useMemo, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from "@/components/ui/tooltip";
import {
    Dialog,
    DialogContent,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { StatusBadge as WoStatusBadge } from "@/components/flow/overlays/StatusBadge";
import {
    Search,
    AlertTriangle,
    Pause,
    Play,
    X,
    ChevronRight,
    PauseCircle,
    Zap,
    Calendar,
    CalendarCheck,
    Package,
    Wrench,
    ShieldAlert,
    CircleAlert,
    GitBranch,
    Split,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
    severityRank,
    type MockWorkOrder,
    type MockWorkOrderStatus,
    type ExceptionItem,
} from "./mockData";
import { WO_PRIORITY_LABELS, HOLD_REASONS, type HoldReason } from "./constants";
import { ReportExceptionDialog, type ReportExceptionPayload } from "./ReportExceptionDialog";
import { useRetrieveWorkOrders } from "@/hooks/useRetrieveWorkOrders";
import type { WorkOrderList, WorkOrderStatusEnum } from "@/lib/api/generated";
import { useExceptions } from "./useExceptions";
import { useBulkTransitionWorkOrders } from "@/hooks/useBulkTransitionWorkOrders";
import { useBulkPlaceOnHoldWorkOrders } from "@/hooks/useBulkPlaceOnHoldWorkOrders";
import { useBulkClearHoldWorkOrders } from "@/hooks/useBulkClearHoldWorkOrders";

// Nested serializer shapes that the codegen exposes as `{}`. The backend
// produces these fields on WorkOrderList; we cast through for FK crawl.
type ProcessInfo = { id?: string; name?: string; part_type_name?: string };
type RelatedOrderInfo = { id?: string; name?: string; company_name?: string };
type QaProgress = { required?: number; completed?: number };
type CurrentHold = {
    reason?: string;
    placed_at?: string;
    placed_by_name?: string;
    notes?: string;
    hours_open?: number;
};

// Adapt the real list-serializer response to the shape the UI was written
// against. Fields that have no backend counterpart are set to empty/null.
function adaptWorkOrder(w: WorkOrderList): MockWorkOrder & {
    parts_count: number;
    completed_parts_count: number;
    qa_required: number;
    qa_completed: number;
    current_hold: CurrentHold | null;
} {
    const proc = (w.process_info ?? {}) as ProcessInfo;
    const order = (w.related_order_info ?? {}) as RelatedOrderInfo;
    const qa = (w.qa_progress ?? {}) as QaProgress;
    const hold = w.current_hold != null ? (w.current_hold as CurrentHold) : null;
    return {
        id: w.id,
        erp_id: w.ERP_id,
        status: (w.workorder_status ?? "PENDING") as MockWorkOrderStatus,
        priority: (w.priority ?? 3) as 1 | 2 | 3 | 4,
        quantity: w.quantity ?? 0,
        expected_completion: w.expected_completion ?? "",
        process_name: proc.name ?? "—",
        customer: order.company_name ?? order.name ?? "—",
        part_type: proc.part_type_name ?? "—",
        is_batch: w.is_batch_work_order,
        parent_workorder_id: w.parent_workorder_id ?? null,
        split_reason: null,
        steps: [],
        edges: [],
        parts: [],
        parts_count: w.parts_count,
        completed_parts_count: w.completed_parts_count,
        qa_required: qa.required ?? 0,
        qa_completed: qa.completed ?? 0,
        current_hold: hold,
    };
}

function hoursSince(iso: string) {
    return Math.round((Date.now() - new Date(iso).getTime()) / 3600_000);
}

type TileKey = "all" | "due_today" | "overdue" | "on_hold" | "with_exceptions" | "expedited";

const KIND_ICON: Record<ExceptionItem["kind"], typeof Package> = {
    DOWNTIME: Wrench,
    QUARANTINE: ShieldAlert,
    CAPA: CircleAlert,
};

const KIND_LABEL: Record<ExceptionItem["kind"], string> = {
    DOWNTIME: "Downtime",
    QUARANTINE: "Quarantine",
    CAPA: "CAPA",
};

const HOLD_REASON_MAP = Object.fromEntries(
    HOLD_REASONS.map((r) => [r.value, r.label]),
) as Record<string, string>;

export function WorkOrdersControlCenterPage() {
    const navigate = useNavigate();
    const [tab, setTab] = useState<"work_orders" | "exceptions">("work_orders");
    const [tile, setTile] = useState<TileKey>("all");
    const [search, setSearch] = useState("");
    const [priority, setPriority] = useState("all");
    const [selected, setSelected] = useState<Set<string>>(new Set());
    const [bulkError, setBulkError] = useState<string | null>(null);

    const { data: woData, isLoading: woLoading, error: woError } = useRetrieveWorkOrders({ limit: 200 });
    const workOrders = useMemo(
        () => (woData?.results ?? []).map(adaptWorkOrder),
        [woData],
    );
    const {
        data: exceptionsData,
        isLoading: exLoading,
        error: exError,
        resolveException: resolveExceptionMutation,
    } = useExceptions();
    const [resolvedIds, setResolvedIds] = useState<Set<string>>(new Set());
    const [draftExceptions, setDraftExceptions] = useState<ExceptionItem[]>([]);
    const [reportOpen, setReportOpen] = useState(false);
    const exceptions = useMemo<ExceptionItem[]>(() => {
        const now = new Date().toISOString();
        const merged = [...draftExceptions, ...exceptionsData];
        if (resolvedIds.size === 0) return merged;
        return merged.map((e) =>
            resolvedIds.has(e.id) && !e.closed_at ? { ...e, state: "RESOLVED", closed_at: now } : e,
        );
    }, [exceptionsData, draftExceptions, resolvedIds]);

    function resolveExceptions(ids: string[]) {
        setResolvedIds((prev) => {
            const next = new Set(prev);
            ids.forEach((id) => next.add(id));
            return next;
        });
        const byId = new Map(exceptionsData.map((e) => [e.id, e]));
        ids.forEach((id) => {
            const e = byId.get(id);
            if (e) resolveExceptionMutation(e.id, e.kind);
        });
    }

    function reportException(payload: ReportExceptionPayload) {
        const erpToId = new Map(workOrders.map((w) => [w.erp_id, w.id]));
        const work_order_ids = payload.work_order_ids
            .map((v) => erpToId.get(v) ?? v)
            .filter((id) => workOrders.some((w) => w.id === id));
        const id = `exc-${Date.now()}`;
        const now = new Date().toISOString();
        setDraftExceptions((prev) => [
            {
                ...payload,
                id,
                state: "OPEN",
                opened_at: now,
                closed_at: null,
                work_order_ids,
                source_ref: `${payload.kind === "DOWNTIME" ? "DowntimeEvent" : payload.kind === "QUARANTINE" ? "QuarantineDisposition" : "CAPA"}/${id}`,
            },
            ...prev,
        ]);
    }

    const bulkTransition = useBulkTransitionWorkOrders();
    const bulkPlaceOnHold = useBulkPlaceOnHoldWorkOrders();
    const bulkClearHold = useBulkClearHoldWorkOrders();

    function handleBulkTransition(ids: string[], status: WorkOrderStatusEnum, notes?: string) {
        const real = ids.filter((id) => /^[0-9a-f-]{36}$/i.test(id));
        if (real.length === 0) return;
        setBulkError(null);
        bulkTransition.mutate(
            { ids: real, status, notes },
            {
                onError: (err) => setBulkError(String(err)),
            },
        );
    }

    function handleBulkPlaceOnHold(ids: string[], reason: string, notes?: string) {
        const real = ids.filter((id) => /^[0-9a-f-]{36}$/i.test(id));
        if (real.length === 0) return;
        setBulkError(null);
        bulkPlaceOnHold.mutate(
            { ids: real, reason, notes },
            { onError: (err) => setBulkError(String(err)) },
        );
    }

    function handleBulkClearHold(ids: string[]) {
        const real = ids.filter((id) => /^[0-9a-f-]{36}$/i.test(id));
        if (real.length === 0) return;
        setBulkError(null);
        bulkClearHold.mutate(
            { ids: real },
            { onError: (err) => setBulkError(String(err)) },
        );
    }

    // Annotate WOs with derived flags used by tiles + table.
    const annotated = useMemo(() => {
        const today = new Date();
        const openExcByWo = new Map<string, ExceptionItem[]>();
        for (const e of exceptions) {
            if (e.closed_at) continue;
            for (const woId of e.work_order_ids) {
                if (!openExcByWo.has(woId)) openExcByWo.set(woId, []);
                openExcByWo.get(woId)!.push(e);
            }
        }
        const childCountByParent = new Map<string, number>();
        for (const w of workOrders) {
            if (w.parent_workorder_id) {
                childCountByParent.set(
                    w.parent_workorder_id,
                    (childCountByParent.get(w.parent_workorder_id) ?? 0) + 1,
                );
            }
        }
        return workOrders.map((w) => {
            const overdue =
                !!w.expected_completion &&
                new Date(w.expected_completion) < today &&
                w.status !== "COMPLETED";
            const dueToday = w.expected_completion === today.toISOString().slice(0, 10);
            const expedited = w.priority === 1;
            const openExceptions = openExcByWo.get(w.id) ?? [];
            const parentWo = w.parent_workorder_id
                ? workOrders.find((wo) => wo.id === w.parent_workorder_id)
                : undefined;
            const parentErp = parentWo
                ? parentWo.erp_id
                : w.parent_workorder_id
                  ? w.parent_workorder_id.slice(0, 8)
                  : null;
            return {
                ...w,
                overdue,
                dueToday,
                expedited,
                openExceptions,
                childCount: childCountByParent.get(w.id) ?? 0,
                parentErp,
            };
        });
    }, [workOrders, exceptions]);

    // Tile counts.
    const tileCounts = useMemo(
        () => ({
            all: annotated.length,
            due_today: annotated.filter((w) => w.dueToday && w.status !== "COMPLETED").length,
            overdue: annotated.filter((w) => w.overdue).length,
            on_hold: annotated.filter((w) => w.status === "ON_HOLD").length,
            with_exceptions: annotated.filter((w) => w.openExceptions.length > 0).length,
            expedited: annotated.filter((w) => w.expedited).length,
        }),
        [annotated],
    );

    const rows = useMemo(() => {
        return annotated.filter((w) => {
            if (priority !== "all" && String(w.priority) !== priority) return false;
            if (
                search &&
                !w.erp_id.toLowerCase().includes(search.toLowerCase()) &&
                !w.customer.toLowerCase().includes(search.toLowerCase())
            )
                return false;
            switch (tile) {
                case "due_today":
                    return w.dueToday && w.status !== "COMPLETED";
                case "overdue":
                    return w.overdue;
                case "on_hold":
                    return w.status === "ON_HOLD";
                case "with_exceptions":
                    return w.openExceptions.length > 0;
                case "expedited":
                    return w.expedited;
                default:
                    return true;
            }
        });
    }, [annotated, priority, search, tile]);

    const openExceptionCount = exceptions.filter((e) => !e.closed_at).length;

    const allVisibleSelected = rows.length > 0 && rows.every((r) => selected.has(r.id));
    const someVisibleSelected = rows.some((r) => selected.has(r.id));

    function toggleAll() {
        setSelected((prev) => {
            const next = new Set(prev);
            if (allVisibleSelected) rows.forEach((r) => next.delete(r.id));
            else rows.forEach((r) => next.add(r.id));
            return next;
        });
    }
    function toggleOne(id: string) {
        setSelected((prev) => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
        });
    }

    return (
        <TooltipProvider>
            <div className="space-y-4 p-6 pb-24">
                <div>
                    <h1 className="text-2xl font-semibold">Work Orders · Control Center</h1>
                    <p className="text-sm text-muted-foreground">
                        Fleet view. Filter, select, act across multiple work orders.
                    </p>
                </div>

                {(woError || exError) && (
                    <div className="rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive">
                        {woError && <div>Failed to load work orders: {woError.message}</div>}
                        {exError && <div>Failed to load exceptions: {exError.message}</div>}
                    </div>
                )}
                {bulkError && (
                    <div className="rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive">
                        Bulk action failed: {bulkError}
                        <button className="ml-2 underline" onClick={() => setBulkError(null)}>
                            Dismiss
                        </button>
                    </div>
                )}
                {(woLoading || exLoading) && !woData && (
                    <div className="rounded-md border bg-muted/30 p-3 text-sm text-muted-foreground">
                        Loading…
                    </div>
                )}

                <Tabs value={tab} onValueChange={(v) => setTab(v as typeof tab)}>
                    <TabsList>
                        <TabsTrigger value="work_orders">
                            Work Orders
                            <Badge variant="secondary" className="ml-2 px-1.5">
                                {annotated.length}
                            </Badge>
                        </TabsTrigger>
                        <TabsTrigger value="exceptions">
                            Exceptions
                            {openExceptionCount > 0 && (
                                <Badge variant="destructive" className="ml-2 px-1.5">
                                    {openExceptionCount}
                                </Badge>
                            )}
                        </TabsTrigger>
                    </TabsList>

                    {/* -------- WORK ORDERS TAB -------- */}
                    <TabsContent value="work_orders" className="mt-4 space-y-4">
                        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
                            <Tile
                                active={tile === "all"}
                                onClick={() => setTile("all")}
                                label="All"
                                count={tileCounts.all}
                                Icon={CalendarCheck}
                            />
                            <Tile
                                active={tile === "due_today"}
                                onClick={() => setTile("due_today")}
                                label="Due today"
                                count={tileCounts.due_today}
                                Icon={Calendar}
                            />
                            <Tile
                                active={tile === "overdue"}
                                onClick={() => setTile("overdue")}
                                label="Overdue"
                                count={tileCounts.overdue}
                                Icon={AlertTriangle}
                                emphasis="destructive"
                            />
                            <Tile
                                active={tile === "on_hold"}
                                onClick={() => setTile("on_hold")}
                                label="On hold"
                                count={tileCounts.on_hold}
                                Icon={PauseCircle}
                            />
                            <Tile
                                active={tile === "with_exceptions"}
                                onClick={() => setTile("with_exceptions")}
                                label="With exceptions"
                                count={tileCounts.with_exceptions}
                                Icon={CircleAlert}
                                emphasis="destructive"
                            />
                            <Tile
                                active={tile === "expedited"}
                                onClick={() => setTile("expedited")}
                                label="Expedited"
                                count={tileCounts.expedited}
                                Icon={Zap}
                            />
                        </div>

                        <Card>
                            <CardContent className="space-y-3 p-4">
                                <div className="flex flex-wrap items-center gap-2">
                                    <div className="relative">
                                        <Search className="absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                                        <Input
                                            placeholder="Search ERP ID or customer…"
                                            value={search}
                                            onChange={(e) => setSearch(e.target.value)}
                                            className="w-72 pl-8"
                                        />
                                    </div>
                                    <Select value={priority} onValueChange={setPriority}>
                                        <SelectTrigger className="w-36">
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="all">Any priority</SelectItem>
                                            {Object.entries(WO_PRIORITY_LABELS).map(([k, v]) => (
                                                <SelectItem key={k} value={k}>
                                                    {v.label}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                    {tile !== "all" && (
                                        <Button size="sm" variant="ghost" onClick={() => setTile("all")}>
                                            <X className="mr-1 h-3 w-3" />
                                            Clear tile filter
                                        </Button>
                                    )}
                                    <div className="ml-auto text-sm text-muted-foreground">
                                        {rows.length} of {annotated.length}
                                    </div>
                                </div>

                                <Table>
                                    <TableHeader>
                                        <TableRow>
                                            <TableHead className="w-10">
                                                <Checkbox
                                                    checked={
                                                        allVisibleSelected
                                                            ? true
                                                            : someVisibleSelected
                                                              ? "indeterminate"
                                                              : false
                                                    }
                                                    onCheckedChange={toggleAll}
                                                />
                                            </TableHead>
                                            <TableHead>ERP ID</TableHead>
                                            <TableHead>Status</TableHead>
                                            <TableHead>Priority</TableHead>
                                            <TableHead>Process</TableHead>
                                            <TableHead>Customer</TableHead>
                                            <TableHead>Progress</TableHead>
                                            <TableHead>QA</TableHead>
                                            <TableHead>Due</TableHead>
                                            <TableHead className="w-10" />
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {rows.map((r) => {
                                            const priorityCfg = WO_PRIORITY_LABELS[r.priority];
                                            const pct =
                                                r.parts_count > 0
                                                    ? Math.min(
                                                          100,
                                                          Math.round(
                                                              (r.completed_parts_count / r.parts_count) * 100,
                                                          ),
                                                      )
                                                    : 0;
                                            return (
                                                <TableRow
                                                    key={r.id}
                                                    className={cn("cursor-pointer", selected.has(r.id) && "bg-accent/50")}
                                                    onClick={() => navigate({ to: `/workorder/${r.id}/control` })}
                                                >
                                                    <TableCell onClick={(e) => e.stopPropagation()}>
                                                        <Checkbox
                                                            checked={selected.has(r.id)}
                                                            onCheckedChange={() => toggleOne(r.id)}
                                                        />
                                                    </TableCell>
                                                    <TableCell>
                                                        <div className="flex items-center gap-2">
                                                            <span className="font-mono text-sm">{r.erp_id}</span>
                                                            {r.parentErp && (
                                                                <Tooltip>
                                                                    <TooltipTrigger asChild>
                                                                        <Badge variant="outline" className="text-[10px]">
                                                                            <GitBranch className="mr-0.5 h-2.5 w-2.5" />
                                                                            split
                                                                        </Badge>
                                                                    </TooltipTrigger>
                                                                    <TooltipContent>Split from {r.parentErp}</TooltipContent>
                                                                </Tooltip>
                                                            )}
                                                            {r.childCount > 0 && (
                                                                <Tooltip>
                                                                    <TooltipTrigger asChild>
                                                                        <Badge variant="secondary" className="text-[10px]">
                                                                            <Split className="mr-0.5 h-2.5 w-2.5" />
                                                                            {r.childCount}
                                                                        </Badge>
                                                                    </TooltipTrigger>
                                                                    <TooltipContent>
                                                                        {r.childCount} child WO{r.childCount === 1 ? "" : "s"} split from this one
                                                                    </TooltipContent>
                                                                </Tooltip>
                                                            )}
                                                            {r.is_batch && (
                                                                <Badge variant="outline" className="text-[10px]">
                                                                    Batch
                                                                </Badge>
                                                            )}
                                                            {r.expedited && (
                                                                <Tooltip>
                                                                    <TooltipTrigger asChild>
                                                                        <Badge
                                                                            variant="outline"
                                                                            className="text-[10px]"
                                                                        >
                                                                            <Zap className="mr-0.5 h-2.5 w-2.5" />
                                                                            Expedited
                                                                        </Badge>
                                                                    </TooltipTrigger>
                                                                    <TooltipContent>Priority 1 — urgent queue</TooltipContent>
                                                                </Tooltip>
                                                            )}
                                                            {r.openExceptions.length > 0 && (
                                                                <Tooltip>
                                                                    <TooltipTrigger asChild>
                                                                        <Badge variant="destructive" className="text-[10px]">
                                                                            <CircleAlert className="mr-0.5 h-2.5 w-2.5" />
                                                                            {r.openExceptions.length}
                                                                        </Badge>
                                                                    </TooltipTrigger>
                                                                    <TooltipContent>
                                                                        {r.openExceptions
                                                                            .map((e) => `${KIND_LABEL[e.kind]}: ${e.title}`)
                                                                            .join(" · ")}
                                                                    </TooltipContent>
                                                                </Tooltip>
                                                            )}
                                                        </div>
                                                    </TableCell>
                                                    <TableCell>
                                                        <div className="flex items-center gap-1.5">
                                                            <WoStatusBadge status={r.status} />
                                                            {r.current_hold != null && (
                                                                <Tooltip>
                                                                    <TooltipTrigger asChild>
                                                                        <Badge
                                                                            variant="secondary"
                                                                            className="text-[10px]"
                                                                        >
                                                                            <PauseCircle className="mr-0.5 h-2.5 w-2.5" />
                                                                            {HOLD_REASON_MAP[r.current_hold.reason ?? ""] ??
                                                                                r.current_hold.reason}{" "}
                                                                            · {r.current_hold.hours_open ?? 0}h
                                                                        </Badge>
                                                                    </TooltipTrigger>
                                                                    {r.current_hold.notes && (
                                                                        <TooltipContent>
                                                                            {r.current_hold.notes}
                                                                        </TooltipContent>
                                                                    )}
                                                                </Tooltip>
                                                            )}
                                                        </div>
                                                    </TableCell>
                                                    <TableCell>
                                                        <Badge className={cn(priorityCfg.className)} variant="secondary">
                                                            {priorityCfg.label}
                                                        </Badge>
                                                    </TableCell>
                                                    <TableCell className="text-sm">{r.process_name}</TableCell>
                                                    <TableCell className="text-sm">{r.customer}</TableCell>
                                                    <TableCell>
                                                        <div className="flex items-center gap-2">
                                                            <div className="h-2 w-24 overflow-hidden rounded-full bg-muted">
                                                                <div
                                                                    className="h-full bg-primary"
                                                                    style={{ width: `${pct}%` }}
                                                                />
                                                            </div>
                                                            <span className="text-xs tabular-nums text-muted-foreground">
                                                                {r.completed_parts_count}/{r.parts_count}
                                                            </span>
                                                        </div>
                                                    </TableCell>
                                                    <TableCell>
                                                        {r.qa_required > 0 ? (
                                                            <span className="text-xs tabular-nums">
                                                                {r.qa_completed}/{r.qa_required}
                                                            </span>
                                                        ) : (
                                                            <span className="text-xs text-muted-foreground">—</span>
                                                        )}
                                                    </TableCell>
                                                    <TableCell>
                                                        <div className="flex items-center gap-2 text-sm">
                                                            {r.expected_completion}
                                                            {r.overdue && (
                                                                <Badge
                                                                    variant="destructive"
                                                                    className="px-1 py-0 text-[10px]"
                                                                >
                                                                    Overdue
                                                                </Badge>
                                                            )}
                                                        </div>
                                                    </TableCell>
                                                    <TableCell>
                                                        <ChevronRight className="h-4 w-4 text-muted-foreground" />
                                                    </TableCell>
                                                </TableRow>
                                            );
                                        })}
                                        {rows.length === 0 && (
                                            <TableRow>
                                                <TableCell colSpan={9} className="py-8 text-center text-muted-foreground">
                                                    No work orders match these filters.
                                                </TableCell>
                                            </TableRow>
                                        )}
                                    </TableBody>
                                </Table>
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* -------- EXCEPTIONS TAB -------- */}
                    <TabsContent value="exceptions" className="mt-4 space-y-4">
                        <ExceptionsList
                            exceptions={exceptions}
                            workOrders={annotated}
                            onOpenWorkOrder={(id) => navigate({ to: `/workorder/${id}/control` })}
                            onResolve={(ids) => resolveExceptions(ids)}
                            onReport={() => setReportOpen(true)}
                        />
                    </TabsContent>
                </Tabs>

                {selected.size > 0 && tab === "work_orders" && (
                    <FleetBulkBar
                        selectedIds={Array.from(selected)}
                        workOrders={workOrders}
                        onRelease={(ids) => handleBulkTransition(ids, "IN_PROGRESS")}
                        onHold={(ids, reason, notes) => handleBulkPlaceOnHold(ids, reason, notes)}
                        onClearHold={(ids) => handleBulkClearHold(ids)}
                        onChangeStatus={(ids, status) => handleBulkTransition(ids, status)}
                        onSplit={(id) => navigate({ to: `/workorder/${id}/control` })}
                        onReport={() => setReportOpen(true)}
                        onClear={() => setSelected(new Set())}
                    />
                )}

                <ReportExceptionDialog
                    open={reportOpen}
                    onOpenChange={setReportOpen}
                    onSubmit={reportException}
                />
            </div>
        </TooltipProvider>
    );
}

function FleetBulkBar({
    selectedIds,
    workOrders,
    onRelease,
    onHold,
    onClearHold,
    onChangeStatus,
    onSplit,
    onReport,
    onClear,
}: {
    selectedIds: string[];
    workOrders: (MockWorkOrder & { current_hold: { reason?: string; notes?: string; hours_open?: number } | null })[];
    onRelease: (ids: string[]) => void;
    onHold: (ids: string[], reason: string, notes?: string) => void;
    onClearHold: (ids: string[]) => void;
    onChangeStatus: (ids: string[], status: WorkOrderStatusEnum) => void;
    onSplit: (id: string) => void;
    onReport: () => void;
    onClear: () => void;
}) {
    const [changeOpen, setChangeOpen] = useState(false);
    const [holdOpen, setHoldOpen] = useState(false);
    const [targetStatus, setTargetStatus] = useState<WorkOrderStatusEnum>("IN_PROGRESS");
    const [holdReason, setHoldReason] = useState<HoldReason>("MATERIAL");
    const [holdNotes, setHoldNotes] = useState("");

    const selectedWOs = workOrders.filter((w) => selectedIds.includes(w.id));
    const releasable = selectedWOs.filter((w) => w.status === "PENDING").map((w) => w.id);
    const holdable = selectedWOs
        .filter((w) => w.status === "IN_PROGRESS" || w.status === "PENDING")
        .map((w) => w.id);
    const holdcleared = selectedWOs.filter((w) => w.status === "ON_HOLD").map((w) => w.id);

    return (
        <>
            <div className="fixed bottom-6 left-1/2 z-40 -translate-x-1/2">
                <Card className="border-primary shadow-lg">
                    <CardContent className="flex items-center gap-2 p-3">
                        <div className="mr-2 border-r pr-2 text-sm font-medium">
                            {selectedIds.length} selected
                        </div>
                        <Tooltip>
                            <TooltipTrigger asChild>
                                <span>
                                    <Button
                                        size="sm"
                                        variant="outline"
                                        disabled={releasable.length === 0}
                                        onClick={() => releasable.length > 0 && onRelease(releasable)}
                                    >
                                        <Play className="mr-1 h-4 w-4" />
                                        Release {releasable.length > 0 ? `(${releasable.length})` : ""}
                                    </Button>
                                </span>
                            </TooltipTrigger>
                            <TooltipContent>Only PENDING work orders</TooltipContent>
                        </Tooltip>
                        <Tooltip>
                            <TooltipTrigger asChild>
                                <span>
                                    <Button
                                        size="sm"
                                        variant="outline"
                                        disabled={holdable.length === 0}
                                        onClick={() => holdable.length > 0 && setHoldOpen(true)}
                                    >
                                        <Pause className="mr-1 h-4 w-4" />
                                        Hold {holdable.length > 0 ? `(${holdable.length})` : ""}
                                    </Button>
                                </span>
                            </TooltipTrigger>
                            <TooltipContent>PENDING or IN_PROGRESS only</TooltipContent>
                        </Tooltip>
                        <Tooltip>
                            <TooltipTrigger asChild>
                                <span>
                                    <Button
                                        size="sm"
                                        variant="outline"
                                        disabled={holdcleared.length === 0}
                                        onClick={() => holdcleared.length > 0 && onClearHold(holdcleared)}
                                    >
                                        Clear hold {holdcleared.length > 0 ? `(${holdcleared.length})` : ""}
                                    </Button>
                                </span>
                            </TooltipTrigger>
                            <TooltipContent>Only ON_HOLD work orders</TooltipContent>
                        </Tooltip>
                        <Button size="sm" variant="outline" onClick={() => setChangeOpen(true)}>
                            Change status…
                        </Button>
                        <Button size="sm" variant="outline" onClick={onReport}>
                            <CircleAlert className="mr-1 h-4 w-4" />
                            Report exception
                        </Button>
                        <Button
                            size="sm"
                            variant="outline"
                            disabled={selectedIds.length !== 1}
                            onClick={() => selectedIds.length === 1 && onSplit(selectedIds[0])}
                        >
                            <Split className="mr-1 h-4 w-4" />
                            Split…
                        </Button>
                        <Button size="icon" variant="ghost" onClick={onClear}>
                            <X className="h-4 w-4" />
                        </Button>
                    </CardContent>
                </Card>
            </div>

            <Dialog open={changeOpen} onOpenChange={setChangeOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Change status for {selectedIds.length} WOs</DialogTitle>
                    </DialogHeader>
                    <Select
                        value={targetStatus}
                        onValueChange={(v) => setTargetStatus(v as WorkOrderStatusEnum)}
                    >
                        <SelectTrigger>
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="PENDING">Pending</SelectItem>
                            <SelectItem value="IN_PROGRESS">In Progress</SelectItem>
                            <SelectItem value="WAITING_FOR_OPERATOR">Waiting for Operator</SelectItem>
                            <SelectItem value="ON_HOLD">On Hold</SelectItem>
                            <SelectItem value="COMPLETED">Completed</SelectItem>
                            <SelectItem value="CANCELLED">Cancelled</SelectItem>
                        </SelectContent>
                    </Select>
                    <DialogFooter>
                        <Button variant="ghost" onClick={() => setChangeOpen(false)}>
                            Cancel
                        </Button>
                        <Button
                            onClick={() => {
                                onChangeStatus(selectedIds, targetStatus);
                                setChangeOpen(false);
                            }}
                        >
                            Apply to {selectedIds.length}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <Dialog open={holdOpen} onOpenChange={setHoldOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Place {holdable.length} WO{holdable.length === 1 ? "" : "s"} on hold</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-3">
                        <Select
                            value={holdReason}
                            onValueChange={(v) => setHoldReason(v as HoldReason)}
                        >
                            <SelectTrigger>
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                {HOLD_REASONS.map((r) => (
                                    <SelectItem key={r.value} value={r.value}>
                                        {r.label}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        <Textarea
                            placeholder="Notes (optional)"
                            value={holdNotes}
                            onChange={(e) => setHoldNotes(e.target.value)}
                            rows={3}
                        />
                    </div>
                    <DialogFooter>
                        <Button variant="ghost" onClick={() => setHoldOpen(false)}>
                            Cancel
                        </Button>
                        <Button
                            onClick={() => {
                                onHold(holdable, holdReason, holdNotes || undefined);
                                setHoldNotes("");
                                setHoldOpen(false);
                            }}
                        >
                            Apply to {holdable.length}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}

function Tile({
    label,
    count,
    Icon,
    active,
    emphasis,
    onClick,
}: {
    label: string;
    count: number;
    Icon: typeof Package;
    active: boolean;
    /**
     * "destructive" dims the count red when non-zero (overdue, with exceptions).
     * Default has no semantic tone — relies on label + count for meaning.
     */
    emphasis?: "destructive";
    onClick: () => void;
}) {
    const isAlert = emphasis === "destructive" && count > 0;
    return (
        <button
            onClick={onClick}
            className={cn(
                "flex flex-col gap-1 rounded-md border bg-card px-3 py-2 text-left transition-colors",
                active && "ring-2 ring-ring border-ring",
                !active && "hover:bg-accent hover:text-accent-foreground",
            )}
        >
            <div className="flex items-center justify-between">
                <span className="text-xs font-medium">{label}</span>
                <Icon
                    className={cn(
                        "h-3.5 w-3.5",
                        isAlert ? "text-destructive" : "text-muted-foreground",
                    )}
                />
            </div>
            <div
                className={cn(
                    "text-2xl font-semibold tabular-nums",
                    count === 0 && "text-muted-foreground",
                    isAlert && "text-destructive",
                )}
            >
                {count}
            </div>
        </button>
    );
}

type ExceptionSort = "age" | "severity" | "impact";

// Per-kind action: Downtime resolves in-place; Quarantine + CAPA redirect
// to their canonical management pages so the user doesn't lose the full
// disposition / CAPA workflow context.
function ExceptionRowAction({
    exc,
    onResolve,
}: {
    exc: ExceptionItem;
    onResolve: (ids: string[]) => void;
}) {
    const navigate = useNavigate();
    const isOpen = !exc.closed_at;
    if (exc.kind === "DOWNTIME") {
        return (
            <Button
                size="sm"
                variant="outline"
                className="w-full"
                disabled={!isOpen}
                onClick={() => onResolve([exc.id])}
            >
                <Wrench className="mr-1 h-3 w-3" />
                Resolve
            </Button>
        );
    }
    if (exc.kind === "QUARANTINE") {
        return (
            <Button
                size="sm"
                variant="outline"
                className="w-full"
                onClick={() => navigate({ to: `/dispositions/edit/${exc.id}` })}
            >
                Open disposition
            </Button>
        );
    }
    return (
        <Button
            size="sm"
            variant="outline"
            className="w-full"
            onClick={() => navigate({ to: `/quality/capas/${exc.id}` })}
        >
            Open CAPA
        </Button>
    );
}

function ExceptionsList({
    exceptions,
    workOrders,
    onOpenWorkOrder,
    onResolve,
    onReport,
}: {
    exceptions: ExceptionItem[];
    workOrders: MockWorkOrder[];
    onOpenWorkOrder: (id: string) => void;
    onResolve: (ids: string[]) => void;
    onReport: () => void;
}) {
    const [openOnly, setOpenOnly] = useState(true);
    const [kindFilter, setKindFilter] = useState<string>("all");
    const [severityFilter, setSeverityFilter] = useState<string>("all");
    const [sort, setSort] = useState<ExceptionSort>("age");
    const [selected, setSelected] = useState<Set<string>>(new Set());

    const woById = useMemo(() => {
        const m = new Map<string, MockWorkOrder>();
        workOrders.forEach((w) => m.set(w.id, w));
        return m;
    }, [workOrders]);

    const filtered = useMemo(() => {
        const rows = exceptions.filter((e) => {
            if (openOnly && e.closed_at) return false;
            if (kindFilter !== "all" && e.kind !== kindFilter) return false;
            if (severityFilter !== "all" && e.severity !== severityFilter) return false;
            return true;
        });
        const sorted = [...rows];
        if (sort === "age") {
            sorted.sort((a, b) => new Date(a.opened_at).getTime() - new Date(b.opened_at).getTime());
        } else if (sort === "severity") {
            sorted.sort((a, b) => severityRank(b.severity) - severityRank(a.severity));
        } else {
            sorted.sort((a, b) => b.work_order_ids.length - a.work_order_ids.length);
        }
        return sorted;
    }, [exceptions, openOnly, kindFilter, severityFilter, sort]);

    const openIds = filtered.filter((e) => !e.closed_at).map((e) => e.id);
    const selectedDowntimeIds = filtered
        .filter((e) => e.kind === "DOWNTIME" && !e.closed_at && selected.has(e.id))
        .map((e) => e.id);
    const allOpenSelected = openIds.length > 0 && openIds.every((id) => selected.has(id));
    const someOpenSelected = openIds.some((id) => selected.has(id));
    function toggleAllOpen() {
        setSelected((prev) => {
            const next = new Set(prev);
            if (allOpenSelected) openIds.forEach((id) => next.delete(id));
            else openIds.forEach((id) => next.add(id));
            return next;
        });
    }
    function toggleOne(id: string) {
        setSelected((prev) => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
        });
    }

    return (
        <Card>
            <CardContent className="space-y-3 p-4">
                <div className="flex flex-wrap items-center gap-2">
                    <Button
                        size="sm"
                        variant={openOnly ? "default" : "outline"}
                        onClick={() => setOpenOnly((v) => !v)}
                    >
                        Open only
                    </Button>
                    <Select value={kindFilter} onValueChange={setKindFilter}>
                        <SelectTrigger className="w-44">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="all">All sources</SelectItem>
                            <SelectItem value="DOWNTIME">Downtime events</SelectItem>
                            <SelectItem value="QUARANTINE">Quarantine dispositions</SelectItem>
                            <SelectItem value="CAPA">CAPAs</SelectItem>
                        </SelectContent>
                    </Select>
                    <Select value={severityFilter} onValueChange={setSeverityFilter}>
                        <SelectTrigger className="w-36">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="all">Any severity</SelectItem>
                            <SelectItem value="CRITICAL">Critical</SelectItem>
                            <SelectItem value="HIGH">High</SelectItem>
                            <SelectItem value="MEDIUM">Medium</SelectItem>
                            <SelectItem value="LOW">Low</SelectItem>
                        </SelectContent>
                    </Select>
                    <Select value={sort} onValueChange={(v) => setSort(v as ExceptionSort)}>
                        <SelectTrigger className="w-36">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="age">Oldest first</SelectItem>
                            <SelectItem value="severity">Highest severity</SelectItem>
                            <SelectItem value="impact">Most WOs impacted</SelectItem>
                        </SelectContent>
                    </Select>
                    <Button size="sm" variant="outline" onClick={onReport}>
                        <CircleAlert className="mr-1 h-4 w-4" />
                        Report exception
                    </Button>
                    <div className="ml-auto text-xs text-muted-foreground">
                        Unified · {filtered.length} items
                    </div>
                </div>

                {openIds.length > 0 && (
                    <div className="flex items-center gap-2 rounded-md border bg-muted/40 px-3 py-1.5 text-xs">
                        <Checkbox
                            checked={allOpenSelected ? true : someOpenSelected ? "indeterminate" : false}
                            onCheckedChange={toggleAllOpen}
                        />
                        <span className="text-muted-foreground">Select all open · {openIds.length}</span>
                        <div className="ml-auto flex items-center gap-2">
                            <span>{selected.size} selected</span>
                            <Tooltip>
                                <TooltipTrigger asChild>
                                    <span>
                                        <Button
                                            size="sm"
                                            variant="outline"
                                            className="h-7 text-xs"
                                            disabled={selectedDowntimeIds.length === 0}
                                            onClick={() => {
                                                onResolve(selectedDowntimeIds);
                                                setSelected(new Set());
                                            }}
                                        >
                                            Bulk resolve downtime{" "}
                                            {selectedDowntimeIds.length > 0 ? `(${selectedDowntimeIds.length})` : ""}
                                        </Button>
                                    </span>
                                </TooltipTrigger>
                                <TooltipContent>
                                    Quarantine dispositions and CAPAs resolve via their own
                                    management pages — open them from the row action.
                                </TooltipContent>
                            </Tooltip>
                        </div>
                    </div>
                )}

                <div className="divide-y rounded-md border">
                    {filtered.map((e) => {
                        const Icon = KIND_ICON[e.kind];
                        const impacted = e.work_order_ids
                            .map((id) => woById.get(id))
                            .filter((w): w is MockWorkOrder => !!w);
                        const isOpen = !e.closed_at;
                        return (
                            <div key={e.id} className="grid grid-cols-[auto_auto_1fr_auto] items-start gap-3 p-3">
                                <Checkbox
                                    className="mt-1"
                                    checked={selected.has(e.id)}
                                    onCheckedChange={() => toggleOne(e.id)}
                                    disabled={!isOpen}
                                />
                                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border bg-muted">
                                    <Icon className="h-4 w-4" />
                                </div>
                                <div className="min-w-0 space-y-1">
                                    <div className="flex flex-wrap items-center gap-2">
                                        <Badge variant="outline" className="text-[10px]">
                                            {KIND_LABEL[e.kind]}
                                        </Badge>
                                        <Badge
                                            variant={
                                                e.severity === "CRITICAL" || e.severity === "HIGH"
                                                    ? "destructive"
                                                    : "secondary"
                                            }
                                            className="text-[10px]"
                                        >
                                            {e.severity}
                                        </Badge>
                                        <Badge variant="outline" className="text-[10px]">
                                            {e.state.replace(/_/g, " ")}
                                        </Badge>
                                        <span className="text-[11px] text-muted-foreground">
                                            {hoursSince(e.opened_at)}h ago · {e.reported_by}
                                        </span>
                                        <span className="text-[10px] font-mono text-muted-foreground">
                                            {e.source_ref}
                                        </span>
                                    </div>
                                    <div className="text-sm font-medium">{e.title}</div>
                                    <div className="text-sm text-muted-foreground">{e.description}</div>
                                    <div className="flex flex-wrap items-center gap-1 pt-1 text-xs">
                                        <span className="text-muted-foreground">
                                            Impacts {impacted.length} WO{impacted.length === 1 ? "" : "s"}:
                                        </span>
                                        {impacted.map((w) => (
                                            <button
                                                key={w.id}
                                                onClick={() => onOpenWorkOrder(w.id)}
                                                className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px] hover:bg-accent"
                                            >
                                                {w.erp_id}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                                <div className="flex flex-col items-end gap-1">
                                    <ExceptionRowAction exc={e} onResolve={onResolve} />
                                </div>
                            </div>
                        );
                    })}
                    {filtered.length === 0 && (
                        <div className="py-8 text-center text-sm text-muted-foreground">No exceptions match.</div>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}

export default WorkOrdersControlCenterPage;
