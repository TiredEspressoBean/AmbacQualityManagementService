import { useParams, useSearch, Link } from "@tanstack/react-router";
import { WorkOrderHoldBanner, WorkOrderHoldHistory, type WorkOrderHold } from "@/components/workorders/WorkOrderHoldBanner";
import { MakeupPanel } from "@/components/workorders/MakeupPanel";
import { useState } from "react";
import { useRetrieveWorkOrder } from "@/hooks/useRetrieveWorkOrder";
import { useRetrieveParts } from "@/hooks/parts";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ArrowLeft, AlertTriangle, Truck } from "lucide-react";
import { QaProgressSection } from "@/components/qa-progress-section";
import { QaRightPanel } from "@/components/qa-right-panel";
import { WorkOrderStatusActions } from "@/components/work-order-status-actions";
import { StartWorkDialog } from "@/components/workorder/StartWorkDialog";
import { WorkOrderPartsTable } from "@/components/work-order-parts-table";
import { WorkOrderMaterialsPanel } from "@/components/workorder/WorkOrderMaterialsPanel";
import { WorkOrderDocuments } from "@/components/reports/WorkOrderDocuments";
import { StatusBadge } from "@/components/flow/overlays/StatusBadge";
import { cn } from "@/lib/utils";
import type { WorkOrderStatusEnum } from "@/lib/api/generated";
import { parseDateOnly } from "@/lib/date-only";

