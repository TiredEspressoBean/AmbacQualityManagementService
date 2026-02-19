import { useParams, useNavigate } from "@tanstack/react-router";
import { useRetrieveWorkOrder } from "@/hooks/useRetrieveWorkOrder";
import { useRetrieveParts } from "@/hooks/useRetrieveParts";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";
import { ArrowLeft } from "lucide-react";
import { QaProgressSection } from "@/components/qa-progress-section";
import { QaFormSection } from "@/components/qa-form-section";
import { QaRightPanel } from "@/components/qa-right-panel";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useState } from "react";

export function QaWorkOrderDetailPage() {
    const { workOrderId } = useParams({ from: "/qa/workorder/$workOrderId" });
    const navigate = useNavigate();
    const [activeTab, setActiveTab] = useState("qa-forms");
    const [selectedPart, setSelectedPart] = useState<any | null>(null);

    // Fetch work order details
    const { data: workOrder, isLoading: isLoadingWorkOrder, error: workOrderError } = useRetrieveWorkOrder(
        workOrderId
    );

    // Fetch parts for this work order that require QA
    const { data: partsData, isLoading: isLoadingParts } = useRetrieveParts({
        work_order: workOrderId,
        requires_sampling: true,
        part_status__in: "PENDING,IN_PROGRESS,REWORK_NEEDED,REWORK_IN_PROGRESS",
        limit: 100,
    });

    const parts = partsData?.results || [];
    const isBatchProcess = workOrder?.is_batch_work_order || false;

    if (isLoadingWorkOrder) {
        return (
            <div className="space-y-6">
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
            <div className="space-y-6">
                <Button 
                    variant="ghost" 
                    onClick={() => navigate({ to: "/QA" })}
                >
                    <ArrowLeft className="h-4 w-4 mr-2" />
                    Back to QA
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

    return (
        <div className="space-y-4">
            {/* Header */}
            <div className="flex items-center gap-4">
                <Button
                    variant="ghost"
                    onClick={() => navigate({ to: "/QA" })}
                >
                    <ArrowLeft className="h-4 w-4 mr-2" />
                    Back to QA
                </Button>
                <div>
                    <h1 className="text-2xl font-semibold">
                        {workOrder.ERP_id}
                        {isBatchProcess && <span className="text-sm text-muted-foreground ml-2">(Batch Process)</span>}
                    </h1>
                    <p className="text-muted-foreground">
                        Quality Assurance
                        {(workOrder.process_info as any)?.name && (
                            <span className="ml-2">• Process: {(workOrder.process_info as any).name}</span>
                        )}
                    </p>
                </div>
            </div>

            {/* Resizable Panel Layout */}
            <ResizablePanelGroup direction="horizontal" className="w-full max-w-[1600px] mx-auto rounded-lg border min-h-[calc(100vh-200px)]">
                {/* Left Panel - Work Order Info & QA Forms */}
                <ResizablePanel defaultSize={40} minSize={30} className="p-6">
                    <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full">
                        <TabsList className="grid w-full grid-cols-2">
                            <TabsTrigger value="overview">Overview</TabsTrigger>
                            <TabsTrigger value="qa-forms">QA Forms</TabsTrigger>
                        </TabsList>

                        <TabsContent value="overview" className="mt-6 h-full">
                            <QaProgressSection
                                workOrder={workOrder}
                                parts={parts}
                                isLoadingParts={isLoadingParts}
                            />
                        </TabsContent>

                        <TabsContent value="qa-forms" className="mt-6 h-full">
                            <QaFormSection
                                workOrder={workOrder}
                                parts={parts}
                                isLoadingParts={isLoadingParts}
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