import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { PartQualityForm } from "./part-quality-form";
import { FpiStatusBanner } from "./fpi-status-banner";
import { useState } from "react";
import { CheckCircle, AlertTriangle, Clock, ShieldCheck, Lock } from "lucide-react";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { useFpiCheckStatus } from "@/hooks/useFpiRecords";

type QaFormSectionProps = {
    workOrder: any;
    parts: any[];
    isLoadingParts: boolean;
    isBatchProcess: boolean;
    selectedPart: any | null;
    onPartSelect: (part: any | null) => void;
    /** Quality reports for this work order - used for legacy FPI check fallback */
    qualityReports?: any[];
    /** Step info with requires_first_piece_inspection flag */
    stepInfo?: { id?: string; requires_first_piece_inspection?: boolean };
};

export function QaFormSection({
    workOrder,
    parts,
    isLoadingParts,
    isBatchProcess,
    selectedPart,
    onPartSelect,
    qualityReports = [],
    stepInfo
}: QaFormSectionProps) {
    const [showQaForm, setShowQaForm] = useState(false);
    const [currentBatchIndex, setCurrentBatchIndex] = useState(0);

    // Use the new FPI API to check status
    const workOrderId = workOrder?.id;
    const stepId = stepInfo?.id;

    const { data: fpiApiStatus, refetch: refetchFpi } = useFpiCheckStatus(
        workOrderId,
        stepId,
        { enabled: !!workOrderId && !!stepId && stepInfo?.requires_first_piece_inspection }
    );

    // Check if a part is blocked by FPI using API response
    const isBlockedByFpi = (_part: any) => {
        // If FPI not required or satisfied, not blocked
        if (!fpiApiStatus?.requires_fpi || fpiApiStatus?.satisfied) {
            return false;
        }
        // If FPI is required but not satisfied, parts are blocked
        // In the new model, we don't designate specific parts as "first piece" upfront
        // The FPI record tracks this separately
        return true;
    };

    // Check if FPI is pending (for UI display)
    const isFpiPending = fpiApiStatus?.requires_fpi && !fpiApiStatus?.satisfied;

    // Check if a part is the first piece candidate (legacy compatibility)
    const isFirstPieceCandidate = (_part: any) => {
        // With the new API model, the first piece is tracked in FPIRecord
        // For now, return false as the banner handles this
        return false;
    };

    if (isLoadingParts) {
        return (
            <div className="space-y-6">
                <Card>
                    <CardHeader>
                        <Skeleton className="h-6 w-48" />
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-4">
                            {Array.from({ length: 3 }).map((_, i) => (
                                <div key={i} className="flex items-center justify-between p-4 border rounded">
                                    <div className="space-y-2">
                                        <Skeleton className="h-4 w-32" />
                                        <Skeleton className="h-3 w-48" />
                                    </div>
                                    <Skeleton className="h-8 w-20" />
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            </div>
        );
    }

    if (parts.length === 0) {
        return (
            <Card>
                <CardContent className="pt-6">
                    <div className="text-center py-8">
                        <CheckCircle className="h-12 w-12 mx-auto text-green-500 mb-4" />
                        <p className="text-lg font-medium">Quality Assurance Complete</p>
                        <p className="text-sm text-muted-foreground mt-2">
                            All parts in this work order have completed quality assurance.
                        </p>
                    </div>
                </CardContent>
            </Card>
        );
    }

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'COMPLETED':
            case 'PASSED':
                return <CheckCircle className="h-4 w-4 text-green-600" />;
            case 'REWORK_NEEDED':
            case 'FAILED':
                return <AlertTriangle className="h-4 w-4 text-red-600" />;
            case 'IN_PROGRESS':
                return <Clock className="h-4 w-4 text-blue-600" />;
            default:
                return <Clock className="h-4 w-4 text-yellow-600" />;
        }
    };

    const canDoQA = (part: any) => {
        // Only allow QA for parts in specific statuses
        const allowedStatuses = [
            "PENDING",
            "AWAITING_QA",
            "IN_PROGRESS",
            "READY_FOR_NEXT_STEP",
            "REWORK_IN_PROGRESS",
            "REWORK_NEEDED"
        ];
        return allowedStatuses.includes(part.part_status);
    };

    const availableParts = parts.filter(canDoQA);

    const handleNextPart = () => {
        if (isBatchProcess && currentBatchIndex < parts.length - 1) {
            setCurrentBatchIndex(currentBatchIndex + 1);
            onPartSelect(parts[currentBatchIndex + 1]);
            setShowQaForm(true);
        } else if (!isBatchProcess) {
            const currentIndex = availableParts.findIndex(p => p.id === selectedPart?.id);
            if (currentIndex >= 0 && currentIndex < availableParts.length - 1) {
                onPartSelect(availableParts[currentIndex + 1]);
                setShowQaForm(true);
            }
        }
    };

    return (
        <div className="space-y-4">
            {/* FPI Status Banner - Now using API-driven component */}
            {workOrderId && stepId && stepInfo?.requires_first_piece_inspection && !showQaForm && (
                <FpiStatusBanner
                    workOrderId={workOrderId}
                    stepId={stepId}
                    onStatusChange={() => refetchFpi()}
                />
            )}

            {/* Compact Batch Header */}
            {isBatchProcess && availableParts.length > 0 && !showQaForm && (
                <div className="bg-blue-500/10 border border-blue-500/50 dark:bg-blue-500/20 dark:border-blue-500/60 rounded-lg p-3">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <AlertTriangle className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                            <div>
                                <p className="font-medium text-sm">
                                    Batch Process
                                    <Badge variant="secondary" className="ml-2 text-xs">
                                        {availableParts.length} forms needed
                                    </Badge>
                                </p>
                            </div>
                        </div>
                        <Button
                            size="sm"
                            onClick={() => {
                                setCurrentBatchIndex(0);
                                onPartSelect(availableParts[0]);
                                setShowQaForm(true);
                            }}
                        >
                            <CheckCircle className="h-4 w-4 mr-2" />
                            Start Forms
                        </Button>
                    </div>
                </div>
            )}

            {/* Compact Part Selector (Non-Batch) */}
            {!isBatchProcess && !showQaForm && (
                <div className="border rounded-lg p-3 bg-background">
                    {availableParts.length === 0 ? (
                        <div className="text-center py-4">
                            <p className="text-sm text-muted-foreground">
                                No parts available for QA at this time.
                            </p>
                        </div>
                    ) : isFpiPending ? (
                        <div className="text-center py-4">
                            <Lock className="h-8 w-8 mx-auto text-amber-500 mb-2" />
                            <p className="text-sm text-muted-foreground">
                                Complete First Piece Inspection above before selecting parts.
                            </p>
                        </div>
                    ) : (
                        <div className="flex items-center gap-3">
                            <label className="text-sm font-medium whitespace-nowrap">Select Part:</label>
                            <Select
                                value={selectedPart?.id?.toString() || ""}
                                onValueChange={(value) => {
                                    const part = availableParts.find(p => p.id === value);
                                    if (part) {
                                        onPartSelect(part);
                                    }
                                }}
                            >
                                <SelectTrigger className="flex-1 min-w-0">
                                    <SelectValue placeholder="Choose a part..." />
                                </SelectTrigger>
                                <SelectContent>
                                    {availableParts.map((part) => (
                                        <SelectItem
                                            key={part.id}
                                            value={part.id.toString()}
                                        >
                                            <div className="flex items-center gap-2">
                                                <span>
                                                    {part.ERP_id} - {part.part_status?.replace('_', ' ')}
                                                </span>
                                            </div>
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            <Button
                                size="sm"
                                disabled={!selectedPart}
                                onClick={() => setShowQaForm(true)}
                                className="flex-shrink-0"
                            >
                                Start QA
                            </Button>
                        </div>
                    )}
                </div>
            )}

            {/* Active QA Form (Inline) */}
            {selectedPart && showQaForm && (
                <div className="space-y-4">
                    {/* Form Header */}
                    <div className="flex items-center justify-between border-b pb-3">
                        <div className="flex items-center gap-3">
                            {getStatusIcon(selectedPart.part_status)}
                            <div>
                                <h3 className="font-semibold">
                                    {isBatchProcess ? "Batch Quality Assessment" : selectedPart.ERP_id}
                                </h3>
                                <p className="text-sm text-muted-foreground">
                                    {isBatchProcess ? (
                                        `Form ${currentBatchIndex + 1} of ${availableParts.length}`
                                    ) : (
                                        `${selectedPart.step_name || selectedPart.step_description || 'N/A'}`
                                    )}
                                </p>
                            </div>
                            {isBatchProcess && (
                                <Badge variant="secondary" className="text-xs">
                                    Batch
                                </Badge>
                            )}
                        </div>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                                setShowQaForm(false);
                                onPartSelect(null);
                            }}
                        >
                            Close
                        </Button>
                    </div>

                    {/* Form */}
                    <PartQualityForm
                        part={selectedPart}
                        onClose={() => {
                            // Check if there's a next part
                            const hasNext = isBatchProcess
                                ? currentBatchIndex < availableParts.length - 1
                                : availableParts.findIndex(p => p.id === selectedPart?.id) < availableParts.length - 1;

                            if (hasNext) {
                                handleNextPart();
                            } else {
                                setShowQaForm(false);
                                onPartSelect(null);
                            }
                        }}
                    />
                </div>
            )}

        </div>
    );
}