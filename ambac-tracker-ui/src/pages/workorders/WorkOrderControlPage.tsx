import { Fragment, useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useParams, useNavigate } from "@tanstack/react-router";
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
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
    Sheet,
    SheetContent,
    SheetDescription,
    SheetHeader,
    SheetTitle,
} from "@/components/ui/sheet";
import { StatusBadge as WoStatusBadge } from "@/components/flow/overlays/StatusBadge";
import { StatusBadge as PartStatusBadge } from "@/components/ui/status-badge";
import {
    AlertTriangle,
    ArrowLeft,
    CheckCircle2,
    ChevronDown,
    ChevronLeft,
    ChevronRight,
    CircleAlert,
    GitBranch,
    MoreHorizontal,
    PauseCircle,
    ShieldAlert,
    Split,
    Undo2,
    Wrench,
    X,
    XCircle,
    Search,
    FileText,
} from "lucide-react";
import { UndoSplitButton } from "./SplitWorkOrderUndo";
import { ReportExceptionDialog, type ReportExceptionPayload } from "./ReportExceptionDialog";

type SplitMode = "QUANTITY" | "OPERATION" | "REWORK";
const MOCK_REWORK_PROCESSES = [
    { id: "proc-rework-injector", name: "Injector Rework Rev A" },
    { id: "proc-rework-generic", name: "Generic Rework Loop" },
];
import { cn } from "@/lib/utils";
import {
    type ExceptionItem,
    type MockPart,
    type MockPartStatus,
    type MockStep,
    type MockStepEdge,
    type MockStepType,
    type MockWorkOrder,
    type MockStepVisit,
} from "./mockData";
import { WO_PRIORITY_LABELS, HOLD_REASONS, STATUS_BAR_FILL, type HoldReason } from "./constants";
import { useRetrieveWorkOrder } from "@/hooks/useRetrieveWorkOrder";
import { useRetrieveParts } from "@/hooks/useRetrieveParts";
import { usePartTraveler } from "@/hooks/usePartTraveler";
import { useRetrieveProcessWithSteps } from "@/hooks/useRetrieveProcessWithSteps";
import { useUpdatePart } from "@/hooks/useUpdatePart";
import { useBulkIncrementParts } from "@/hooks/useBulkIncrementParts";
import { useBulkRollbackParts } from "@/hooks/useBulkRollbackParts";
import { useBulkSetStatusParts } from "@/hooks/useBulkSetStatusParts";
import { usePlaceOnHoldWorkOrder } from "@/hooks/usePlaceOnHoldWorkOrder";
import { useClearHoldWorkOrder } from "@/hooks/useClearHoldWorkOrder";
import { useSplitWorkOrder } from "@/hooks/useSplitWorkOrder";
import { useUndoSplitWorkOrder } from "@/hooks/useUndoSplitWorkOrder";
import { ReactFlowProvider } from "@xyflow/react";
import { FlowCanvas, type StepData as FlowStepData } from "@/components/flow";
import "@xyflow/react/dist/style.css";
import { useExceptions } from "./useExceptions";
import type {
    WorkOrder,
    Parts as PartRow,
    TravelerStepEntry,
    Processes as ProcessRecord,
    ProcessStep,
    StepEdge,
} from "@/lib/api/generated";

// Adapt the real detail serializer to the shape the component body uses.
// Steps/edges start empty; the process-with-steps useEffect fills them once
// `useRetrieveProcessWithSteps` resolves.
function adaptWorkOrderDetail(w: WorkOrder): MockWorkOrder {
    const proc = (w.process_info ?? {}) as { id?: string; name?: string; part_type_name?: string };
    const order = (w.related_order_info ?? {}) as { company_name?: string; name?: string };
    return {
        id: w.id,
        erp_id: w.ERP_id,
        status: (w.workorder_status ?? "PENDING") as MockWorkOrder["status"],
        priority: (w.priority ?? 3) as 1 | 2 | 3 | 4,
        quantity: w.quantity ?? 0,
        expected_completion: w.expected_completion ?? "",
        process_name: proc.name ?? "—",
        customer: order.company_name ?? order.name ?? "—",
        part_type: proc.part_type_name ?? "—",
        is_batch: w.is_batch_work_order ?? false,
        parent_workorder_id: w.parent_workorder_id ?? null,
        split_reason: null,
        steps: [],
        edges: [],
        parts: [],
    };
}

function adaptProcessSteps(proc: ProcessRecord): { steps: MockStep[]; edges: MockStepEdge[] } {
    const steps: MockStep[] = (proc.process_steps ?? [])
        .slice()
        .sort((a: ProcessStep, b: ProcessStep) => a.order - b.order)
        .map((ps: ProcessStep) => ({
            id: ps.step.id,
            order: ps.order,
            name: ps.step.name,
            requires_qa: ps.step.requires_qa_signoff ?? false,
            node_type: (ps.step.step_type ?? "TASK") as MockStepType,
        }));
    const edges: MockStepEdge[] = (proc.step_edges ?? []).map((e: StepEdge) => ({
        from_step: e.from_step,
        to_step: e.to_step,
        edge_type: (e.edge_type ?? "default") as MockStepEdge["edge_type"],
    }));
    return { steps, edges };
}

function adaptPart(p: PartRow): MockPart {
    return {
        id: p.id,
        serial: p.ERP_id,
        step_id: p.step,
        status: (p.part_status ?? "PENDING") as MockPartStatus,
        updated_at: p.updated_at,
        operator: null, // Parts list serializer doesn't expose the current operator directly
        rework_count: p.total_rework_count,
        requires_sampling: p.requires_sampling,
        traveler: [], // fetched lazily via usePartTraveler on row expand
    };
}

function adaptTravelerEntry(t: TravelerStepEntry): MockStepVisit {
    const op = (t.operator as { name?: string } | null)?.name ?? null;
    const eq = (t.equipment_used?.[0] as { name?: string } | undefined)?.name ?? null;
    const qs = t.quality_status;
    return {
        step_order: t.step_order,
        step_name: t.step_name,
        visit_number: t.visit_number ?? 1,
        started_at: t.started_at ?? "",
        ended_at: t.completed_at ?? null,
        operator: op,
        equipment: eq,
        quality_status: qs === "PASS" ? "PASS" : qs === "FAIL" ? "FAIL" : null,
    };
}

function StepHistoryPanelLive({ partId }: { partId: string }) {
    const { data, isLoading, error } = usePartTraveler(partId);
    if (isLoading) {
        return <div className="rounded-md border bg-muted/30 p-3 text-xs text-muted-foreground">Loading traveler…</div>;
    }
    if (error) {
        return (
            <div className="rounded-md border border-destructive bg-destructive/10 p-3 text-xs text-destructive">
                Traveler unavailable: {error.message}
            </div>
        );
    }
    const visits = (data?.traveler ?? []).map(adaptTravelerEntry);
    const part: MockPart = {
        id: partId,
        serial: data?.part_erp_id ?? partId,
        step_id: data?.current_step_id ?? "",
        status: "PENDING",
        updated_at: "",
        operator: null,
        rework_count: 0,
        requires_sampling: false,
        traveler: visits,
    };
    return <StepHistoryPanel part={part} />;
}

const STATUS_OPTIONS: MockPartStatus[] = [
    "PENDING",
    "IN_PROGRESS",
    "AWAITING_QA",
    "READY_FOR_NEXT_STEP",
    "COMPLETED",
    "QUARANTINED",
    "REWORK_NEEDED",
    "REWORK_IN_PROGRESS",
    "SCRAPPED",
];

function prettyStatus(s: string) {
    return s.replace(/_/g, " ").toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());
}

function hoursSince(iso: string) {
    return Math.round((Date.now() - new Date(iso).getTime()) / 3600_000);
}

