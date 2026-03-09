import { useState, useMemo, Fragment } from "react";
import { useNavigate } from "@tanstack/react-router";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ChevronDown, ChevronRight, ExternalLink, RefreshCw, AlertTriangle } from "lucide-react";
import { useRetrieveParts } from "@/hooks/useRetrieveParts";
import { usePartTraveler } from "@/hooks/usePartTraveler";
import { cn } from "@/lib/utils";

type PartsStatusEnum =
    | "PENDING"
    | "IN_PROGRESS"
    | "AWAITING_QA"
    | "READY_FOR_NEXT_STEP"
    | "COMPLETED"
    | "QUARANTINED"
    | "REWORK_NEEDED"
    | "REWORK_IN_PROGRESS"
    | "SCRAPPED"
    | "CANCELLED"
    | "SHIPPED"
    | "IN_STOCK"
    | "AWAITING_PICKUP"
    | "CORE_BANKED"
    | "RMA_CLOSED";

type Props = {
    workOrderId: string;
    onPartSelect?: (part: any) => void;
    selectedPartId?: string;
};

const STATUS_OPTIONS: { value: string; label: string }[] = [
    { value: "all", label: "All Statuses" },
    { value: "PENDING", label: "Pending" },
    { value: "IN_PROGRESS", label: "In Progress" },
    { value: "AWAITING_QA", label: "Awaiting QA" },
    { value: "READY_FOR_NEXT_STEP", label: "Ready for Next Step" },
    { value: "COMPLETED", label: "Completed" },
    { value: "QUARANTINED", label: "Quarantined" },
    { value: "REWORK_NEEDED", label: "Rework Needed" },
    { value: "REWORK_IN_PROGRESS", label: "Rework In Progress" },
    { value: "SCRAPPED", label: "Scrapped" },
];

const statusColors: Record<string, string> = {
    PENDING: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
    IN_PROGRESS: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300",
    AWAITING_QA: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300",
    READY_FOR_NEXT_STEP: "bg-cyan-100 text-cyan-700 dark:bg-cyan-900 dark:text-cyan-300",
    COMPLETED: "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300",
    QUARANTINED: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300",
    REWORK_NEEDED: "bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300",
    REWORK_IN_PROGRESS: "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300",
    SCRAPPED: "bg-gray-200 text-gray-600 dark:bg-gray-700 dark:text-gray-400",
    CANCELLED: "bg-gray-200 text-gray-500 dark:bg-gray-700 dark:text-gray-400",
    SHIPPED: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300",
    IN_STOCK: "bg-indigo-100 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-300",
};

function StatusBadge({ status }: { status: string }) {
    const colorClass = statusColors[status] || statusColors.PENDING;
    const label = status.replace(/_/g, " ").toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
    return (
        <Badge variant="outline" className={cn("text-xs", colorClass)}>
            {label}
        </Badge>
    );
}

function PartStepHistory({ partId }: { partId: string }) {
    const { data, isLoading } = usePartTraveler(partId, { enabled: true });

    if (isLoading) {
        return (
            <div className="p-4 space-y-2">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
            </div>
        );
    }

    const traveler = data?.traveler || [];

    if (traveler.length === 0) {
        return (
            <div className="p-4 text-sm text-muted-foreground">
                No step history available
            </div>
        );
    }

    return (
        <div className="p-4 bg-muted/30 space-y-2">
            <p className="text-xs font-medium text-muted-foreground mb-2">Step History</p>
            <div className="space-y-1">
                {traveler
                    .sort((a, b) => a.step_order - b.step_order)
                    .map((step, idx) => (
                        <div
                            key={`${step.step_id}-${idx}`}
                            className="flex items-center justify-between text-sm py-1 px-2 rounded bg-background"
                        >
                            <div className="flex items-center gap-2">
                                <span className="text-muted-foreground">{step.step_order}.</span>
                                <span>{step.step_name}</span>
                                {step.visit_number && step.visit_number > 1 && (
                                    <Badge variant="secondary" className="text-xs">
                                        Visit #{step.visit_number}
                                    </Badge>
                                )}
                            </div>
                            <div className="flex items-center gap-2">
                                {step.quality_status && step.quality_status !== "null" && (
                                    <Badge
                                        variant={step.quality_status === "PASS" ? "default" : "destructive"}
                                        className="text-xs"
                                    >
                                        {step.quality_status}
                                    </Badge>
                                )}
                                <span className="text-xs text-muted-foreground">
                                    {step.status}
                                </span>
                            </div>
                        </div>
                    ))}
            </div>
        </div>
    );
}