const PRIORITY_LABELS: Record<number, { label: string; className: string }> = {
    1: { label: "Critical", className: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300" },
    2: { label: "High", className: "bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300" },
    3: { label: "Normal", className: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300" },
    4: { label: "Low", className: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300" },
};

export function WorkOrderDetailPage() {
    // `?start=<part>` (a scanned part serial) opens Start Work with that part ticked.
    const startPartId = (useSearch({ strict: false }) as { start?: string }).start;
    const { workOrderId } = useParams({ from: "/workorder/$workOrderId" });
    const [activeTab, setActiveTab] = useState("overview");
    const [selectedPart, setSelectedPart] = useState<any | null>(null);
    const [partsStatusFilter, setPartsStatusFilter] = useState<string>("all");

    // Jump from an Exceptions badge into the Parts tab pre-filtered to that
    // status. Non-lead QA reaches the actionable Awaiting QA queue with one
    // click instead of hunting through the Control Center.
    const handleJumpToStatus = (status: string) => {
        setPartsStatusFilter(status);
        setActiveTab("parts");
    };

    // Fetch work order details
    const {
        data: workOrder,
        isLoading: isLoadingWorkOrder,
        error: workOrderError,
        refetch: refetchWorkOrder,
    } = useRetrieveWorkOrder(workOrderId);

    // Fetch all parts for overview stats
    const { data: allPartsData, isLoading: isLoadingAllParts } = useRetrieveParts({
        work_order: workOrderId,
        limit: 200,
    });

    const allParts = allPartsData?.results || [];

    // Parts currently out at a subcontract vendor (Flow B). The send-out /
    // receive-back actions live on the Control page — this is a link there.
    const atOspCount = allParts.filter((p) => p.part_status === "AT_OUTSIDE_PROCESS").length;

    // Check if work order is overdue
    const isOverdue = workOrder?.expected_completion
        ? parseDateOnly(workOrder.expected_completion) < new Date()
        : false;

    if (isLoadingWorkOrder) {
        return (
            <div className="space-y-6 p-6">
                <div className="flex items-center gap-4">
                    <Skeleton className="h-10 w-32" />
                    <Skeleton className="h-8 w-64" />
                </div>
                <Card>
                    <CardHeader>
                        <Skeleton className="h-6 w-48" />
                    </CardHeader>
                    <CardContent>
                        <Skeleton className="h-32 w-full" />
                    </CardContent>
                </Card>
            </div>
        );
    }

    if (workOrderError || !workOrder) {
        return (
            <div className="space-y-6 p-6">
                <Button
                    variant="ghost"
                    onClick={() => window.history.back()}
                >
                    <ArrowLeft className="h-4 w-4 mr-2" />
                    Back to Work Orders
                </Button>
                <Card>
                    <CardContent className="pt-6">
                        <p className="text-muted-foreground text-center">
                            Work order not found or access denied.
                        </p>
                    </CardContent>
                </Card>
            </div>
        );
    }

    const currentStatus = (workOrder.workorder_status || "PENDING") as WorkOrderStatusEnum;
    const priority = workOrder.priority || 3;
    const priorityConfig = PRIORITY_LABELS[priority] || PRIORITY_LABELS[3];

    return (
        <div className="space-y-4 p-6">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex items-center gap-4">
                    <Button
                        variant="ghost"
                        onClick={() => window.history.back()}
                    >
                        <ArrowLeft className="h-4 w-4 mr-2" />
                        Back
                    </Button>
                    <div className="flex items-center gap-3">
                        <h1 className="text-2xl font-semibold">
                            {workOrder.ERP_id}
                        </h1>
                        <StatusBadge status={currentStatus} />
                        {workOrder.short_closed && (
                            <Badge variant="outline" className="text-xs" title={workOrder.short_close_reason || undefined}>
                                Short-closed
                            </Badge>
                        )}
                        <Badge className={cn("text-xs", priorityConfig.className)}>
                            {priorityConfig.label}
                        </Badge>
                        {isOverdue && currentStatus !== "COMPLETED" && currentStatus !== "CANCELLED" && (
                            <Badge variant="destructive" className="text-xs flex items-center gap-1">
                                <AlertTriangle className="h-3 w-3" />
                                Overdue
                            </Badge>
                        )}
                        {atOspCount > 0 && (
                            <Link
                                to="/workorder/$workOrderId/control"
                                params={{ workOrderId }}
                                title="Manage send-out / receive-back on the Control page"
                            >
                                <Badge variant="outline" className="text-xs flex items-center gap-1 hover:bg-accent">
                                    <Truck className="h-3 w-3" />
                                    {atOspCount} at outside process
                                </Badge>
                            </Link>
                        )}
                    </div>
                </div>

                {/* Status Actions */}
                <div className="flex items-center gap-2">
                    <WorkOrderDocuments workOrderId={workOrderId} />
                    <StartWorkDialog workOrderId={workOrderId} blockedReason={workOrder.start_refusal}
                                     initialPartId={startPartId} />
                    <WorkOrderStatusActions
                        workOrderId={workOrderId}
                        currentStatus={currentStatus}
                        releasedAt={workOrder.released_at}
                        currentHold={(workOrder.current_hold as WorkOrderHold | null) ?? null}
                        onStatusChange={() => refetchWorkOrder()}
                    />
                </div>
            </div>

            {/* Why it stopped — the lead deciding whether to resume needs it here. */}
            {workOrder.current_hold && <WorkOrderHoldBanner hold={workOrder.current_hold as WorkOrderHold} />}
            <WorkOrderHoldHistory holds={workOrder.hold_history ?? []} />

            {/* Make-up: replace scrap so the order still delivers its good count. Only
                shown when there's a shortfall (the schedule's WO dialog always shows it). */}
            <MakeupPanel workOrderId={workOrderId} onlyWhenShort />

            {/* Process Info */}
            {workOrder.process_info?.name && (
                <p className="text-muted-foreground">
                    Process: {workOrder.process_info.name}
                </p>
            )}

            {/* Resizable Panel Layout */}
            <ResizablePanelGroup
                direction="horizontal"
                className="w-full max-w-[1600px] mx-auto rounded-lg border min-h-[calc(100vh-220px)]"
            >
                {/* Left Panel - Work Order Info & Forms */}
                <ResizablePanel defaultSize={40} minSize={30} className="p-6">
                    <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full">
                        <TabsList className="grid w-full grid-cols-3">
                            <TabsTrigger value="overview">Overview</TabsTrigger>
                            <TabsTrigger value="parts">Parts</TabsTrigger>
                            <TabsTrigger value="materials">Materials</TabsTrigger>
                        </TabsList>

                        <TabsContent value="overview" className="mt-6 h-full overflow-auto">
                            <QaProgressSection
                                workOrder={workOrder}
                                parts={allParts}
                                isLoadingParts={isLoadingAllParts}
                                onJumpToStatus={handleJumpToStatus}
                            />
                        </TabsContent>

                        <TabsContent value="parts" className="mt-6 h-full overflow-auto">
                            <WorkOrderPartsTable
                                workOrderId={workOrderId}
                                onPartSelect={setSelectedPart}
                                selectedPartId={selectedPart?.id}
                                statusFilter={partsStatusFilter}
                                onStatusFilterChange={setPartsStatusFilter}
                            />
                        </TabsContent>

                        <TabsContent value="materials" className="mt-6 h-full overflow-auto">
                            <WorkOrderMaterialsPanel workOrderId={workOrderId} />
                        </TabsContent>
                    </Tabs>
                </ResizablePanel>

                <ResizableHandle />

                {/* Right Panel - Documents / 3D Annotations */}
                <ResizablePanel defaultSize={60} minSize={40} className="p-6">
                    <QaRightPanel
                        workOrder={workOrder}
                        selectedPart={selectedPart}
                    />
                </ResizablePanel>
            </ResizablePanelGroup>
        </div>
    );
}
