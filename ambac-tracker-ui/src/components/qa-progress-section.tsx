import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { FileText, Calendar, Package } from "lucide-react";
import { MeasurementProgressChart } from "./measurement-progress-chart";

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