export function WorkOrderPartsTable({ workOrderId, onPartSelect, selectedPartId }: Props) {
    const navigate = useNavigate();
    const [statusFilter, setStatusFilter] = useState<string>("all");
    const [expandedPartId, setExpandedPartId] = useState<string | null>(null);

    // Fetch all parts for this work order
    const { data: partsData, isLoading, isError, refetch } = useRetrieveParts({
        work_order: workOrderId,
        limit: 200,
    });

    const parts = partsData?.results || [];

    // Filter parts by status
    const filteredParts = useMemo(() => {
        if (statusFilter === "all") return parts;
        return parts.filter((part) => part.part_status === statusFilter);
    }, [parts, statusFilter]);

    // Calculate status counts for filter display
    const statusCounts = useMemo(() => {
        const counts: Record<string, number> = { all: parts.length };
        parts.forEach((part) => {
            const status = part.part_status || "PENDING";
            counts[status] = (counts[status] || 0) + 1;
        });
        return counts;
    }, [parts]);

    const toggleExpand = (partId: string) => {
        setExpandedPartId(expandedPartId === partId ? null : partId);
    };

    const handleRowClick = (part: any) => {
        onPartSelect?.(part);
    };

    const handleViewPart = (partId: string, e: React.MouseEvent) => {
        e.stopPropagation();
        navigate({ to: "/details/$model/$id", params: { model: "Part", id: partId } });
    };

    if (isLoading) {
        return (
            <div className="space-y-4">
                <Skeleton className="h-10 w-48" />
                <Skeleton className="h-64 w-full" />
            </div>
        );
    }

    if (isError) {
        return (
            <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                <AlertTriangle className="h-8 w-8 mb-2" />
                <p>Failed to load parts</p>
                <Button variant="outline" size="sm" className="mt-2" onClick={() => refetch()}>
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Retry
                </Button>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {/* Filters */}
            <div className="flex items-center justify-between">
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                    <SelectTrigger className="w-[200px]">
                        <SelectValue placeholder="Filter by status" />
                    </SelectTrigger>
                    <SelectContent>
                        {STATUS_OPTIONS.map((option) => (
                            <SelectItem key={option.value} value={option.value}>
                                {option.label}
                                {statusCounts[option.value] !== undefined && (
                                    <span className="ml-2 text-muted-foreground">
                                        ({statusCounts[option.value]})
                                    </span>
                                )}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>
                <span className="text-sm text-muted-foreground">
                    {filteredParts.length} of {parts.length} parts
                </span>
            </div>

            {/* Table */}
            {filteredParts.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                    No parts found
                </div>
            ) : (
                <div className="border rounded-lg">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead className="w-8"></TableHead>
                                <TableHead>ERP ID</TableHead>
                                <TableHead>Status</TableHead>
                                <TableHead>Current Step</TableHead>
                                <TableHead className="w-10"></TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {filteredParts.map((part) => {
                                const isExpanded = expandedPartId === part.id;
                                const isSelected = selectedPartId === part.id;

                                return (
                                    <Fragment key={part.id}>
                                        <TableRow
                                            className={cn(
                                                "cursor-pointer",
                                                isSelected && "bg-muted"
                                            )}
                                            onClick={() => handleRowClick(part)}
                                        >
                                            <TableCell>
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    className="h-6 w-6"
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        toggleExpand(part.id);
                                                    }}
                                                >
                                                    {isExpanded ? (
                                                        <ChevronDown className="h-4 w-4" />
                                                    ) : (
                                                        <ChevronRight className="h-4 w-4" />
                                                    )}
                                                </Button>
                                            </TableCell>
                                            <TableCell className="font-medium">
                                                {part.ERP_id || part.id.slice(0, 8)}
                                            </TableCell>
                                            <TableCell>
                                                <StatusBadge status={part.part_status || "PENDING"} />
                                            </TableCell>
                                            <TableCell className="text-muted-foreground">
                                                {(part.step_info as any)?.name || part.step_description || "-"}
                                            </TableCell>
                                            <TableCell>
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    className="h-6 w-6"
                                                    onClick={(e) => handleViewPart(part.id, e)}
                                                    title="View Part Details"
                                                >
                                                    <ExternalLink className="h-3 w-3" />
                                                </Button>
                                            </TableCell>
                                        </TableRow>
                                        {isExpanded && (
                                            <TableRow>
                                                <TableCell colSpan={5} className="p-0">
                                                    <PartStepHistory partId={part.id} />
                                                </TableCell>
                                            </TableRow>
                                        )}
                                    </Fragment>
                                );
                            })}
                        </TableBody>
                    </Table>
                </div>
            )}
        </div>
    );
}
