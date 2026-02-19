import { useState, useMemo } from "react";
import { useNavigate } from "@tanstack/react-router";
import { PartAnnotator } from "./PartAnnotator";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Loader2, ArrowLeft, Box, FileText, AlertTriangle } from "lucide-react";
import { useQualityReports } from "@/hooks/useQualityReports";
import { useRetrieveErrorTypes } from "@/hooks/useRetrieveErrorTypes";
import { useRetrieveThreeDModels } from "@/hooks/useRetrieveThreeDModels";
import { Checkbox } from "@/components/ui/checkbox";
import { api } from "@/lib/api/generated";
import { useQuery } from "@tanstack/react-query";

export function AnnotatorPage() {
    const navigate = useNavigate();
    const [selectedReportIds, setSelectedReportIds] = useState<string[]>([]);
    const [startAnnotating, setStartAnnotating] = useState(false);

    // Fetch all quality reports
    const { data: qualityReportsData, isLoading: isLoadingReports } = useQualityReports({
        queries: {
            limit: 1000,
            ordering: "-created_at" // Most recent first
        }
    });

    // Fetch error types to check requires_3d_annotation
    const { data: errorTypesData } = useRetrieveErrorTypes({
        limit: 1000
    });

    // Filter quality reports to only those with error types requiring 3D annotation
    const reportsRequiringAnnotation = useMemo(() => {
        if (!qualityReportsData?.results || !errorTypesData?.results) return [];

        return qualityReportsData.results.filter(report => {
            if (!report.errors || report.errors.length === 0) return false;

            return report.errors.some(errorId => {
                const errorType = errorTypesData.results.find(et => et.id === errorId);
                return errorType?.requires_3d_annotation === true;
            });
        });
    }, [qualityReportsData, errorTypesData]);

    // Get the part from selected reports (should all be same part)
    const selectedReports = useMemo(() => {
        return reportsRequiringAnnotation.filter(r => selectedReportIds.includes(r.id));
    }, [reportsRequiringAnnotation, selectedReportIds]);

    const partId = selectedReports.length > 0 ? selectedReports[0].part : null;

    // Fetch part details to get part type
    const { data: partData } = useQuery({
        queryKey: ["part", partId],
        queryFn: () => api.api_Parts_retrieve({ params: { id: partId! } }),
        enabled: !!partId,
    });

    // Fetch 3D model for the part type
    const { data: modelsData, isLoading: isLoadingModel } = useRetrieveThreeDModels({
        queries: {
            part_type: partData?.part_type,
            archived: false,
            limit: 1,
        },
    }, {
        enabled: !!partData?.part_type,
    });

    const model3D = modelsData?.count && modelsData.count > 0 ? modelsData.results[0] : null;

    const handleToggleReport = (reportId: string) => {
        setSelectedReportIds(prev =>
            prev.includes(reportId)
                ? prev.filter(id => id !== reportId)
                : [...prev, reportId]
        );
    };

    // Show annotator if reports are selected and we have model data
    if (startAnnotating && selectedReportIds.length > 0 && partId) {
        if (isLoadingModel) {
            return (
                <div className="flex items-center justify-center h-screen">
                    <div className="flex flex-col items-center gap-4">
                        <Loader2 className="h-8 w-8 animate-spin text-primary" />
                        <p className="text-muted-foreground">Loading 3D model...</p>
                    </div>
                </div>
            );
        }

        if (!model3D) {
            return (
                <div className="flex items-center justify-center h-screen">
                    <div className="text-center p-8 max-w-md">
                        <AlertTriangle className="h-12 w-12 mx-auto mb-4 text-destructive" />
                        <h3 className="text-lg font-semibold mb-2">No 3D Model Found</h3>
                        <p className="text-sm text-muted-foreground mb-4">
                            No 3D model is available for this part type.
                        </p>
                        <Button onClick={() => setStartAnnotating(false)} variant="outline">
                            <ArrowLeft className="h-4 w-4 mr-2" />
                            Back to Reports
                        </Button>
                    </div>
                </div>
            );
        }

        return (
            <div className="h-screen flex flex-col">
                <div className="p-4 border-b bg-card shrink-0 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                                setStartAnnotating(false);
                            }}
                        >
                            <ArrowLeft className="h-4 w-4 mr-2" />
                            Back to Reports
                        </Button>
                        <div>
                            <h2 className="text-sm font-medium">
                                {model3D?.name || `Model #${model3D?.id}`}
                            </h2>
                            <p className="text-xs text-muted-foreground">
                                Part: {partData?.serial_number || `#${partId}`} • {selectedReportIds.length} report{selectedReportIds.length > 1 ? 's' : ''}
                            </p>
                        </div>
                    </div>
                </div>

                <div className="flex-1 min-h-0">
                    <PartAnnotator
                        modelId={model3D.id}
                        partId={partId}
                        qualityReportIds={selectedReportIds}
                        showHeader={true}
                        startExpanded={true}
                        onSaveComplete={() => {
                            console.log("Annotations saved successfully");
                            // Optionally navigate back to selection
                            setStartAnnotating(false);
                            setSelectedReportIds([]);
                        }}
                    />
                </div>
            </div>
        );
    }

    // Show quality report selection screen
    return (
        <div className="container max-w-4xl mx-auto py-8 px-4">
            <div className="flex items-center gap-4 mb-6">
                <Button variant="ghost" onClick={() => navigate({ to: "/" })}>
                    <ArrowLeft className="h-4 w-4 mr-2" />
                    Back
                </Button>
                <div>
                    <h1 className="text-3xl font-bold flex items-center gap-2">
                        <Box className="h-8 w-8" />
                        3D Part Annotator
                    </h1>
                    <p className="text-muted-foreground mt-1">
                        Add 3D annotations to quality reports
                    </p>
                </div>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>Select Quality Reports</CardTitle>
                    <CardDescription>
                        Choose quality reports that require 3D defect annotations
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    {isLoadingReports ? (
                        <div className="flex items-center gap-2 p-4">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            <span className="text-sm text-muted-foreground">Loading quality reports...</span>
                        </div>
                    ) : reportsRequiringAnnotation.length === 0 ? (
                        <div className="text-center p-8">
                            <FileText className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                            <p className="text-sm text-muted-foreground">
                                No quality reports requiring 3D annotation found
                            </p>
                        </div>
                    ) : (
                        <>
                            <div className="border rounded-lg divide-y max-h-96 overflow-y-auto">
                                {reportsRequiringAnnotation.map(report => {
                                    const errorNames = report.errors
                                        ?.map(errorId => errorTypesData?.results.find(et => et.id === errorId)?.error_name)
                                        .filter((name): name is string => name !== undefined && name !== null)
                                        .join(", ") || "No errors";

                                    return (
                                        <div
                                            key={report.id}
                                            className="flex items-center space-x-3 p-3 hover:bg-accent cursor-pointer transition-colors"
                                            onClick={() => handleToggleReport(report.id)}
                                        >
                                            <Checkbox
                                                checked={selectedReportIds.includes(report.id)}
                                                onCheckedChange={() => handleToggleReport(report.id)}
                                            />
                                            <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2 mb-1">
                                                    <span className="text-sm font-medium">Report #{report.id}</span>
                                                    <span className={`text-xs px-2 py-0.5 rounded ${
                                                        report.status === 'PASS' ? 'bg-green-100 text-green-800' :
                                                        report.status === 'FAIL' ? 'bg-red-100 text-red-800' :
                                                        'bg-yellow-100 text-yellow-800'
                                                    }`}>
                                                        {report.status}
                                                    </span>
                                                </div>
                                                <p className="text-xs text-muted-foreground">
                                                    {errorNames}
                                                </p>
                                                {report.part_display && (
                                                    <p className="text-xs text-muted-foreground mt-1">
                                                        Part: {report.part_display}
                                                    </p>
                                                )}
                                                {report.created_at && (
                                                    <p className="text-xs text-muted-foreground">
                                                        {new Date(report.created_at).toLocaleDateString()}
                                                    </p>
                                                )}
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>

                            {selectedReportIds.length > 0 && (
                                <div className="flex items-center justify-between pt-2">
                                    <p className="text-sm text-muted-foreground">
                                        {selectedReportIds.length} report{selectedReportIds.length > 1 ? 's' : ''} selected
                                    </p>
                                    <Button
                                        onClick={() => setStartAnnotating(true)}
                                        disabled={selectedReportIds.length === 0}
                                    >
                                        <Box className="h-4 w-4 mr-2" />
                                        Start Annotating
                                    </Button>
                                </div>
                            )}
                        </>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}