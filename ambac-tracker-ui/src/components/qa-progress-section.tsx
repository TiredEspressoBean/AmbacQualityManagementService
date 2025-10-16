import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { FileText, Calendar, Package, CheckCircle2, Circle, ArrowRight } from "lucide-react";
import { MeasurementProgressChart } from "./measurement-progress-chart";
import { useRetrieveProcessWithSteps } from "@/hooks/useRetrieveProcessWithSteps";

type QaProgressSectionProps = {
    workOrder: any;
    parts: any[];
    isLoadingParts: boolean;
};

export function QaProgressSection({ workOrder, parts, isLoadingParts }: QaProgressSectionProps) {
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

    // Get current step from first part (all parts in QA should be on same step)
    const currentPart = parts[0];
    const processId = currentPart?.process;
    const currentStepId = currentPart?.step;

    // Fetch process with all steps
    const { data: processWithSteps, isLoading: processLoading } = useRetrieveProcessWithSteps(
        { params: { id: processId! } },
        { enabled: !!processId && processId !== undefined }
    );

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
            <MeasurementProgressChart workOrder={workOrder} parts={parts} />

            {/* Process Steps */}
            {processWithSteps && processWithSteps.steps && processWithSteps.steps.length > 0 && (
                <Card>
                    <CardHeader className="pb-3">
                        <CardTitle className="text-lg">Process Steps</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-2">
                            {processWithSteps.steps
                                .sort((a, b) => a.order - b.order)
                                .map((step, index) => {
                                    const isCurrentStep = step.id === currentStepId;
                                    const isPastStep = step.order < (currentPart?.step_info as any)?.order;
                                    const isFutureStep = step.order > (currentPart?.step_info as any)?.order;

                                    return (
                                        <div
                                            key={step.id}
                                            className={`flex items-start gap-3 p-3 rounded-lg border transition-colors ${
                                                isCurrentStep
                                                    ? 'bg-blue-500/10 border-blue-500/50 dark:bg-blue-500/20 dark:border-blue-500/60'
                                                    : isPastStep
                                                    ? 'bg-green-500/10 border-green-500/50 dark:bg-green-500/20 dark:border-green-500/60'
                                                    : 'bg-muted/30 border-muted'
                                            }`}
                                        >
                                            <div className="flex-shrink-0 mt-0.5">
                                                {isPastStep ? (
                                                    <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400" />
                                                ) : isCurrentStep ? (
                                                    <Circle className="h-5 w-5 text-blue-600 fill-blue-600 dark:text-blue-400 dark:fill-blue-400" />
                                                ) : (
                                                    <Circle className="h-5 w-5 text-muted-foreground" />
                                                )}
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2">
                                                    <p className="font-medium text-sm">
                                                        {step.name}
                                                    </p>
                                                    {isCurrentStep && (
                                                        <Badge variant="default" className="text-xs">
                                                            Current
                                                        </Badge>
                                                    )}
                                                    {step.sampling_required && (
                                                        <Badge variant="outline" className="text-xs">
                                                            QA Required
                                                        </Badge>
                                                    )}
                                                </div>
                                                {step.description && (
                                                    <p className="text-xs text-muted-foreground mt-1">
                                                        {step.description}
                                                    </p>
                                                )}
                                            </div>
                                            {index < processWithSteps.steps.length - 1 && (
                                                <ArrowRight className="h-4 w-4 text-muted-foreground flex-shrink-0 mt-1" />
                                            )}
                                        </div>
                                    );
                                })}
                        </div>
                        {processLoading && (
                            <p className="text-sm text-muted-foreground text-center py-4">
                                Loading process steps...
                            </p>
                        )}
                    </CardContent>
                </Card>
            )}

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
}