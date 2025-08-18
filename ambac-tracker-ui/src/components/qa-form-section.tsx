import * as React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { PartQualityForm } from "./part-quality-form";
import { useState } from "react";
import { CheckCircle, AlertTriangle, Clock } from "lucide-react";

type QaFormSectionProps = {
    workOrder: any;
    parts: any[];
    isLoadingParts: boolean;
    isBatchProcess: boolean;
};

export function QaFormSection({ workOrder, parts, isLoadingParts, isBatchProcess }: QaFormSectionProps) {
    const [selectedPart, setSelectedPart] = useState<any | null>(null);
    const [showQaForm, setShowQaForm] = useState(false);
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

    return (
        <div className="space-y-6">

            {/* Batch Quality Forms Summary (for batch processes) */}
            {isBatchProcess && parts.length > 0 && (
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            Quality Forms Required
                            <Badge variant="secondary" className="text-sm">
                                {parts.length} forms
                            </Badge>
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                            <div className="flex items-center gap-3">
                                <AlertTriangle className="h-5 w-5 text-blue-600" />
                                <div>
                                    <p className="font-medium text-blue-900">
                                        {parts.length} Quality Assessment{parts.length === 1 ? '' : 's'} Required
                                    </p>
                                    <p className="text-sm text-blue-700 mt-1">
                                        This batch requires {parts.length} quality form{parts.length === 1 ? '' : 's'} to be completed based on sampling rules.
                                    </p>
                                </div>
                            </div>
                        </div>
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            <Button 
                                className="bg-green-600 hover:bg-green-700 h-12"
                                onClick={() => {
                                    setSelectedPart(parts[0]); // Use first part as template
                                    setShowQaForm(true);
                                }}
                            >
                                <CheckCircle className="h-4 w-4 mr-2" />
                                Start Quality Forms
                            </Button>
                            <Button variant="outline" className="h-12">
                                <Clock className="h-4 w-4 mr-2" />
                                View Individual Parts
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Parts List (for non-batch processes or when viewing individual parts) */}
            {!isBatchProcess && (
            <Card>
                <CardHeader>
                    <CardTitle>
                        Parts Requiring QA
                        <span className="text-sm font-normal text-muted-foreground ml-2">
                            ({parts.length} {parts.length === 1 ? 'part' : 'parts'})
                        </span>
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="space-y-3">
                        {parts.map((part: any, index: number) => {
                            const statusColor = 
                                part.part_status === 'COMPLETED' || part.part_status === 'PASSED' ? 'bg-green-100 text-green-800 border-green-200' :
                                part.part_status === 'REWORK_NEEDED' || part.part_status === 'FAILED' ? 'bg-red-100 text-red-800 border-red-200' :
                                part.part_status === 'IN_PROGRESS' ? 'bg-blue-100 text-blue-800 border-blue-200' :
                                'bg-yellow-100 text-yellow-800 border-yellow-200';

                            const isSelectedPart = selectedPart?.id === part.id;

                            return (
                                <div key={part.id} 
                                     className={`flex items-center justify-between p-4 border rounded-lg transition-all cursor-pointer
                                                ${isSelectedPart ? 'ring-2 ring-primary ring-offset-2 bg-primary/5' : 'hover:bg-muted/30'}`}
                                     onClick={() => {
                                         if (!isSelectedPart) {
                                             setSelectedPart(part);
                                             setShowQaForm(false); // Reset form view when selecting new part
                                         }
                                     }}>
                                    <div className="space-y-2 flex-1">
                                        <div className="flex items-center gap-3">
                                            {getStatusIcon(part.part_status)}
                                            <span className="font-medium text-base">{part.ERP_id}</span>
                                            <span className={`px-2 py-1 text-xs rounded border ${statusColor}`}>
                                                {part.part_status?.replace('_', ' ') || 'Pending'}
                                            </span>
                                            {isBatchProcess && (
                                                <span className="text-xs text-muted-foreground bg-muted px-2 py-1 rounded">
                                                    Part {index + 1} of {parts.length}
                                                </span>
                                            )}
                                        </div>
                                        <div className="text-sm text-muted-foreground space-y-1">
                                            <div className="flex items-center gap-1">
                                                <span className="font-medium">Step:</span>
                                                <span>{(part as any).step_name || (part as any).step_description || 'N/A'}</span>
                                            </div>
                                            <div className="flex items-center gap-4">
                                                <span><strong>Process:</strong> {(part as any).process_name || 'N/A'}</span>
                                                <span><strong>Type:</strong> {(part as any).part_type_name || 'N/A'}</span>
                                            </div>
                                        </div>
                                    </div>
                                    
                                    <div className="flex items-center gap-2 ml-4">
                                        {!isBatchProcess && (
                                            <Button 
                                                size="sm"
                                                variant={isSelectedPart ? "default" : "outline"}
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    setSelectedPart(part);
                                                    setShowQaForm(true);
                                                }}
                                            >
                                                {isSelectedPart ? "Selected" : "Start QA"}
                                            </Button>
                                        )}
                                        {isBatchProcess && (
                                            <Button 
                                                size="sm" 
                                                variant="outline"
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    setSelectedPart(part);
                                                    setShowQaForm(true);
                                                }}
                                            >
                                                Individual QA
                                            </Button>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </CardContent>
            </Card>
            )}

            {/* Individual QA Form */}
            {selectedPart && showQaForm && (
                <Card>
                    <CardHeader>
                        <div className="flex items-center justify-between">
                            <CardTitle className="flex items-center gap-2">
                                {isBatchProcess ? "Batch Quality Assessment" : `Quality Assessment - ${selectedPart.ERP_id}`}
                                {isBatchProcess && (
                                    <Badge variant="secondary" className="text-xs">
                                        Batch Form
                                    </Badge>
                                )}
                            </CardTitle>
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
                    </CardHeader>
                    <CardContent>
                        <PartQualityForm 
                            part={selectedPart} 
                            onClose={() => {
                                setShowQaForm(false);
                                setSelectedPart(null);
                                // Optionally refresh parts data here
                            }}
                        />
                    </CardContent>
                </Card>
            )}

            {/* Part Selection Prompt */}
            {selectedPart && !showQaForm && (
                <Card>
                    <CardHeader>
                        <CardTitle>Part Selected - {selectedPart.ERP_id}</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="flex items-center gap-3 p-4 bg-muted/50 rounded-lg">
                            {getStatusIcon(selectedPart.part_status)}
                            <div>
                                <p className="font-medium">
                                    {selectedPart.ERP_id} - {selectedPart.part_status?.replace('_', ' ') || 'Pending'}
                                </p>
                                <p className="text-sm text-muted-foreground">
                                    Step: {selectedPart.step_name || selectedPart.step_description || 'N/A'}
                                </p>
                            </div>
                        </div>
                        
                        <div className="flex gap-3">
                            <Button 
                                onClick={() => setShowQaForm(true)}
                                className="flex-1 h-12"
                            >
                                <CheckCircle className="h-4 w-4 mr-2" />
                                Start Quality Assessment
                            </Button>
                            <Button 
                                variant="outline" 
                                onClick={() => setSelectedPart(null)}
                                className="h-12"
                            >
                                Cancel
                            </Button>
                        </div>
                        
                        <div className="text-sm text-muted-foreground space-y-2 pt-2 border-t">
                            <p><strong>QA Form includes:</strong></p>
                            <ul className="list-disc list-inside space-y-1 ml-4">
                                <li>Operator and machine assignment</li>
                                <li>Step-specific measurements</li>
                                <li>Pass/fail/pending status</li>
                                <li>Notes and observations</li>
                                <li>Automatic spec validation</li>
                            </ul>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* No Selection State */}
            {!selectedPart && !isBatchProcess && (
                <Card>
                    <CardHeader>
                        <CardTitle>Quality Assessment Form</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-center py-8">
                            <Clock className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                            <p className="text-lg font-medium mb-2">Ready for Quality Assessment</p>
                            <p className="text-sm text-muted-foreground">
                                Select a part above to begin quality assessment
                            </p>
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}