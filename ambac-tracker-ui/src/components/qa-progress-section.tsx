import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { FileText, Calendar, Package, CheckCircle2, Circle, Clock, User, Gauge, AlertTriangle, Paperclip } from "lucide-react";
import { MeasurementProgressChart } from "./measurement-progress-chart";
import { useWorkOrderStepHistory } from "@/hooks/useWorkOrderStepHistory";
import { memo } from "react";

type QaProgressSectionProps = {
    workOrder: any;
    parts: any[];
    isLoadingParts: boolean;
};

export const QaProgressSection = memo(function QaProgressSection({ workOrder, parts, isLoadingParts }: QaProgressSectionProps) {
    const isBatchProcess = workOrder?.is_batch_work_order || false;

    // Calculate progress stats
    const totalParts = parts.length;
    const completedParts = parts.filter(p =>
        p.part_status === 'COMPLETED' || p.part_status === 'PASSED'
    ).length;
    const failedParts = parts.filter(p =>
        p.part_status === 'REWORK_NEEDED' || p.part_status === 'FAILED'
    ).length;
    const progressPercentage = totalParts > 0 ? Math.round((completedParts / totalParts) * 100) : 0;

    // Fetch step history for digital traveler
    const { data: stepHistoryData, isLoading: stepHistoryLoading } = useWorkOrderStepHistory(
        workOrder?.id,
        { enabled: !!workOrder?.id }
    );

    const stepHistory = stepHistoryData?.step_history || [];

    return (
        <div className="space-y-6">
            {/* Work Order Header */}
            <Card>
                <CardHeader className="pb-3">
                    <CardTitle className="text-lg flex items-center gap-2">
                        {workOrder.ERP_id}
                        {isBatchProcess && (
                            <Badge variant="outline" className="text-xs">
                                Batch Process
                            </Badge>
                        )}
                    </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    {/* Customer */}
                    <div className="flex items-start gap-3">
                        <FileText className="h-4 w-4 text-muted-foreground mt-0.5" />
                        <div className="space-y-1">
                            <p className="text-sm font-medium">Customer</p>
                            <p className="text-sm text-muted-foreground">
                                {workOrder.related_order_detail?.company_name || 
                                 workOrder.related_order_detail?.name || 
                                 "Not specified"}
                            </p>
                        </div>
                    </div>

                    {/* Due Date */}
                    <div className="flex items-start gap-3">
                        <Calendar className="h-4 w-4 text-muted-foreground mt-0.5" />
                        <div className="space-y-1">
                            <p className="text-sm font-medium">Due Date</p>
                            <p className="text-sm text-muted-foreground">
                                {workOrder.expected_completion 
                                    ? new Date(workOrder.expected_completion).toLocaleDateString()
                                    : "Not set"
                                }
                            </p>
                        </div>
                    </div>

                    {/* Quantity */}
                    <div className="flex items-start gap-3">
                        <Package className="h-4 w-4 text-muted-foreground mt-0.5" />
                        <div className="space-y-1">
                            <p className="text-sm font-medium">Quantity</p>
                            <p className="text-sm text-muted-foreground">
                                {workOrder.quantity || "Not specified"}
                            </p>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* QA Progress */}
            <Card>
                <CardHeader className="pb-3">
                    <CardTitle className="text-lg">QA Progress</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    {/* Progress Bar */}
                    <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                            <span>Completed</span>
                            <span>{progressPercentage}%</span>
                        </div>
                        <div className="w-full bg-muted rounded-full h-2">
                            <div 
                                className="bg-primary rounded-full h-2 transition-all duration-300"
                                style={{ width: `${progressPercentage}%` }}
                            />
                        </div>
                    </div>

                    <Separator />

                    {/* Stats */}
                    <div className="grid grid-cols-2 gap-4 text-center">
                        <div>
                            <p className="text-2xl font-semibold">{totalParts}</p>
                            <p className="text-xs text-muted-foreground">Total Parts</p>
                        </div>
                        <div>
                            <p className="text-2xl font-semibold text-green-600">{completedParts}</p>
                            <p className="text-xs text-muted-foreground">Completed</p>
                        </div>
                        {failedParts > 0 && (
                            <>
                                <div className="col-span-2">
                                    <p className="text-2xl font-semibold text-red-600">{failedParts}</p>
                                    <p className="text-xs text-muted-foreground">Need Rework</p>
                                </div>
                            </>
                        )}
                    </div>

                    {totalParts === 0 && !isLoadingParts && (
                        <p className="text-center text-sm text-muted-foreground py-4">
                            No parts requiring QA
                        </p>
                    )}
                </CardContent>
            </Card>

            {/* Measurement Progress Chart */}
            <MeasurementProgressChart workOrder={workOrder} />

            {/* Digital Traveler - Step History */}
            <Card>
                <CardHeader className="pb-3">
                    <CardTitle className="text-lg">Digital Traveler</CardTitle>
                    {stepHistoryData?.process_name && (
                        <p className="text-sm text-muted-foreground">{stepHistoryData.process_name}</p>
                    )}
                </CardHeader>
                <CardContent>
                    {stepHistoryLoading ? (
                        <p className="text-sm text-muted-foreground text-center py-4">
                            Loading step history...
                        </p>
                    ) : stepHistory.length === 0 ? (
                        <p className="text-sm text-muted-foreground text-center py-4">
                            No step history available
                        </p>
                    ) : (
                        <div className="space-y-2">
                            {stepHistory
                                .sort((a, b) => a.step_order - b.step_order)
                                .map((step) => {
                                    const isCompleted = step.status === 'COMPLETED';
                                    const isInProgress = step.status === 'IN_PROGRESS';
                                    const _isPending = step.status === 'PENDING';
                                    const isSkipped = step.status === 'SKIPPED';

                                    const hasDefects = step.defect_count > 0;
                                    const hasMeasurements = step.measurement_count > 0;
                                    const hasAttachments = step.attachment_count > 0;

                                    return (
                                        <div
                                            key={step.step_id}
                                            className={`p-3 rounded-lg border transition-colors ${
                                                isInProgress
                                                    ? 'bg-blue-500/10 border-blue-500/50 dark:bg-blue-500/20 dark:border-blue-500/60'
                                                    : isCompleted
                                                    ? 'bg-green-500/10 border-green-500/50 dark:bg-green-500/20 dark:border-green-500/60'
                                                    : isSkipped
                                                    ? 'bg-yellow-500/10 border-yellow-500/50 dark:bg-yellow-500/20 dark:border-yellow-500/60'
                                                    : 'bg-muted/30 border-muted'
                                            }`}
                                        >
                                            <div className="flex items-start gap-3">
                                                <div className="flex-shrink-0 mt-0.5">
                                                    {isCompleted ? (
                                                        <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400" />
                                                    ) : isInProgress ? (
                                                        <Clock className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                                                    ) : (
                                                        <Circle className="h-5 w-5 text-muted-foreground" />
                                                    )}
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-center gap-2 flex-wrap">
                                                        <p className="font-medium text-sm">
                                                            {step.step_name}
                                                        </p>
                                                        {isInProgress && (
                                                            <Badge variant="default" className="text-xs">
                                                                In Progress
                                                            </Badge>
                                                        )}
                                                        {isCompleted && step.quality_status && (
                                                            <Badge
                                                                variant={step.quality_status === 'PASS' ? 'default' : 'destructive'}
                                                                className="text-xs"
                                                            >
                                                                {step.quality_status}
                                                            </Badge>
                                                        )}
                                                        {isSkipped && (
                                                            <Badge variant="secondary" className="text-xs">
                                                                Skipped
                                                            </Badge>
                                                        )}
                                                    </div>

                                                    {/* Step details for completed/in-progress steps */}
                                                    {(isCompleted || isInProgress) && (
                                                        <div className="mt-2 space-y-1">
                                                            {/* Operator & Timing */}
                                                            <div className="flex items-center gap-4 text-xs text-muted-foreground">
                                                                {step.operator_name && (
                                                                    <span className="flex items-center gap-1">
                                                                        <User className="h-3 w-3" />
                                                                        {step.operator_name}
                                                                    </span>
                                                                )}
                                                                {step.completed_at && (
                                                                    <span>
                                                                        {new Date(step.completed_at).toLocaleDateString()}
                                                                    </span>
                                                                )}
                                                                {step.duration_seconds && (
                                                                    <span>
                                                                        {Math.round(step.duration_seconds / 60)}m
                                                                    </span>
                                                                )}
                                                            </div>

                                                            {/* Parts progress */}
                                                            {(step.parts_at_step > 0 || step.parts_completed > 0) && (
                                                                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                                                                    <Package className="h-3 w-3" />
                                                                    <span>{step.parts_completed}/{step.parts_at_step + step.parts_completed} parts</span>
                                                                </div>
                                                            )}

                                                            {/* Counts */}
                                                            <div className="flex items-center gap-3 text-xs">
                                                                {hasMeasurements && (
                                                                    <span className="flex items-center gap-1 text-muted-foreground">
                                                                        <Gauge className="h-3 w-3" />
                                                                        {step.measurement_count}
                                                                    </span>
                                                                )}
                                                                {hasDefects && (
                                                                    <span className="flex items-center gap-1 text-red-600 dark:text-red-400">
                                                                        <AlertTriangle className="h-3 w-3" />
                                                                        {step.defect_count}
                                                                    </span>
                                                                )}
                                                                {hasAttachments && (
                                                                    <span className="flex items-center gap-1 text-muted-foreground">
                                                                        <Paperclip className="h-3 w-3" />
                                                                        {step.attachment_count}
                                                                    </span>
                                                                )}
                                                            </div>
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Notes */}
            {workOrder.notes && (
                <Card>
                    <CardHeader className="pb-3">
                        <CardTitle className="text-lg">Notes</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                            {workOrder.notes}
                        </p>
                    </CardContent>
                </Card>
            )}
        </div>
    );
});