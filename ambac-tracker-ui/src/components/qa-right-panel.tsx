import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { QaDocumentsSection } from "./qa-documents-section";
import { useRetrieveThreeDModels } from "@/hooks/useRetrieveThreeDModels";
import { usePartTraveler } from "@/hooks/usePartTraveler";
import { Box, History, CheckCircle2, Clock, Circle, User, Gauge, AlertTriangle, Paperclip, Wrench } from "lucide-react";
import type { schemas } from "@/lib/api/generated";
import { z } from "zod";
import { PartAnnotator } from "@/pages/PartAnnotator";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

type WorkOrder = z.infer<typeof schemas.WorkOrder>;
type Part = z.infer<typeof schemas.Part>;

type Props = {
    workOrder: WorkOrder;
    selectedPart: Part | null;
};

export function QaRightPanel({ workOrder, selectedPart }: Props) {
    // Fetch 3D models for the selected part's part type (non-archived only)
    const { data: modelsData, isLoading: modelsLoading } = useRetrieveThreeDModels({
        queries: {
            part_type: selectedPart?.part_type,
            // archived: false,
            limit: 1,
        },
    });

    // Fetch part traveler when a part is selected
    const { data: travelerData, isLoading: travelerLoading } = usePartTraveler(
        selectedPart?.id || "",
        { enabled: !!selectedPart?.id }
    );

    // Check count field from paginated response to see if any 3D models exist
    const has3DModel = !modelsLoading && modelsData && modelsData.count > 0;

    // Get the first model if available
    const model3D = has3DModel ? modelsData.results[0] : null;

    const traveler = travelerData?.traveler || [];

    // If no part selected, show only documents
    if (!selectedPart) {
        return <QaDocumentsSection workOrder={workOrder} />;
    }

    // Part selected - show tabs with traveler, documents, and optionally 3D
    const tabCount = has3DModel ? 3 : 2;

    return (
        <Tabs defaultValue="traveler" className="h-full">
            <TabsList className={`grid w-full grid-cols-${tabCount}`}>
                <TabsTrigger value="traveler">
                    <History className="h-4 w-4 mr-2" />
                    Traveler
                </TabsTrigger>
                <TabsTrigger value="documents">Documents</TabsTrigger>
                {has3DModel && (
                    <TabsTrigger value="annotations">
                        <Box className="h-4 w-4 mr-2" />
                        3D
                    </TabsTrigger>
                )}
            </TabsList>

            <TabsContent value="traveler" className="h-full mt-4 overflow-auto">
                <Card>
                    <CardHeader className="pb-3">
                        <CardTitle className="text-lg flex items-center gap-2">
                            Part Traveler
                            <Badge variant="outline" className="text-xs font-normal">
                                {selectedPart.ERP_id || selectedPart.id}
                            </Badge>
                        </CardTitle>
                        {travelerData?.process_name && (
                            <p className="text-sm text-muted-foreground">{travelerData.process_name}</p>
                        )}
                    </CardHeader>
                    <CardContent>
                        {travelerLoading ? (
                            <p className="text-sm text-muted-foreground text-center py-4">
                                Loading traveler...
                            </p>
                        ) : traveler.length === 0 ? (
                            <p className="text-sm text-muted-foreground text-center py-4">
                                No history available for this part
                            </p>
                        ) : (
                            <div className="space-y-4">
                                {traveler
                                    .sort((a, b) => a.step_order - b.step_order)
                                    .map((step) => {
                                        const isCompleted = step.status === 'COMPLETED';
                                        const isInProgress = step.status === 'IN_PROGRESS';
                                        const isSkipped = step.status === 'SKIPPED';

                                        return (
                                            <div
                                                key={`${step.step_id}-${step.visit_number || 1}`}
                                                className={`p-4 rounded-lg border ${
                                                    isInProgress
                                                        ? 'bg-blue-500/10 border-blue-500/50'
                                                        : isCompleted
                                                        ? 'bg-green-500/10 border-green-500/50'
                                                        : isSkipped
                                                        ? 'bg-yellow-500/10 border-yellow-500/50'
                                                        : 'bg-muted/30 border-muted'
                                                }`}
                                            >
                                                {/* Step Header */}
                                                <div className="flex items-start gap-3">
                                                    <div className="flex-shrink-0 mt-0.5">
                                                        {isCompleted ? (
                                                            <CheckCircle2 className="h-5 w-5 text-green-600" />
                                                        ) : isInProgress ? (
                                                            <Clock className="h-5 w-5 text-blue-600" />
                                                        ) : (
                                                            <Circle className="h-5 w-5 text-muted-foreground" />
                                                        )}
                                                    </div>
                                                    <div className="flex-1">
                                                        <div className="flex items-center gap-2 flex-wrap">
                                                            <p className="font-medium">{step.step_name}</p>
                                                            {(step.visit_number ?? 1) > 1 && (
                                                                <Badge variant="secondary" className="text-xs">
                                                                    Visit #{step.visit_number}
                                                                </Badge>
                                                            )}
                                                            {step.quality_status && step.quality_status !== 'null' && (
                                                                <Badge
                                                                    variant={step.quality_status === 'PASS' ? 'default' : 'destructive'}
                                                                    className="text-xs"
                                                                >
                                                                    {step.quality_status}
                                                                </Badge>
                                                            )}
                                                        </div>

                                                        {/* Operator & Timing */}
                                                        {(isCompleted || isInProgress) && (
                                                            <div className="mt-2 text-sm text-muted-foreground space-y-1">
                                                                {step.operator?.name && (
                                                                    <div className="flex items-center gap-2">
                                                                        <User className="h-3 w-3" />
                                                                        <span>{step.operator.name}</span>
                                                                        {step.operator.employee_id && (
                                                                            <span className="text-xs">({step.operator.employee_id})</span>
                                                                        )}
                                                                    </div>
                                                                )}
                                                                <div className="flex items-center gap-4 text-xs">
                                                                    {step.started_at && (
                                                                        <span>Started: {new Date(step.started_at).toLocaleString()}</span>
                                                                    )}
                                                                    {step.completed_at && (
                                                                        <span>Completed: {new Date(step.completed_at).toLocaleString()}</span>
                                                                    )}
                                                                    {step.duration_seconds && (
                                                                        <span>Duration: {Math.round(step.duration_seconds / 60)}m</span>
                                                                    )}
                                                                </div>
                                                            </div>
                                                        )}

                                                        {/* Equipment */}
                                                        {step.equipment_used && step.equipment_used.length > 0 && (
                                                            <div className="mt-2">
                                                                <p className="text-xs font-medium text-muted-foreground mb-1">Equipment:</p>
                                                                <div className="flex flex-wrap gap-1">
                                                                    {step.equipment_used.map((eq) => (
                                                                        <Badge key={eq.id} variant="outline" className="text-xs">
                                                                            <Wrench className="h-3 w-3 mr-1" />
                                                                            {eq.name}
                                                                        </Badge>
                                                                    ))}
                                                                </div>
                                                            </div>
                                                        )}

                                                        {/* Measurements */}
                                                        {step.measurements && step.measurements.length > 0 && (
                                                            <div className="mt-3">
                                                                <p className="text-xs font-medium text-muted-foreground mb-1 flex items-center gap-1">
                                                                    <Gauge className="h-3 w-3" />
                                                                    Measurements ({step.measurements.length})
                                                                </p>
                                                                <div className="space-y-1">
                                                                    {step.measurements.slice(0, 5).map((m, idx) => (
                                                                        <div key={idx} className="flex items-center justify-between text-xs bg-background/50 rounded px-2 py-1">
                                                                            <span>{m.label}</span>
                                                                            <span className={m.passed ? 'text-green-600' : 'text-red-600'}>
                                                                                {m.actual_value} {m.unit}
                                                                                {m.nominal && (
                                                                                    <span className="text-muted-foreground ml-1">
                                                                                        (nom: {m.nominal})
                                                                                    </span>
                                                                                )}
                                                                            </span>
                                                                        </div>
                                                                    ))}
                                                                    {step.measurements.length > 5 && (
                                                                        <p className="text-xs text-muted-foreground">
                                                                            +{step.measurements.length - 5} more
                                                                        </p>
                                                                    )}
                                                                </div>
                                                            </div>
                                                        )}

                                                        {/* Defects */}
                                                        {step.defects_found && step.defects_found.length > 0 && (
                                                            <div className="mt-3">
                                                                <p className="text-xs font-medium text-red-600 mb-1 flex items-center gap-1">
                                                                    <AlertTriangle className="h-3 w-3" />
                                                                    Defects ({step.defects_found.length})
                                                                </p>
                                                                <div className="space-y-1">
                                                                    {step.defects_found.map((d, idx) => (
                                                                        <div key={idx} className="flex items-center justify-between text-xs bg-red-500/10 rounded px-2 py-1">
                                                                            <span>{d.error_name}</span>
                                                                            <Badge variant="outline" className="text-xs">
                                                                                {d.severity}
                                                                            </Badge>
                                                                        </div>
                                                                    ))}
                                                                </div>
                                                            </div>
                                                        )}

                                                        {/* Attachments */}
                                                        {step.attachments && step.attachments.length > 0 && (
                                                            <div className="mt-2 flex items-center gap-1 text-xs text-muted-foreground">
                                                                <Paperclip className="h-3 w-3" />
                                                                <span>{step.attachments.length} attachment(s)</span>
                                                            </div>
                                                        )}

                                                        {/* Approval */}
                                                        {step.approved_by?.name && (
                                                            <div className="mt-2 text-xs text-muted-foreground">
                                                                <span>Approved by: {step.approved_by.name}</span>
                                                                {step.approved_by.approved_at && (
                                                                    <span> at {new Date(step.approved_by.approved_at).toLocaleString()}</span>
                                                                )}
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
            </TabsContent>

            <TabsContent value="documents" className="h-full mt-4">
                <QaDocumentsSection workOrder={workOrder} />
            </TabsContent>

            {has3DModel && (
                <TabsContent value="annotations" className="h-full mt-4 min-h-[500px]">
                    {model3D && (
                        <PartAnnotator
                            modelId={model3D.id}
                            partId={selectedPart.id}
                            workOrderId={workOrder.id}
                            className="h-full min-h-[500px]"
                            showHeader={false}
                            startExpanded={false}
                        />
                    )}
                </TabsContent>
            )}
        </Tabs>
    );
}