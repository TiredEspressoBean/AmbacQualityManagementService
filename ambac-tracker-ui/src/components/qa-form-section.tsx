import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { PartQualityForm } from "./part-quality-form";
import { useState, useMemo } from "react";
import { CheckCircle, AlertTriangle, Clock, ShieldCheck, Lock } from "lucide-react";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";

type FpiStatus = 'not_required' | 'pending' | 'passed' | 'failed';

type QaFormSectionProps = {
    workOrder: any;
    parts: any[];
    isLoadingParts: boolean;
    isBatchProcess: boolean;
    selectedPart: any | null;
    onPartSelect: (part: any | null) => void;
    /** Quality reports for this work order - used to check FPI status */
    qualityReports?: any[];
    /** Step info with requires_first_piece_inspection flag */
    stepInfo?: { requires_first_piece_inspection?: boolean };
};

/**
 * Compute FPI status for a step based on parts and quality reports
 */
function computeFpiStatus(
    parts: any[],
    qualityReports: any[],
    stepRequiresFpi: boolean
): { status: FpiStatus; firstPiecePart: any | null; fpiReport: any | null } {
    if (!stepRequiresFpi) {
        return { status: 'not_required', firstPiecePart: null, fpiReport: null };
    }

    // Find FPI reports for this step
    const fpiReports = qualityReports.filter(qr => qr.is_first_piece);

    // Check for passing FPI
    const passingFpi = fpiReports.find(qr => qr.status === 'PASS');
    if (passingFpi) {
        const fpiPart = parts.find(p => p.id === passingFpi.part);
        return { status: 'passed', firstPiecePart: fpiPart, fpiReport: passingFpi };
    }

    // Check for failing FPI
    const failingFpi = fpiReports.find(qr => qr.status === 'FAIL');
    if (failingFpi) {
        const fpiPart = parts.find(p => p.id === failingFpi.part);
        return { status: 'failed', firstPiecePart: fpiPart, fpiReport: failingFpi };
    }

    // No FPI yet - find the first piece candidate (earliest created_at)
    const sortedParts = [...parts].sort((a, b) =>
        new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
    );
    const firstPiecePart = sortedParts[0] || null;

    return { status: 'pending', firstPiecePart, fpiReport: null };
}

export function QaFormSection({
    _workOrder,
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

    // Compute FPI status
    const fpiStatus = useMemo(() => {
        const requiresFpi = stepInfo?.requires_first_piece_inspection ?? false;
        return computeFpiStatus(parts, qualityReports, requiresFpi);
    }, [parts, qualityReports, stepInfo?.requires_first_piece_inspection]);

    // Check if a part is blocked by FPI
    const isBlockedByFpi = (part: any) => {
        if (fpiStatus.status === 'not_required' || fpiStatus.status === 'passed') {
            return false;
        }
        // In pending or failed state, all parts except the first piece candidate are blocked
        return part.id !== fpiStatus.firstPiecePart?.id;
    };

    // Check if a part is the first piece candidate
    const isFirstPieceCandidate = (part: any) => {
        return fpiStatus.status !== 'not_required' &&
               fpiStatus.firstPiecePart?.id === part.id;
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
            {/* FPI Status Banner */}
            {fpiStatus.status !== 'not_required' && !showQaForm && (
                <div className={`rounded-lg p-3 border ${
                    fpiStatus.status === 'passed'
                        ? 'bg-green-500/10 border-green-500/50'
                        : fpiStatus.status === 'failed'
                        ? 'bg-red-500/10 border-red-500/50'
                        : 'bg-amber-500/10 border-amber-500/50'
                }`}>
                    <div className="flex items-center gap-3">
                        {fpiStatus.status === 'passed' ? (
                            <ShieldCheck className="h-5 w-5 text-green-600" />
                        ) : fpiStatus.status === 'failed' ? (
                            <AlertTriangle className="h-5 w-5 text-red-600" />
                        ) : (
                            <Lock className="h-5 w-5 text-amber-600" />
                        )}
                        <div className="flex-1">
                            <p className="font-medium text-sm">
                                First Piece Inspection {fpiStatus.status === 'passed' ? 'Passed' : fpiStatus.status === 'failed' ? 'Failed' : 'Required'}
                            </p>
                            <p className="text-xs text-muted-foreground">
                                {fpiStatus.status === 'passed' ? (
                                    'All parts can now proceed through this step.'
                                ) : fpiStatus.status === 'failed' ? (
                                    'FPI failed. Re-inspect or fix setup before other parts can proceed.'
                                ) : (
                                    `Part ${fpiStatus.firstPiecePart?.ERP_id || 'TBD'} must pass inspection before other parts can proceed.`
                                )}
                            </p>
                        </div>
                        {fpiStatus.status !== 'passed' && fpiStatus.firstPiecePart && (
                            <Badge variant={fpiStatus.status === 'failed' ? 'destructive' : 'secondary'}>
                                {parts.filter(p => p.id !== fpiStatus.firstPiecePart?.id).length} blocked
                            </Badge>
                        )}
                    </div>
                </div>
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
                                            disabled={isBlockedByFpi(part)}
                                        >
                                            <div className="flex items-center gap-2">
                                                <span className={isBlockedByFpi(part) ? 'text-muted-foreground' : ''}>
                                                    {part.ERP_id} - {part.part_status?.replace('_', ' ')}
                                                </span>
                                                {isFirstPieceCandidate(part) && (
                                                    <Badge variant="outline" className="text-xs bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200">
                                                        First Piece
                                                    </Badge>
                                                )}
                                                {isBlockedByFpi(part) && (
                                                    <Badge variant="secondary" className="text-xs">
                                                        <Lock className="h-3 w-3 mr-1" />
                                                        Waiting FPI
                                                    </Badge>
                                                )}
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
                            {isFirstPieceCandidate(selectedPart) && (
                                <Badge variant="outline" className="text-xs bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200">
                                    <ShieldCheck className="h-3 w-3 mr-1" />
                                    First Piece Inspection
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