import { useParams, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useRetrieveWorkOrder } from "@/hooks/useRetrieveWorkOrder";
import { useRetrieveParts } from "@/hooks/useRetrieveParts";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ArrowLeft, AlertTriangle } from "lucide-react";
import { QaProgressSection } from "@/components/qa-progress-section";
import { QaFormSection } from "@/components/qa-form-section";
import { QaRightPanel } from "@/components/qa-right-panel";
import { WorkOrderStatusActions } from "@/components/work-order-status-actions";
import { WorkOrderPartsTable } from "@/components/work-order-parts-table";
import { StatusBadge } from "@/components/flow/overlays/StatusBadge";
import { cn } from "@/lib/utils";
import type { WorkOrderStatusEnum } from "@/lib/api/generated";

const PRIORITY_LABELS: Record<number, { label: string; className: string }> = {
    1: { label: "Critical", className: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300" },
    2: { label: "High", className: "bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300" },
    3: { label: "Normal", className: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300" },
    4: { label: "Low", className: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300" },
};

export function WorkOrderDetailPage() {
    const { workOrderId } = useParams({ from: "/workorder/$workOrderId" });
    const navigate = useNavigate();
    const [activeTab, setActiveTab] = useState("overview");
    const [selectedPart, setSelectedPart] = useState<any | null>(null);

    // Fetch work order details
    const {
        data: workOrder,
        isLoading: isLoadingWorkOrder,
        error: workOrderError,
        refetch: refetchWorkOrder,
    } = useRetrieveWorkOrder(workOrderId);

    // Fetch parts needing QA (for QA Forms tab)
    const { data: qaPartsData, isLoading: isLoadingQaParts } = useRetrieveParts({
        work_order: workOrderId,
        needs_qa: true,
        status__in: ["PENDING", "IN_PROGRESS", "AWAITING_QA", "REWORK_NEEDED", "REWORK_IN_PROGRESS", "READY_FOR_NEXT_STEP"],
        limit: 100,
    });

    // Fetch all parts for overview stats
    const { data: allPartsData, isLoading: isLoadingAllParts } = useRetrieveParts({
        work_order: workOrderId,
        limit: 200,
    });

    const qaParts = qaPartsData?.results || [];
    const allParts = allPartsData?.results || [];
    const isBatchProcess = workOrder?.is_batch_work_order || false;

    // Check if work order is overdue
    const isOverdue = workOrder?.expected_completion
        ? new Date(workOrder.expected_completion) < new Date()
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
                    onClick={() => navigate({ to: "/editor/WorkOrders" })}
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
                        onClick={() => navigate({ to: "/editor/WorkOrders" })}
                    >
                        <ArrowLeft className="h-4 w-4 mr-2" />
                        Back
                    </Button>
                    <div className="flex items-center gap-3">
                        <h1 className="text-2xl font-semibold">
                            {workOrder.ERP_id}
                        </h1>
                        <StatusBadge status={currentStatus} />
                        <Badge className={cn("text-xs", priorityConfig.className)}>
                            {priorityConfig.label}
                        </Badge>
                        {isBatchProcess && (
                            <Badge variant="outline" className="text-xs">
                                Batch
                            </Badge>
                        )}
                        {isOverdue && currentStatus !== "COMPLETED" && currentStatus !== "CANCELLED" && (
                            <Badge variant="destructive" className="text-xs flex items-center gap-1">
                                <AlertTriangle className="h-3 w-3" />
                                Overdue
                            </Badge>
                        )}
                    </div>
                </div>

                {/* Status Actions */}
                <WorkOrderStatusActions
                    workOrderId={workOrderId}
                    currentStatus={currentStatus}
                    currentNotes={workOrder.notes}
                    onStatusChange={() => refetchWorkOrder()}
                />
            </div>

            {/* Process Info */}
            {(workOrder.process_info as any)?.name && (
                <p className="text-muted-foreground">
                    Process: {(workOrder.process_info as any).name}
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
                            <TabsTrigger value="qa-forms">QA Forms</TabsTrigger>
                        </TabsList>

                        <TabsContent value="overview" className="mt-6 h-full overflow-auto">
                            <QaProgressSection
                                workOrder={workOrder}
                                parts={allParts}
                                isLoadingParts={isLoadingAllParts}
                            />
                        </TabsContent>

                        <TabsContent value="parts" className="mt-6 h-full overflow-auto">
                            <WorkOrderPartsTable
                                workOrderId={workOrderId}
                                onPartSelect={setSelectedPart}
                                selectedPartId={selectedPart?.id}
                            />
                        </TabsContent>

                        <TabsContent value="qa-forms" className="mt-6 h-full overflow-auto">
                            <QaFormSection
                                workOrder={workOrder}
                                parts={qaParts}
                                isLoadingParts={isLoadingQaParts}
                                isBatchProcess={isBatchProcess}
                                selectedPart={selectedPart}
                                onPartSelect={setSelectedPart}
                            />
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
