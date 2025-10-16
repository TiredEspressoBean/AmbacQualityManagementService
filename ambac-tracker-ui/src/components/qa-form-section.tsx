import * as React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { PartQualityForm } from "./part-quality-form";
import { useState } from "react";
import { CheckCircle, AlertTriangle, Clock } from "lucide-react";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";

type QaFormSectionProps = {
    workOrder: any;
    parts: any[];
    isLoadingParts: boolean;
    isBatchProcess: boolean;
};

export function QaFormSection({ workOrder, parts, isLoadingParts, isBatchProcess }: QaFormSectionProps) {
    const [selectedPart, setSelectedPart] = useState<any | null>(null);
    const [showQaForm, setShowQaForm] = useState(false);
    const [currentBatchIndex, setCurrentBatchIndex] = useState(0);
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
            setSelectedPart(parts[currentBatchIndex + 1]);
            setShowQaForm(true);
        } else if (!isBatchProcess) {
            const currentIndex = availableParts.findIndex(p => p.id === selectedPart?.id);
            if (currentIndex >= 0 && currentIndex < availableParts.length - 1) {
                setSelectedPart(availableParts[currentIndex + 1]);
                setShowQaForm(true);
            }
        }
    };

    return (
        <div className="space-y-4">
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
                                setSelectedPart(availableParts[0]);
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
                                    const part = availableParts.find(p => p.id === parseInt(value));
                                    if (part) {
                                        setSelectedPart(part);
                                    }
                                }}
                            >
                                <SelectTrigger className="flex-1 min-w-0">
                                    <SelectValue placeholder="Choose a part..." />
                                </SelectTrigger>
                                <SelectContent>
                                    {availableParts.map((part) => (
                                        <SelectItem key={part.id} value={part.id.toString()}>
                                            {part.ERP_id} - {part.part_status?.replace('_', ' ')}
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
                                setSelectedPart(null);
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
                                setSelectedPart(null);
                            }
                        }}
                    />
                </div>
            )}

        </div>
    );
}