// Status colors for the per-step distribution bar. Theme-token fills only —
// primary (positive work), destructive (problems), muted/secondary (idle).
// Ordered so "good" states stack left, "exception" states stack right.
const STEP_BAR_BUCKETS: { key: MockPartStatus[]; className: string; label: string }[] = [
    { key: ["COMPLETED", "READY_FOR_NEXT_STEP"], className: STATUS_BAR_FILL.COMPLETED, label: "Complete / ready" },
    { key: ["IN_PROGRESS"], className: STATUS_BAR_FILL.IN_PROGRESS, label: "In progress" },
    { key: ["AWAITING_QA"], className: STATUS_BAR_FILL.AWAITING_QA, label: "Awaiting QA" },
    { key: ["PENDING"], className: STATUS_BAR_FILL.PENDING, label: "Pending" },
    { key: ["REWORK_NEEDED", "REWORK_IN_PROGRESS"], className: STATUS_BAR_FILL.REWORK_NEEDED, label: "Rework" },
    { key: ["QUARANTINED"], className: STATUS_BAR_FILL.QUARANTINED, label: "Quarantined" },
    { key: ["SCRAPPED"], className: STATUS_BAR_FILL.SCRAPPED, label: "Scrapped" },
];

function StepDistributionBar({ parts }: { parts: MockPart[] }) {
    if (parts.length === 0) {
        return <div className="h-1.5 w-full rounded-full bg-muted" />;
    }
    const total = parts.length;
    return (
        <div className="flex h-1.5 w-full overflow-hidden rounded-full bg-muted">
            {STEP_BAR_BUCKETS.map((b) => {
                const n = parts.filter((p) => b.key.includes(p.status)).length;
                if (n === 0) return null;
                return (
                    <div
                        key={b.label}
                        className={cn("h-full", b.className)}
                        style={{ width: `${(n / total) * 100}%` }}
                        title={`${b.label}: ${n}`}
                    />
                );
            })}
        </div>
    );
}

function NodeTypeBadge({ type }: { type: MockStepType }) {
    if (type === "TASK" || type === "START") return null;
    // Single outline variant — the label carries the meaning. Destructive
    // variant for ESCALATION so "something went wrong" reads at a glance.
    const variant = type === "ESCALATION" ? "destructive" : "outline";
    return (
        <Badge variant={variant} className="px-1.5 py-0 text-[10px]">
            {type.charAt(0) + type.slice(1).toLowerCase()}
        </Badge>
    );
}

function formatAge(hours: number) {
    if (hours < 1) return "<1h";
    if (hours < 48) return `${Math.round(hours)}h`;
    return `${Math.round(hours / 24)}d`;
}

type StepRow = {
    step: MockStep;
    parts: MockPart[];
    readyCount: number;
    qaCount: number;
    oldestHours: number | null;
    nextSteps: MockStep[];
    hasIncomingRework: boolean;
};

type StepSort = "order" | "count" | "oldest" | "ready";

type StepLayout = "compact" | "strip";

function StepStatusList({
    steps,
    edges,
    parts,
    activeStepFilter,
    onFilterStep,
    onAdvanceReady,
    onShowFlow,
}: {
    steps: MockStep[];
    edges: MockStepEdge[];
    parts: MockPart[];
    activeStepFilter: string | null;
    onFilterStep: (stepId: string | null) => void;
    onAdvanceReady: (stepId: string) => void;
    onShowFlow: () => void;
}) {
    const [sort, setSort] = useState<StepSort>("order");
    const [showEmpty, setShowEmpty] = useState(false);
    const [layout, setLayout] = useState<StepLayout>("strip");

    const rows = useMemo<StepRow[]>(() => {
        const stepById = new Map(steps.map((s) => [s.id, s]));
        return steps.map((step) => {
            const stepParts = parts.filter((p) => p.step_id === step.id);
            const readyCount = stepParts.filter(
                (p) => p.status === "READY_FOR_NEXT_STEP" || p.status === "COMPLETED",
            ).length;
            const qaCount = stepParts.filter((p) => p.status === "AWAITING_QA").length;
            const oldestHours = stepParts.length
                ? Math.max(...stepParts.map((p) => (Date.now() - new Date(p.updated_at).getTime()) / 3600_000))
                : null;
            const nextSteps = edges
                .filter((e) => e.from_step === step.id)
                .map((e) => stepById.get(e.to_step))
                .filter((s): s is MockStep => !!s);
            const hasIncomingRework = edges.some((e) => e.to_step === step.id && e.edge_type === "rework");
            return { step, parts: stepParts, readyCount, qaCount, oldestHours, nextSteps, hasIncomingRework };
        });
    }, [steps, edges, parts]);

    const sorted = useMemo(() => {
        const visible = showEmpty ? rows : rows.filter((r) => r.parts.length > 0);
        const arr = [...visible];
        switch (sort) {
            case "count":
                arr.sort((a, b) => b.parts.length - a.parts.length);
                break;
            case "oldest":
                arr.sort((a, b) => (b.oldestHours ?? -1) - (a.oldestHours ?? -1));
                break;
            case "ready":
                arr.sort((a, b) => b.readyCount - a.readyCount);
                break;
            default:
                arr.sort((a, b) => a.step.order - b.step.order);
        }
        return arr;
    }, [rows, sort, showEmpty]);

    const totalActive = rows.filter((r) => r.parts.length > 0).length;

    return (
        <Card>
            <CardContent className="p-3">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                    <div className="text-xs">
                        <span className="font-medium">Step status</span>
                        <span className="ml-1.5 text-muted-foreground">
                            {parts.length} parts · {totalActive} active
                        </span>
                    </div>
                    <div className="ml-auto flex items-center gap-1">
                        <Select value={sort} onValueChange={(v) => setSort(v as StepSort)}>
                            <SelectTrigger className="h-7 w-36 text-xs">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="order">Process order</SelectItem>
                                <SelectItem value="count">Most parts first</SelectItem>
                                <SelectItem value="oldest">Oldest first</SelectItem>
                                <SelectItem value="ready">Most ready first</SelectItem>
                            </SelectContent>
                        </Select>
                        <div className="flex h-7 overflow-hidden rounded-md border">
                            <button
                                onClick={() => setLayout("compact")}
                                className={cn(
                                    "px-2 text-xs transition-colors",
                                    layout === "compact" ? "bg-accent" : "hover:bg-accent/50",
                                )}
                                title="One row per step"
                            >
                                Rows
                            </button>
                            <button
                                onClick={() => setLayout("strip")}
                                className={cn(
                                    "px-2 text-xs transition-colors border-l",
                                    layout === "strip" ? "bg-accent" : "hover:bg-accent/50",
                                )}
                                title="Single-row stage tape"
                            >
                                Strip
                            </button>
                        </div>
                        <Button
                            size="sm"
                            variant="ghost"
                            className="h-7 text-xs"
                            onClick={() => setShowEmpty((v) => !v)}
                        >
                            {showEmpty ? "Hide empty" : "Show empty"}
                        </Button>
                        <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={onShowFlow}>
                            <GitBranch className="mr-1 h-3 w-3" />
                            Flow
                        </Button>
                        {activeStepFilter !== null && (
                            <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={() => onFilterStep(null)}>
                                <X className="mr-1 h-3 w-3" />
                                Clear
                            </Button>
                        )}
                    </div>
                </div>

                {layout === "strip" ? (
                    <StepStrip
                        rows={sorted}
                        activeStepFilter={activeStepFilter}
                        onFilterStep={onFilterStep}
                        onAdvanceReady={onAdvanceReady}
                    />
                ) : (
                    <div className="divide-y rounded-md border">
                        {sorted.map((row) => (
                            <StepRow
                                key={row.step.id}
                                row={row}
                                active={activeStepFilter === row.step.id}
                                onFilterStep={onFilterStep}
                                onAdvanceReady={onAdvanceReady}
                            />
                        ))}
                        {sorted.length === 0 && (
                            <div className="py-4 text-center text-xs text-muted-foreground">
                                No active steps. Toggle "Show empty" to see the full process.
                            </div>
                        )}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}

function StepRow({
    row,
    active,
    onFilterStep,
    onAdvanceReady,
}: {
    row: StepRow;
    active: boolean;
    onFilterStep: (stepId: string | null) => void;
    onAdvanceReady: (stepId: string) => void;
}) {
    const { step, parts: stepParts, readyCount, qaCount, oldestHours, nextSteps, hasIncomingRework } = row;
    const isEmpty = stepParts.length === 0;
    const stale = oldestHours !== null && oldestHours > 24;
    return (
        <div
            onClick={() => onFilterStep(active ? null : step.id)}
            className={cn(
                "grid h-9 cursor-pointer grid-cols-[auto_minmax(160px,240px)_1fr_auto_auto] items-center gap-3 px-3 text-sm transition-colors",
                active && "bg-accent",
                !active && "hover:bg-accent/40",
                isEmpty && "opacity-55",
            )}
            title={
                nextSteps.length
                    ? `Next: ${nextSteps.map((n) => `${n.order}. ${n.name}`).join(" or ")}`
                    : undefined
            }
        >
            {/* Order chip */}
            <div
                className={cn(
                    "flex h-6 w-6 items-center justify-center rounded-full text-[11px] font-semibold",
                    active ? "bg-primary text-primary-foreground" : "bg-muted",
                )}
            >
                {step.order}
            </div>

            {/* Name + badges */}
            <div className="flex min-w-0 items-center gap-1.5">
                <span className="truncate font-medium">{step.name}</span>
                {step.requires_qa && (
                    <Badge variant="outline" className="px-1 py-0 text-[9px]">
                        QA
                    </Badge>
                )}
                <NodeTypeBadge type={step.node_type} />
                {hasIncomingRework && (
                    <span className="text-[11px] text-destructive" title="Rework edge feeds into this step">
                        ↺
                    </span>
                )}
                {nextSteps.length > 1 && (
                    <span className="text-[11px] text-muted-foreground" title="Branches downstream">
                        ⑂
                    </span>
                )}
            </div>

            {/* Composition bar fills middle */}
            <div className="min-w-0">
                <StepDistributionBar parts={stepParts} />
            </div>

            {/* Metrics cluster */}
            <div className="flex items-center gap-2 whitespace-nowrap text-xs">
                <span className="tabular-nums font-semibold">{stepParts.length}</span>
                {qaCount > 0 && (
                    <span className="rounded bg-secondary px-1 py-0 text-[10px] font-medium text-secondary-foreground">
                        QA {qaCount}
                    </span>
                )}
                {oldestHours !== null && (
                    <span
                        className={cn(
                            "text-[10px]",
                            stale ? "font-medium text-destructive" : "text-muted-foreground",
                        )}
                    >
                        {formatAge(oldestHours)}
                    </span>
                )}
            </div>

            {/* Ready button or placeholder */}
            <div onClick={(e) => e.stopPropagation()} className="w-[120px] text-right">
                {readyCount > 0 ? (
                    <Button
                        size="sm"
                        variant="ghost"
                        className="h-7 px-2 text-xs"
                        onClick={() => onAdvanceReady(step.id)}
                    >
                        Advance {readyCount}
                        <ChevronRight className="ml-0.5 h-3 w-3" />
                    </Button>
                ) : (
                    <span className="text-[10px] text-muted-foreground">—</span>
                )}
            </div>
        </div>
    );
}

function StepStrip({
    rows,
    activeStepFilter,
    onFilterStep,
    onAdvanceReady,
}: {
    rows: StepRow[];
    activeStepFilter: string | null;
    onFilterStep: (stepId: string | null) => void;
    onAdvanceReady: (stepId: string) => void;
}) {
    return (
        <div className="flex gap-1 overflow-x-auto rounded-md border p-1">
            {rows.map((row) => {
                const active = activeStepFilter === row.step.id;
                const stale = row.oldestHours !== null && row.oldestHours > 24;
                return (
                    <button
                        key={row.step.id}
                        onClick={() => onFilterStep(active ? null : row.step.id)}
                        className={cn(
                            "flex min-w-[140px] flex-1 flex-col gap-1 rounded px-2 py-1.5 text-left transition-colors",
                            active && "bg-accent ring-1 ring-primary",
                            !active && "hover:bg-accent/50",
                            row.parts.length === 0 && "opacity-55",
                        )}
                        title={
                            row.nextSteps.length
                                ? `Next: ${row.nextSteps.map((n) => `${n.order}. ${n.name}`).join(" or ")}`
                                : undefined
                        }
                    >
                        <div className="flex items-center justify-between gap-1">
                            <div className="flex min-w-0 items-center gap-1">
                                <span className="text-[10px] text-muted-foreground">{row.step.order}.</span>
                                <span className="truncate text-xs font-medium">{row.step.name}</span>
                                {row.step.node_type === "DECISION" && (
                                    <span className="text-[10px] text-muted-foreground">◆</span>
                                )}
                                {row.step.node_type === "REWORK" && (
                                    <span className="text-[10px] text-destructive">↺</span>
                                )}
                            </div>
                            <span className="text-sm font-semibold tabular-nums">{row.parts.length}</span>
                        </div>
                        <StepDistributionBar parts={row.parts} />
                        <div className="flex items-center justify-between text-[10px]">
                            <span className={cn(stale ? "font-medium text-destructive" : "text-muted-foreground")}>
                                {row.oldestHours !== null ? formatAge(row.oldestHours) : "—"}
                            </span>
                            {row.readyCount > 0 && (
                                <span
                                    className="cursor-pointer font-medium text-primary"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        onAdvanceReady(row.step.id);
                                    }}
                                >
                                    ▶ {row.readyCount}
                                </span>
                            )}
                        </div>
                    </button>
                );
            })}
        </div>
    );
}

function StepHistoryPanel({ part }: { part: MockPart }) {
    return (
        <div className="space-y-2 rounded-md border bg-muted/30 p-3">
            <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
                <FileText className="h-3 w-3" />
                Traveler · {part.serial}
            </div>
            <Table>
                <TableHeader>
                    <TableRow className="hover:bg-transparent">
                        <TableHead className="h-8 text-xs">Step</TableHead>
                        <TableHead className="h-8 text-xs">Visit</TableHead>
                        <TableHead className="h-8 text-xs">Operator</TableHead>
                        <TableHead className="h-8 text-xs">Equipment</TableHead>
                        <TableHead className="h-8 text-xs">Started</TableHead>
                        <TableHead className="h-8 text-xs">Ended</TableHead>
                        <TableHead className="h-8 text-xs">QA</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {part.traveler.map((v, i) => (
                        <TableRow key={i} className="hover:bg-transparent">
                            <TableCell className="py-1.5 text-xs">
                                {v.step_order}. {v.step_name}
                            </TableCell>
                            <TableCell className="py-1.5 text-xs">#{v.visit_number}</TableCell>
                            <TableCell className="py-1.5 text-xs">{v.operator ?? "—"}</TableCell>
                            <TableCell className="py-1.5 text-xs">{v.equipment ?? "—"}</TableCell>
                            <TableCell className="py-1.5 text-xs">
                                {new Date(v.started_at).toLocaleString()}
                            </TableCell>
                            <TableCell className="py-1.5 text-xs">
                                {v.ended_at ? new Date(v.ended_at).toLocaleString() : "—"}
                            </TableCell>
                            <TableCell className="py-1.5 text-xs">
                                {v.quality_status ? (
                                    <PartStatusBadge status={v.quality_status} size="sm" showIcon={false} />
                                ) : (
                                    <span className="text-muted-foreground">—</span>
                                )}
                            </TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </div>
    );
}

type Action =
    | { kind: "advance" }
    | { kind: "rewind" }
    | { kind: "move"; stepId: string }
    | { kind: "status"; status: MockPartStatus }
    | { kind: "scrap"; reason: string };

function applyAction(part: MockPart, steps: MockStep[], action: Action): MockPart {
    const stepIdx = steps.findIndex((s) => s.id === part.step_id);
    if (action.kind === "advance") {
        const next = Math.min(steps.length - 1, stepIdx + 1);
        return {
            ...part,
            step_id: steps[next].id,
            status: next === steps.length - 1 ? "COMPLETED" : "IN_PROGRESS",
            updated_at: new Date().toISOString(),
        };
    }
    if (action.kind === "rewind") {
        const prev = Math.max(0, stepIdx - 1);
        return { ...part, step_id: steps[prev].id, status: "IN_PROGRESS", updated_at: new Date().toISOString() };
    }
    if (action.kind === "move") {
        return { ...part, step_id: action.stepId, status: "IN_PROGRESS", updated_at: new Date().toISOString() };
    }
    if (action.kind === "status") {
        return { ...part, status: action.status, updated_at: new Date().toISOString() };
    }
    if (action.kind === "scrap") {
        return { ...part, status: "SCRAPPED", updated_at: new Date().toISOString() };
    }
    return part;
}

export function WorkOrderControlPage() {
    const navigate = useNavigate();
    const params = useParams({ strict: false }) as { workOrderId?: string };
    const workOrderId = params.workOrderId ?? "";

    const { data: realWo, error: realWoError } = useRetrieveWorkOrder(workOrderId, {
        enabled: !!workOrderId,
    });
    const { data: realPartsData } = useRetrieveParts(
        { work_order: workOrderId, limit: 500 },
        undefined,
        { enabled: !!workOrderId },
    );
    const processId = realWo?.process ?? null;
    const { data: realProcess } = useRetrieveProcessWithSteps(
        { params: { id: processId ?? "" } },
        { enabled: !!processId },
    );

    const [wo, setWo] = useState<MockWorkOrder | null>(null);
    const [parts, setParts] = useState<MockPart[]>([]);

    useEffect(() => {
        if (realWo) {
            setWo((prev) => ({
                ...adaptWorkOrderDetail(realWo),
                steps: prev?.steps ?? adaptWorkOrderDetail(realWo).steps,
                edges: prev?.edges ?? adaptWorkOrderDetail(realWo).edges,
            }));
            const h = realWo.current_hold as {
                reason?: string;
                placed_at?: string;
                placed_by_name?: string | null;
                notes?: string | null;
                hours_open?: number;
                expected_clear_at?: string | null;
            } | null | undefined;
            setCurrentHold(
                h && h.reason && h.placed_at
                    ? {
                          reason: h.reason,
                          placed_at: h.placed_at,
                          placed_by_name: h.placed_by_name ?? null,
                          notes: h.notes ?? null,
                          hours_open: h.hours_open ?? 0,
                          expected_clear_at: h.expected_clear_at ?? null,
                      }
                    : null,
            );
        }
    }, [realWo]);
    useEffect(() => {
        if (realPartsData?.results) {
            setParts(realPartsData.results.map(adaptPart));
        }
    }, [realPartsData]);
    useEffect(() => {
        if (realProcess) {
            const { steps, edges } = adaptProcessSteps(realProcess);
            if (steps.length > 0) {
                setWo((prev) => ({ ...prev, steps, edges }));
            }
        }
    }, [realProcess]);
    const [selected, setSelected] = useState<Set<string>>(new Set());
    const [expanded, setExpanded] = useState<Set<string>>(new Set());
    const [stepFilter, setStepFilter] = useState<string | null>(null);
    const [statusFilter, setStatusFilter] = useState<string>("all");
    const [search, setSearch] = useState("");

    const [moveDialogOpen, setMoveDialogOpen] = useState(false);
    const [moveTarget, setMoveTarget] = useState<string | null>(null);
    const [statusDialogOpen, setStatusDialogOpen] = useState(false);
    const [statusTarget, setStatusTarget] = useState<MockPartStatus>("IN_PROGRESS");
    const [scrapDialogOpen, setScrapDialogOpen] = useState(false);
    const [scrapReason, setScrapReason] = useState("");

    const [holdDialogOpen, setHoldDialogOpen] = useState(false);
    const [holdReason, setHoldReason] = useState<HoldReason>("MATERIAL");
    const [holdNotes, setHoldNotes] = useState("");
    const [bulkErrorBanner, setBulkErrorBanner] = useState<string | null>(null);
    const [currentHold, setCurrentHold] = useState<{
        reason: string;
        placed_at: string;
        placed_by_name: string | null;
        notes: string | null;
        hours_open: number;
        expected_clear_at: string | null;
    } | null>(null);
    const [flowDrawerOpen, setFlowDrawerOpen] = useState(false);
    const [splitMode, setSplitMode] = useState<SplitMode | null>(null);
    const [splitQuantity, setSplitQuantity] = useState<number>(1);
    const [splitNewErpId, setSplitNewErpId] = useState<string>("");
    const [splitReworkProcessId, setSplitReworkProcessId] = useState<string>("");
    const [splitNotes, setSplitNotes] = useState<string>("");
    const [splitBanner, setSplitBanner] = useState<string | null>(null);

    function enterSplitMode(mode: SplitMode) {
        setSplitMode(mode);
        setSplitNewErpId(`${wo?.erp_id ?? workOrderId}-${mode === "REWORK" ? "R1" : "A"}`);
        setSplitQuantity(Math.min(1, parts.length - 1));
        setSplitReworkProcessId("");
        setSplitNotes("");
    }
    function exitSplitMode() {
        setSplitMode(null);
    }

    // Parent WO — only fetched when this WO is a child (has parent_workorder_id).
    const parentWoId = wo?.parent_workorder_id ?? null;
    const { data: parentWoData } = useRetrieveWorkOrder(parentWoId ?? "", {
        enabled: !!parentWoId,
    });
    const parentErpId = parentWoData?.ERP_id ?? null;

    // childCount requires either a `parent_workorder` filter on the list
    // endpoint or a `child_count`/`child_ids` field on the detail serializer.
    // Chip is hidden until one ships.
    const childCount = 0;

    const splitMutation = useSplitWorkOrder();
    const undoSplitMutation = useUndoSplitWorkOrder();

    function handleSplit() {
        if (!splitMode) return;
        // Optimistic: remove the parts that are moving to the child WO so the
        // parent list updates immediately. Reverted in onError.
        const moveIds =
            splitMode === "QUANTITY"
                ? parts.slice(0, splitQuantity).map((p) => p.id)
                : Array.from(selected);
        const restoredParts = parts;
        setParts((prev) => prev.filter((p) => !moveIds.includes(p.id)));
        setSelected(new Set());
        const body = {
            id: workOrderId,
            reason: splitMode,
            new_erp_id: splitNewErpId,
            notes: splitNotes || undefined,
            ...(splitMode === "QUANTITY"
                ? { quantity: splitQuantity }
                : { part_ids: moveIds }),
            ...(splitMode === "REWORK" && splitReworkProcessId
                ? { target_process_id: splitReworkProcessId }
                : {}),
        };
        splitMutation.mutate(body, {
            onSuccess: (data) => {
                const childErpId = (data as { child_erp_id?: string }).child_erp_id ?? splitNewErpId;
                setSplitBanner(`Child WO ${childErpId} created · parts moved`);
                setSplitMode(null);
            },
            onError: (err: unknown) => {
                setParts(restoredParts);
                const msg = err instanceof Error ? err.message : String(err);
                setSplitBanner(`Split failed: ${msg}`);
            },
        });
    }

    function handleUndoSplit() {
        undoSplitMutation.mutate(
            { id: workOrderId },
            {
                onSuccess: () => {
                    if (parentWoId) {
                        void navigate({ to: `/workorder/${parentWoId}/control` });
                    }
                },
                onError: (err: unknown) => {
                    const msg = err instanceof Error ? err.message : String(err);
                    setSplitBanner(`Undo split failed: ${msg}`);
                },
            },
        );
    }

    function advanceReadyAtStep(stepId: string) {
        const ids = parts
            .filter(
                (p) =>
                    p.step_id === stepId &&
                    (p.status === "READY_FOR_NEXT_STEP" || p.status === "COMPLETED"),
            )
            .map((p) => p.id);
        if (ids.length > 0) applyToIds(ids, { kind: "advance" });
    }

    const priorityCfg = wo ? WO_PRIORITY_LABELS[wo.priority] : WO_PRIORITY_LABELS[3];
    const isOverdue = wo
        ? new Date(wo.expected_completion) < new Date() && wo.status !== "COMPLETED" && wo.status !== "CANCELLED"
        : false;

    const filtered = useMemo(() => {
        return parts.filter((p) => {
            if (stepFilter && p.step_id !== stepFilter) return false;
            if (statusFilter !== "all" && p.status !== statusFilter) return false;
            if (search && !p.serial.toLowerCase().includes(search.toLowerCase())) return false;
            return true;
        });
    }, [parts, stepFilter, statusFilter, search]);

    const allVisibleSelected = filtered.length > 0 && filtered.every((p) => selected.has(p.id));
    const someVisibleSelected = filtered.some((p) => selected.has(p.id));

    function toggleAllVisible() {
        setSelected((prev) => {
            const next = new Set(prev);
            if (allVisibleSelected) filtered.forEach((p) => next.delete(p.id));
            else filtered.forEach((p) => next.add(p.id));
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
    function toggleExpanded(id: string) {
        setExpanded((prev) => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
        });
    }
    const queryClient = useQueryClient();
    const updatePart = useUpdatePart();
    const bulkIncrementMutation = useBulkIncrementParts();
    const bulkRollbackMutation = useBulkRollbackParts();
    const bulkSetStatusMutation = useBulkSetStatusParts();

    function applyToIds(ids: string[], action: Action) {
        setParts((prev) => prev.map((p) => (ids.includes(p.id) ? applyAction(p, wo?.steps ?? [], action) : p)));
        if (action.kind === "advance") {
            bulkIncrementMutation.mutate(ids, {
                onSuccess: (data) => {
                    const failures = (data.results as { ok?: boolean; error?: string; id?: string }[]).filter((r) => !r.ok);
                    if (failures.length > 0) setBulkErrorBanner(`${failures.length} part(s) failed to advance.`);
                },
            });
        } else if (action.kind === "rewind") {
            bulkRollbackMutation.mutate(ids, {
                onSuccess: (data) => {
                    const failures = (data.results as { ok?: boolean; error?: string; id?: string }[]).filter((r) => !r.ok);
                    if (failures.length > 0) setBulkErrorBanner(`${failures.length} part(s) failed to roll back.`);
                },
            });
        } else if (action.kind === "status") {
            bulkSetStatusMutation.mutate({ ids, status: action.status }, {
                onSuccess: (data) => {
                    const failures = (data.results as { ok?: boolean; error?: string; id?: string }[]).filter((r) => !r.ok);
                    if (failures.length > 0) setBulkErrorBanner(`${failures.length} part(s) failed to update status.`);
                },
            });
        } else if (action.kind === "scrap") {
            bulkSetStatusMutation.mutate({ ids, status: "SCRAPPED", reason: action.reason }, {
                onSuccess: (data) => {
                    const failures = (data.results as { ok?: boolean; error?: string; id?: string }[]).filter((r) => !r.ok);
                    if (failures.length > 0) setBulkErrorBanner(`${failures.length} part(s) failed to update status.`);
                },
            });
        } else if (action.kind === "move") {
            void Promise.all(
                ids.map((id) => updatePart.mutateAsync({ id, data: { step: action.stepId } })),
            ).then(() => {
                queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "parts" });
            });
        }
    }
    function applyToSelected(action: Action) {
        applyToIds(Array.from(selected), action);
    }

    const placeOnHoldMutation = usePlaceOnHoldWorkOrder();
    const clearHoldMutation = useClearHoldWorkOrder();

    function placeOnHold() {
        placeOnHoldMutation.mutate(
            { id: workOrderId, reason: holdReason, notes: holdNotes || undefined },
            {
                onSuccess: () => {
                    setHoldDialogOpen(false);
                    setHoldNotes("");
                },
            },
        );
    }
    function clearHold() {
        clearHoldMutation.mutate({ id: workOrderId });
    }

    const stepById = useMemo(() => {
        const m = new Map<string, MockStep>();
        wo?.steps.forEach((s) => m.set(s.id, s));
        return m;
    }, [wo?.steps]);

    const completedCount = parts.filter((p) => p.status === "COMPLETED").length;
    const progressPct = parts.length > 0 ? Math.round((completedCount / parts.length) * 100) : 0;

    const { data: exceptionsData, resolveException: resolveExceptionMutation } = useExceptions();
    const [resolvedExceptionIds, setResolvedExceptionIds] = useState<Set<string>>(new Set());
    const [draftWoExceptions, setDraftWoExceptions] = useState<ExceptionItem[]>([]);
    const [reportOpen, setReportOpen] = useState(false);

    const woExceptions: ExceptionItem[] = useMemo(() => {
        const merged = [...draftWoExceptions, ...exceptionsData];
        return merged.filter((e) => {
            if (resolvedExceptionIds.has(e.id)) return false;
            if (e.closed_at) return false;
            return wo ? e.work_order_ids.includes(wo.id) : false;
        });
    }, [exceptionsData, draftWoExceptions, resolvedExceptionIds, wo]);

    function resolveException(id: string) {
        const e = [...draftWoExceptions, ...exceptionsData].find((x) => x.id === id);
        setResolvedExceptionIds((prev) => {
            const next = new Set(prev);
            next.add(id);
            return next;
        });
        if (e) resolveExceptionMutation(e.id, e.kind);
    }

    function reportWoException(payload: ReportExceptionPayload) {
        const id = `exc-${Date.now()}`;
        setDraftWoExceptions((prev) => [
            {
                ...payload,
                id,
                state: "OPEN",
                opened_at: new Date().toISOString(),
                closed_at: null,
                work_order_ids: wo ? [wo.id] : [],
                source_ref: `${payload.kind === "DOWNTIME" ? "DowntimeEvent" : payload.kind === "QUARANTINE" ? "QuarantineDisposition" : "CAPA"}/${id}`,
            },
            ...prev,
        ]);
    }

    if (realWoError && !realWo) {
        return (
            <div className="space-y-4 p-6">
                <Button variant="ghost" onClick={() => navigate({ to: "/workorders" })}>
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    Back
                </Button>
                <Alert variant="destructive">
                    <AlertTitle>Work order not found</AlertTitle>
                    <AlertDescription>
                        No work order with id <span className="font-mono">{workOrderId}</span> exists.
                    </AlertDescription>
                </Alert>
            </div>
        );
    }

    if (!wo) {
        return (
            <div className="space-y-4 p-6">
                <Card>
                    <CardContent className="space-y-3 p-4">
                        <Skeleton className="h-8 w-48" />
                        <Skeleton className="h-4 w-72" />
                        <Skeleton className="h-4 w-56" />
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="space-y-4 p-6 pb-24">
            {/* Header mirrors WorkOrderDetailPage layout */}
            <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
                <div className="flex items-center gap-4">
                    <Button variant="ghost" onClick={() => navigate({ to: "/workorders" })}>
                        <ArrowLeft className="mr-2 h-4 w-4" />
                        Back
                    </Button>
                    <div className="flex flex-wrap items-center gap-3">
                        <h1 className="text-2xl font-semibold">{wo.erp_id}</h1>
                        <WoStatusBadge status={wo.status} />
                        <Badge className={cn("text-xs", priorityCfg.className)}>{priorityCfg.label}</Badge>
                        {wo.is_batch && (
                            <Badge variant="outline" className="text-xs">
                                Batch
                            </Badge>
                        )}
                        {isOverdue && (
                            <Badge variant="destructive" className="flex items-center gap-1 text-xs">
                                <AlertTriangle className="h-3 w-3" />
                                Overdue
                            </Badge>
                        )}
                        {parentWoId && (
                            <Badge
                                variant="outline"
                                className="flex cursor-pointer items-center gap-1 text-xs"
                                onClick={() => navigate({ to: `/workorder/${parentWoId}/control` })}
                                title={`Split from ${parentErpId ?? parentWoId}`}
                            >
                                <GitBranch className="h-3 w-3" />
                                Split from {parentErpId ?? parentWoId}
                            </Badge>
                        )}
                        {childCount > 0 && (
                            <Badge variant="secondary" className="flex items-center gap-1 text-xs">
                                <Split className="h-3 w-3" />
                                {childCount} split{childCount === 1 ? "" : "s"}
                            </Badge>
                        )}
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <Button
                        variant={splitMode ? "default" : "outline"}
                        onClick={() => (splitMode ? exitSplitMode() : enterSplitMode("QUANTITY"))}
                    >
                        <Split className="mr-1 h-4 w-4" />
                        {splitMode ? "Exit split mode" : "Split…"}
                    </Button>
                    {parentWoId && (
                        <UndoSplitButton
                            onUndo={handleUndoSplit}
                            isPending={undoSplitMutation.isPending}
                        />
                    )}
                    {currentHold != null ? (
                        <Button variant="outline" onClick={clearHold}>
                            Clear hold
                        </Button>
                    ) : (
                        <Button variant="outline" onClick={() => setHoldDialogOpen(true)}>
                            <PauseCircle className="mr-1 h-4 w-4" />
                            Place on hold
                        </Button>
                    )}
                </div>
            </div>

            {splitBanner && (
                <div className="flex items-center gap-2 rounded-md border bg-accent/40 px-3 py-2 text-sm">
                    <Split className="h-4 w-4 text-muted-foreground" />
                    <span className="flex-1">{splitBanner}</span>
                    <Button size="sm" variant="ghost" onClick={() => setSplitBanner(null)}>
                        <X className="h-4 w-4" />
                    </Button>
                </div>
            )}

            {bulkErrorBanner && (
                <div className="flex items-center gap-2 rounded-md border border-destructive bg-destructive/10 px-3 py-2 text-sm text-destructive">
                    <AlertTriangle className="h-4 w-4 shrink-0" />
                    <span className="flex-1">{bulkErrorBanner}</span>
                    <Button size="sm" variant="ghost" onClick={() => setBulkErrorBanner(null)}>
                        <X className="h-4 w-4" />
                    </Button>
                </div>
            )}

            {currentHold && (
                <Card className="border-amber-500/50">
                    <CardContent className="flex items-start gap-3 p-3">
                        <PauseCircle className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
                        <div className="flex-1 space-y-0.5 text-sm">
                            <div className="font-medium">
                                On hold · {HOLD_REASONS.find((r) => r.value === currentHold.reason)?.label ?? currentHold.reason}
                            </div>
                            <div className="text-xs text-muted-foreground">
                                {currentHold.hours_open}h open
                                {currentHold.placed_by_name ? ` · placed by ${currentHold.placed_by_name}` : ""}
                                {currentHold.expected_clear_at
                                    ? ` · expected clear ${new Date(currentHold.expected_clear_at).toLocaleDateString()}`
                                    : ""}
                            </div>
                            {currentHold.notes && (
                                <div className="text-xs text-muted-foreground">{currentHold.notes}</div>
                            )}
                        </div>
                    </CardContent>
                </Card>
            )}

            {splitMode && (
                <Card className="border-primary">
                    <CardContent className="space-y-3 p-4">
                        <div className="flex items-center gap-2">
                            <Split className="h-4 w-4 text-primary" />
                            <span className="text-sm font-medium">Split mode</span>
                            <span className="text-xs text-muted-foreground">
                                {splitMode === "QUANTITY"
                                    ? "Move N parts to a new WO"
                                    : splitMode === "OPERATION"
                                      ? "Pick parts in the table below; selection updates here"
                                      : "Pick parts in the table below; choose a rework process"}
                            </span>
                            <div className="ml-auto flex gap-1 rounded-md border p-0.5">
                                {(["QUANTITY", "OPERATION", "REWORK"] as const).map((m) => (
                                    <button
                                        key={m}
                                        onClick={() => setSplitMode(m)}
                                        className={cn(
                                            "rounded px-2 py-0.5 text-xs transition-colors",
                                            splitMode === m
                                                ? "bg-primary text-primary-foreground"
                                                : "hover:bg-accent",
                                        )}
                                    >
                                        {m === "QUANTITY" ? "Quantity" : m === "OPERATION" ? "Selected parts" : "Rework"}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div className="grid gap-3 sm:grid-cols-2">
                            {splitMode === "QUANTITY" ? (
                                <div className="space-y-1">
                                    <label className="text-xs text-muted-foreground">Quantity in new WO</label>
                                    <Input
                                        type="number"
                                        min={1}
                                        max={Math.max(1, parts.length - 1)}
                                        value={splitQuantity}
                                        onChange={(e) => setSplitQuantity(Number(e.target.value))}
                                    />
                                    <p className="text-xs text-muted-foreground">
                                        Parent keeps {Math.max(0, parts.length - splitQuantity)} of {parts.length}.
                                    </p>
                                </div>
                            ) : (
                                <div className="space-y-1">
                                    <label className="text-xs text-muted-foreground">Selected parts</label>
                                    <div className="flex h-9 items-center rounded-md border bg-muted/30 px-3 text-sm">
                                        <span className="tabular-nums font-semibold">{selected.size}</span>
                                        <span className="ml-1 text-muted-foreground">
                                            of {parts.length} selected
                                        </span>
                                        {selected.size === 0 && (
                                            <span className="ml-auto text-xs text-destructive">
                                                select in parts table ↓
                                            </span>
                                        )}
                                    </div>
                                </div>
                            )}

                            {splitMode === "REWORK" && (
                                <div className="space-y-1">
                                    <label className="text-xs text-muted-foreground">Rework process</label>
                                    <Select value={splitReworkProcessId} onValueChange={setSplitReworkProcessId}>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Select rework process…" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {MOCK_REWORK_PROCESSES.map((p) => (
                                                <SelectItem key={p.id} value={p.id}>
                                                    {p.name}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                            )}

                            <div className="space-y-1">
                                <label className="text-xs text-muted-foreground">New ERP id</label>
                                <Input
                                    value={splitNewErpId}
                                    onChange={(e) => setSplitNewErpId(e.target.value)}
                                    className="font-mono"
                                />
                            </div>

                            <div className="space-y-1 sm:col-span-2">
                                <label className="text-xs text-muted-foreground">Notes</label>
                                <Textarea
                                    value={splitNotes}
                                    onChange={(e) => setSplitNotes(e.target.value)}
                                    placeholder="Why is this being split?"
                                    className="min-h-[60px]"
                                />
                            </div>
                        </div>

                        <div className="flex items-center justify-end gap-2 border-t pt-3">
                            <Button variant="ghost" onClick={exitSplitMode}>
                                Cancel
                            </Button>
                            <Button
                                onClick={handleSplit}
                                disabled={
                                    splitMutation.isPending ||
                                    !splitNewErpId.trim() ||
                                    (splitMode === "QUANTITY"
                                        ? splitQuantity < 1 || splitQuantity >= parts.length
                                        : selected.size === 0) ||
                                    (splitMode === "REWORK" && !splitReworkProcessId)
                                }
                            >
                                {splitMutation.isPending ? "Creating…" : "Create child WO"}
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            )}

            <p className="text-sm text-muted-foreground">
                {wo.process_name} · {wo.customer} · {wo.part_type} · Due {wo.expected_completion}
            </p>

            {/* Summary strip */}
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                <Card>
                    <CardContent className="p-3">
                        <div className="text-xs text-muted-foreground">Progress</div>
                        <div className="text-xl font-semibold">{progressPct}%</div>
                        <div className="text-xs text-muted-foreground">
                            {completedCount}/{parts.length} complete
                        </div>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="p-3">
                        <div className="text-xs text-muted-foreground">In quarantine</div>
                        <div className="text-xl font-semibold">{parts.filter((p) => p.status === "QUARANTINED").length}</div>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="p-3">
                        <div className="text-xs text-muted-foreground">Rework</div>
                        <div className="text-xl font-semibold">
                            {parts.filter((p) => p.status === "REWORK_NEEDED" || p.status === "REWORK_IN_PROGRESS").length}
                        </div>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="p-3">
                        <div className="text-xs text-muted-foreground">Scrap</div>
                        <div className="text-xl font-semibold">{parts.filter((p) => p.status === "SCRAPPED").length}</div>
                    </CardContent>
                </Card>
            </div>

            <Card>
                <CardContent className="space-y-2 p-3">
                    <div className="flex items-center gap-2 text-sm">
                        <CircleAlert
                            className={cn("h-4 w-4", woExceptions.length > 0 ? "text-destructive" : "text-muted-foreground")}
                        />
                        <span className="font-medium">Exceptions on this WO</span>
                        {woExceptions.length > 0 ? (
                            <Badge variant="destructive" className="text-[10px]">
                                {woExceptions.length} open
                            </Badge>
                        ) : (
                            <Badge variant="outline" className="text-[10px]">
                                None open
                            </Badge>
                        )}
                        <span className="ml-auto text-[11px] text-muted-foreground">
                            Unified · Downtime + Quarantine + CAPA
                        </span>
                        <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => setReportOpen(true)}>
                            <CircleAlert className="mr-1 h-3 w-3" />
                            Report…
                        </Button>
                    </div>
                    {woExceptions.length > 0 && (
                        <div className="divide-y rounded-md border">
                            {woExceptions.map((e) => {
                                const KindIcon =
                                    e.kind === "DOWNTIME" ? Wrench : e.kind === "QUARANTINE" ? ShieldAlert : CircleAlert;
                                return (
                                    <div key={e.id} className="flex items-center gap-3 p-2 text-sm">
                                        <KindIcon className="h-4 w-4 text-muted-foreground" />
                                        <div className="min-w-0 flex-1">
                                            <div className="flex items-center gap-2">
                                                <Badge variant="outline" className="text-[10px]">
                                                    {e.kind}
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
                                                <span className="truncate font-medium">{e.title}</span>
                                            </div>
                                            <div className="truncate text-xs text-muted-foreground">{e.description}</div>
                                        </div>
                                        <span className="whitespace-nowrap text-[11px] text-muted-foreground">
                                            {hoursSince(e.opened_at)}h · {e.reported_by}
                                        </span>
                                        {e.kind === "DOWNTIME" && (
                                            <Button
                                                size="sm"
                                                variant="outline"
                                                className="h-7 text-xs"
                                                onClick={() => resolveException(e.id)}
                                            >
                                                <Wrench className="mr-1 h-3 w-3" />
                                                Resolve
                                            </Button>
                                        )}
                                        {e.kind === "QUARANTINE" && (
                                            <Button
                                                size="sm"
                                                variant="outline"
                                                className="h-7 text-xs"
                                                onClick={() => navigate({ to: `/dispositions/edit/${e.id}` })}
                                            >
                                                Open disposition
                                            </Button>
                                        )}
                                        {e.kind === "CAPA" && (
                                            <Button
                                                size="sm"
                                                variant="outline"
                                                className="h-7 text-xs"
                                                onClick={() => navigate({ to: `/quality/capas/${e.id}` })}
                                            >
                                                Open CAPA
                                            </Button>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </CardContent>
            </Card>

            <StepStatusList
                steps={wo.steps}
                edges={wo.edges}
                parts={parts}
                activeStepFilter={stepFilter}
                onFilterStep={setStepFilter}
                onAdvanceReady={advanceReadyAtStep}
                onShowFlow={() => setFlowDrawerOpen(true)}
            />

            <Sheet open={flowDrawerOpen} onOpenChange={setFlowDrawerOpen}>
                <SheetContent side="right" className="w-[min(900px,90vw)] sm:max-w-none">
                    <SheetHeader>
                        <SheetTitle>Process flow · {wo.process_name}</SheetTitle>
                        <SheetDescription>
                            Full DAG with decision, rework, and escalation edges. Read-only view.
                        </SheetDescription>
                    </SheetHeader>
                    <div className="mt-4 h-[calc(100vh-140px)] overflow-hidden rounded-md border">
                        <ReactFlowProvider>
                            <FlowCanvas
                                steps={wo.steps.map<FlowStepData>((s) => ({
                                    id: s.id,
                                    name: s.name,
                                    order: s.order,
                                    step_type: s.node_type,
                                    requires_qa_signoff: s.requires_qa,
                                    is_decision_point: s.node_type === "DECISION",
                                }))}
                                stepEdges={wo.edges.map((e) => ({
                                    from_step: e.from_step,
                                    to_step: e.to_step,
                                    edge_type: e.edge_type,
                                }))}
                                editable={false}
                            />
                        </ReactFlowProvider>
                    </div>
                </SheetContent>
            </Sheet>

            <Card>
                <CardContent className="space-y-3 p-4">
                    <div className="flex flex-wrap items-center gap-2">
                        <div className="relative">
                            <Search className="absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                            <Input
                                placeholder="Search serial…"
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                className="w-60 pl-8"
                            />
                        </div>
                        <Select value={statusFilter} onValueChange={setStatusFilter}>
                            <SelectTrigger className="w-48">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">All statuses</SelectItem>
                                {STATUS_OPTIONS.map((s) => (
                                    <SelectItem key={s} value={s}>
                                        {prettyStatus(s)}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        <div className="ml-auto text-sm text-muted-foreground">
                            Showing {filtered.length} of {parts.length}
                        </div>
                    </div>

                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead className="w-10">
                                    <Checkbox
                                        checked={allVisibleSelected ? true : someVisibleSelected ? "indeterminate" : false}
                                        onCheckedChange={toggleAllVisible}
                                    />
                                </TableHead>
                                <TableHead className="w-8" />
                                <TableHead>Serial</TableHead>
                                <TableHead>Current step</TableHead>
                                <TableHead>Status</TableHead>
                                <TableHead>Operator</TableHead>
                                <TableHead>Flags</TableHead>
                                <TableHead className="text-right">Step control</TableHead>
                                <TableHead className="w-10" />
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {filtered.map((p) => {
                                const step = stepById.get(p.step_id);
                                const stepIdx = wo.steps.findIndex((s) => s.id === p.step_id);
                                const isFirst = stepIdx === 0;
                                const isLast = stepIdx === wo.steps.length - 1;
                                const isExpanded = expanded.has(p.id);
                                return (
                                    <Fragment key={p.id}>
                                        <TableRow className={cn(selected.has(p.id) && "bg-accent/50")}>
                                            <TableCell>
                                                <Checkbox
                                                    checked={selected.has(p.id)}
                                                    onCheckedChange={() => toggleOne(p.id)}
                                                />
                                            </TableCell>
                                            <TableCell>
                                                <Button
                                                    size="icon"
                                                    variant="ghost"
                                                    className="h-7 w-7"
                                                    onClick={() => toggleExpanded(p.id)}
                                                >
                                                    {isExpanded ? (
                                                        <ChevronDown className="h-4 w-4" />
                                                    ) : (
                                                        <ChevronRight className="h-4 w-4" />
                                                    )}
                                                </Button>
                                            </TableCell>
                                            <TableCell className="font-mono text-sm">{p.serial}</TableCell>
                                            <TableCell>
                                                <div className="flex items-center gap-2">
                                                    <span className="text-xs text-muted-foreground">{step?.order}.</span>
                                                    <span className="text-sm">{step?.name}</span>
                                                    {step?.requires_qa && (
                                                        <Badge variant="outline" className="px-1 py-0 text-[10px]">
                                                            QA
                                                        </Badge>
                                                    )}
                                                </div>
                                            </TableCell>
                                            <TableCell>
                                                <PartStatusBadge status={p.status} size="sm" />
                                            </TableCell>
                                            <TableCell className="text-sm text-muted-foreground">
                                                {p.operator ?? "—"}
                                            </TableCell>
                                            <TableCell>
                                                <div className="flex flex-wrap gap-1">
                                                    {p.requires_sampling && (
                                                        <Badge variant="outline" className="text-[10px]">
                                                            Sample
                                                        </Badge>
                                                    )}
                                                    {p.rework_count > 0 && (
                                                        <Badge variant="destructive" className="text-[10px]">
                                                            Rework ×{p.rework_count}
                                                        </Badge>
                                                    )}
                                                </div>
                                            </TableCell>
                                            <TableCell className="text-right">
                                                <div className="inline-flex items-center gap-1">
                                                    <Button
                                                        size="icon"
                                                        variant="ghost"
                                                        disabled={isFirst}
                                                        onClick={() => applyToIds([p.id], { kind: "rewind" })}
                                                        title="Previous step"
                                                    >
                                                        <ChevronLeft className="h-4 w-4" />
                                                    </Button>
                                                    <Select
                                                        value={p.step_id}
                                                        onValueChange={(v) => applyToIds([p.id], { kind: "move", stepId: v })}
                                                    >
                                                        <SelectTrigger className="h-8 w-36">
                                                            <SelectValue />
                                                        </SelectTrigger>
                                                        <SelectContent>
                                                            {wo.steps.map((s) => (
                                                                <SelectItem key={s.id} value={s.id}>
                                                                    {s.order}. {s.name}
                                                                </SelectItem>
                                                            ))}
                                                        </SelectContent>
                                                    </Select>
                                                    <Button
                                                        size="icon"
                                                        variant="ghost"
                                                        disabled={isLast}
                                                        onClick={() => applyToIds([p.id], { kind: "advance" })}
                                                        title="Advance step"
                                                    >
                                                        <ChevronRight className="h-4 w-4" />
                                                    </Button>
                                                </div>
                                            </TableCell>
                                            <TableCell>
                                                <DropdownMenu>
                                                    <DropdownMenuTrigger asChild>
                                                        <Button size="icon" variant="ghost">
                                                            <MoreHorizontal className="h-4 w-4" />
                                                        </Button>
                                                    </DropdownMenuTrigger>
                                                    <DropdownMenuContent align="end">
                                                        <DropdownMenuItem
                                                            onClick={() => applyToIds([p.id], { kind: "status", status: "AWAITING_QA" })}
                                                        >
                                                            Send to QA
                                                        </DropdownMenuItem>
                                                        <DropdownMenuItem
                                                            onClick={() =>
                                                                applyToIds([p.id], { kind: "status", status: "READY_FOR_NEXT_STEP" })
                                                            }
                                                        >
                                                            Mark ready for next step
                                                        </DropdownMenuItem>
                                                        <DropdownMenuItem
                                                            onClick={() => applyToIds([p.id], { kind: "status", status: "REWORK_NEEDED" })}
                                                        >
                                                            Flag for rework
                                                        </DropdownMenuItem>
                                                        <DropdownMenuSeparator />
                                                        <DropdownMenuItem
                                                            onClick={() => applyToIds([p.id], { kind: "status", status: "QUARANTINED" })}
                                                        >
                                                            Quarantine
                                                        </DropdownMenuItem>
                                                        <DropdownMenuItem
                                                            variant="destructive"
                                                            onClick={() => applyToIds([p.id], { kind: "scrap", reason: "manual" })}
                                                        >
                                                            Scrap
                                                        </DropdownMenuItem>
                                                    </DropdownMenuContent>
                                                </DropdownMenu>
                                            </TableCell>
                                        </TableRow>
                                        {isExpanded && (
                                            <TableRow className="hover:bg-transparent">
                                                <TableCell colSpan={9} className="p-2">
                                                    <StepHistoryPanelLive partId={p.id} />
                                                </TableCell>
                                            </TableRow>
                                        )}
                                    </Fragment>
                                );
                            })}
                            {filtered.length === 0 && (
                                <TableRow>
                                    <TableCell colSpan={9} className="py-8 text-center text-muted-foreground">
                                        No parts match these filters.
                                    </TableCell>
                                </TableRow>
                            )}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>

            {selected.size > 0 && (
                <div className="fixed bottom-6 left-1/2 z-40 -translate-x-1/2">
                    <Card className="border-primary shadow-lg">
                        <CardContent className="flex items-center gap-2 p-3">
                            <div className="mr-2 border-r pr-2 text-sm font-medium">{selected.size} selected</div>
                            <Button size="sm" variant="outline" onClick={() => applyToSelected({ kind: "rewind" })}>
                                <ChevronLeft className="mr-1 h-4 w-4" />
                                Previous step
                            </Button>
                            <Button size="sm" onClick={() => applyToSelected({ kind: "advance" })}>
                                Advance step
                                <ChevronRight className="ml-1 h-4 w-4" />
                            </Button>
                            <Button
                                size="sm"
                                variant="outline"
                                onClick={() => {
                                    setMoveTarget(wo.steps[0].id);
                                    setMoveDialogOpen(true);
                                }}
                            >
                                Move to step…
                            </Button>
                            <Button size="sm" variant="outline" onClick={() => setStatusDialogOpen(true)}>
                                Set status…
                            </Button>
                            <Button
                                size="sm"
                                variant="outline"
                                onClick={() => applyToSelected({ kind: "status", status: "AWAITING_QA" })}
                            >
                                <CheckCircle2 className="mr-1 h-4 w-4" />
                                Send to QA
                            </Button>
                            <Button
                                size="sm"
                                variant="outline"
                                onClick={() => applyToSelected({ kind: "status", status: "REWORK_NEEDED" })}
                            >
                                <Undo2 className="mr-1 h-4 w-4" />
                                Rework
                            </Button>
                            <Button
                                size="sm"
                                variant="outline"
                                onClick={() => applyToSelected({ kind: "status", status: "QUARANTINED" })}
                            >
                                <AlertTriangle className="mr-1 h-4 w-4" />
                                Quarantine
                            </Button>
                            <Button size="sm" variant="destructive" onClick={() => setScrapDialogOpen(true)}>
                                <XCircle className="mr-1 h-4 w-4" />
                                Scrap
                            </Button>
                            <Button
                                size="sm"
                                variant="outline"
                                onClick={() => enterSplitMode("OPERATION")}
                            >
                                <Split className="mr-1 h-4 w-4" />
                                Split selection…
                            </Button>
                            <Button size="icon" variant="ghost" onClick={() => setSelected(new Set())}>
                                <X className="h-4 w-4" />
                            </Button>
                        </CardContent>
                    </Card>
                </div>
            )}

            <Dialog open={moveDialogOpen} onOpenChange={setMoveDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Move {selected.size} parts to step</DialogTitle>
                        <DialogDescription>
                            Parts will be moved to the selected step. Status is set to In Progress.
                        </DialogDescription>
                    </DialogHeader>
                    <Select value={moveTarget ?? ""} onValueChange={setMoveTarget}>
                        <SelectTrigger>
                            <SelectValue placeholder="Select a step" />
                        </SelectTrigger>
                        <SelectContent>
                            {wo.steps.map((s) => (
                                <SelectItem key={s.id} value={s.id}>
                                    {s.order}. {s.name}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                    <DialogFooter>
                        <Button variant="ghost" onClick={() => setMoveDialogOpen(false)}>
                            Cancel
                        </Button>
                        <Button
                            onClick={() => {
                                if (moveTarget) applyToSelected({ kind: "move", stepId: moveTarget });
                                setMoveDialogOpen(false);
                            }}
                        >
                            Move
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <Dialog open={statusDialogOpen} onOpenChange={setStatusDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Set status for {selected.size} parts</DialogTitle>
                    </DialogHeader>
                    <Select value={statusTarget} onValueChange={(v) => setStatusTarget(v as MockPartStatus)}>
                        <SelectTrigger>
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            {STATUS_OPTIONS.map((s) => (
                                <SelectItem key={s} value={s}>
                                    {prettyStatus(s)}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                    <DialogFooter>
                        <Button variant="ghost" onClick={() => setStatusDialogOpen(false)}>
                            Cancel
                        </Button>
                        <Button
                            onClick={() => {
                                applyToSelected({ kind: "status", status: statusTarget });
                                setStatusDialogOpen(false);
                            }}
                        >
                            Apply
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <Dialog open={scrapDialogOpen} onOpenChange={setScrapDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Scrap {selected.size} parts</DialogTitle>
                        <DialogDescription>
                            This is terminal. Parts moved to SCRAPPED cannot be recovered without a rework flow.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-2">
                        <label className="text-sm">Reason</label>
                        <Input
                            value={scrapReason}
                            onChange={(e) => setScrapReason(e.target.value)}
                            placeholder="e.g. dimensional OOS at step 3"
                        />
                    </div>
                    <DialogFooter>
                        <Button variant="ghost" onClick={() => setScrapDialogOpen(false)}>
                            Cancel
                        </Button>
                        <Button
                            variant="destructive"
                            disabled={!scrapReason.trim()}
                            onClick={() => {
                                applyToSelected({ kind: "scrap", reason: scrapReason });
                                setScrapDialogOpen(false);
                                setScrapReason("");
                            }}
                        >
                            Scrap
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <Dialog open={holdDialogOpen} onOpenChange={setHoldDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Place {wo.erp_id} on hold</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-3">
                        <div>
                            <label className="text-sm">Reason</label>
                            <Select value={holdReason} onValueChange={(v) => setHoldReason(v as HoldReason)}>
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
                        </div>
                        <div>
                            <label className="text-sm">Notes</label>
                            <Textarea
                                value={holdNotes}
                                onChange={(e) => setHoldNotes(e.target.value)}
                                placeholder="What are we waiting on?"
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="ghost" onClick={() => setHoldDialogOpen(false)}>
                            Cancel
                        </Button>
                        <Button onClick={placeOnHold}>Place on hold</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <ReportExceptionDialog
                open={reportOpen}
                onOpenChange={setReportOpen}
                scopedWorkOrderId={wo.id}
                scopedWorkOrderErpId={wo.erp_id}
                onSubmit={reportWoException}
            />
        </div>
    );
}

export default WorkOrderControlPage;
