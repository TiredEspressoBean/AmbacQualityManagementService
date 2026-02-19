import {type ThreeEvent} from "@react-three/fiber";
import {useState, useMemo} from "react";
import {Button} from "@/components/ui/button";
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from "@/components/ui/select";
import {Textarea} from "@/components/ui/textarea";
import {Label} from "@/components/ui/label";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle
} from "@/components/ui/dialog";
import {Edit3, Navigation, Save, Trash2, Loader2, AlertTriangle} from "lucide-react";
import {Badge} from "@/components/ui/badge";
import {toast} from "sonner";
import {ThreeDModelViewer} from "@/components/three-d-model-viewer";
import {AnnotationPoint} from "@/components/annotation-point";
import {AnnotationsList} from "@/components/annotations-list";
import {useCreateHeatMapAnnotation} from "@/hooks/useCreateHeatMapAnnotation";
import {useUpdateHeatMapAnnotation} from "@/hooks/useUpdateHeatMapAnnotation";
import {useDeleteHeatMapAnnotation} from "@/hooks/useDeleteHeatMapAnnotation";
import {useRetrieveThreeDModel} from "@/hooks/useRetrieveThreeDModel";
import {useQualityReports} from "@/hooks/useQualityReports";
import {useRetrieveErrorTypes} from "@/hooks/useRetrieveErrorTypes";
import {useRetrieveHeatMapAnnotations} from "@/hooks/useRetrieveHeatMapAnnotations";
import { useParams } from "@tanstack/react-router";

// Helper to normalize media URLs to relative paths (for Vite proxy to work)
function normalizeMediaUrl(url: string | undefined | null): string | undefined {
    if (!url) return undefined;
    try {
        const parsed = new URL(url, window.location.origin);
        // If it's a media URL, return just the path (relative)
        if (parsed.pathname.startsWith('/media/')) {
            return parsed.pathname;
        }
        // If it's already relative or different, return as-is
        return url;
    } catch {
        // If URL parsing fails, return as-is
        return url;
    }
}

const SEVERITY_LEVELS = ["low", "medium", "high", "critical"];

interface LocalAnnotation {
    id?: number; // ID if it's an existing annotation from the backend
    position_x: number;
    position_y: number;
    position_z: number;
    defect_type: string;
    severity: string;
    notes: string;
    isExisting?: boolean; // Flag to track if this came from the backend
}

interface PartAnnotatorProps {
    modelId: string;
    partId: string;
    workOrderId?: string;
    qualityReportIds?: string[];
    className?: string;
    showHeader?: boolean;
    startExpanded?: boolean;
    onSaveComplete?: () => void;
}

export function PartAnnotator({
                                  modelId: propsModelId, partId: propsPartId, workOrderId, qualityReportIds = [], className = "", showHeader = true, startExpanded = true, onSaveComplete,
                              }: PartAnnotatorProps) {
    // Get route params (if navigated via route) and merge with props
    const routeParams = useParams({ strict: false }) as { modelId?: string; partId?: string };
    const modelId = propsModelId ?? routeParams.modelId ?? "";
    const partId = propsPartId ?? routeParams.partId ?? "";

    // Fetch the 3D model data
    const { data: modelData, isLoading: isLoadingModel, error: modelError } = useRetrieveThreeDModel(modelId);

    console.log('[PartAnnotator] State:', { modelId, isLoadingModel, hasData: !!modelData, error: modelError });
    console.log('[PartAnnotator] Model data:', modelData);

    const [annotations, setAnnotations] = useState<LocalAnnotation[]>([]);
    const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
    const [selectedReportIds, setSelectedReportIds] = useState<string[]>([]);
    const [mode, setMode] = useState<"navigate" | "annotate">("annotate");
    const [isLoading, setIsLoading] = useState(true);
    const [showEditDialog, setShowEditDialog] = useState(false);
    const [annotationsExpanded, setAnnotationsExpanded] = useState(startExpanded);
    const [isSaving, setIsSaving] = useState(false);

    // Count of new annotations (not loaded from previous reports)
    const newAnnotationsCount = annotations.filter(a => !a.isExisting && !a.id).length;

    // Fetch existing annotations for the provided quality reports
    const { data: existingAnnotationsData } = useRetrieveHeatMapAnnotations({
        queries: {
            quality_reports__in: qualityReportIds.join(','),
            part: partId,
            model: modelId,
            limit: 1000,
        },
    }, {
        enabled: qualityReportIds.length > 0,
    });

    // Load existing annotations into state when data arrives
    useMemo(() => {
        if (existingAnnotationsData?.results && annotations.length === 0) {
            const existingAnns: LocalAnnotation[] = existingAnnotationsData.results.map(ann => ({
                id: ann.id,
                position_x: ann.position_x,
                position_y: ann.position_y,
                position_z: ann.position_z,
                defect_type: ann.defect_type || "",
                severity: ann.severity || "low",
                notes: ann.notes || "",
                isExisting: true,
            }));
            setAnnotations(existingAnns);
        }
    }, [existingAnnotationsData]);

    // Fetch failed quality reports for this work order
    const { data: qualityReportsData, isLoading: isLoadingReports } = useQualityReports(
        { queries: { part__work_order: workOrderId, status: 'FAIL', limit: 100 } },
        { enabled: !!workOrderId }
    );

    // Fetch all error types to check requires_3d_annotation
    const { data: errorTypesData } = useRetrieveErrorTypes({
        limit: 1000
    });

    // Filter quality reports to only those with error types requiring 3D annotation
    const reportsRequiringAnnotation = useMemo(() => {
        if (!qualityReportsData?.results || !errorTypesData?.results) return [];

        return qualityReportsData.results.filter(report => {
            if (!report.errors || report.errors.length === 0) return false;

            // Check if ANY of the report's error types require 3D annotation
            return report.errors.some(errorId => {
                const errorType = errorTypesData.results.find(et => et.id === errorId);
                return errorType?.requires_3d_annotation === true;
            });
        });
    }, [qualityReportsData, errorTypesData]);

    // Get available error types from selected reports (only those requiring 3D annotation)
    const availableErrorTypes = useMemo(() => {
        if (!errorTypesData?.results) return [];

        // If reports are selected, filter to only error types from those reports
        if (workOrderId && selectedReportIds.length > 0) {
            const selectedReports = reportsRequiringAnnotation.filter(r => selectedReportIds.includes(r.id));
            const errorTypeIds = new Set<string>();

            selectedReports.forEach(report => {
                report.errors?.forEach(errorId => {
                    const errorType = errorTypesData.results.find(et => et.id === errorId);
                    if (errorType?.requires_3d_annotation) {
                        errorTypeIds.add(errorId);
                    }
                });
            });

            return errorTypesData.results.filter(et => errorTypeIds.has(et.id));
        }

        // Otherwise, show all error types that require 3D annotation
        return errorTypesData.results.filter(et => et.requires_3d_annotation === true);
    }, [selectedReportIds, reportsRequiringAnnotation, errorTypesData, workOrderId]);

    // API mutations
    const createAnnotation = useCreateHeatMapAnnotation();
    const updateAnnotation = useUpdateHeatMapAnnotation();
    const deleteAnnotation = useDeleteHeatMapAnnotation();

    const handleClick = (e: ThreeEvent<MouseEvent>) => {
        if (mode !== "annotate") return;

        // Don't allow adding annotations if no reports are selected
        if (workOrderId && selectedReportIds.length === 0) {
            toast.error("Please select at least one quality report first");
            return;
        }

        const point = e.point;

        const newAnnotation: LocalAnnotation = {
            position_x: point.x,
            position_y: point.y,
            position_z: point.z,
            defect_type: availableErrorTypes.length > 0 ? availableErrorTypes[0].error_name : "",
            severity: SEVERITY_LEVELS[0],
            notes: "",
        };

        setAnnotations([...annotations, newAnnotation]);
    };

    const handleUpdateAnnotation = async (field: string, value: string) => {
        if (selectedIdx === null) return;

        const annotation = annotations[selectedIdx];

        // Update local state immediately for responsiveness
        const updated = [...annotations];
        updated[selectedIdx] = {...updated[selectedIdx], [field]: value};
        setAnnotations(updated);

        // If this is an existing annotation (has an id), persist to API
        if (annotation.id) {
            try {
                await updateAnnotation.mutateAsync({
                    id: annotation.id,
                    data: { [field]: value },
                });
            } catch (error) {
                console.error("Failed to update annotation:", error);
                toast.error("Failed to save changes");
                // Revert local state on error
                setAnnotations(annotations);
            }
        }
    };

    const handleDeleteAnnotation = async () => {
        if (selectedIdx === null) return;

        const annotation = annotations[selectedIdx];

        // If this is an existing annotation (has an id), delete from API
        if (annotation.id) {
            try {
                await deleteAnnotation.mutateAsync(annotation.id);
                toast.success("Annotation deleted");
            } catch (error) {
                console.error("Failed to delete annotation:", error);
                toast.error("Failed to delete annotation");
                return; // Don't remove from local state if API call failed
            }
        }

        // Remove from local state
        const updated = annotations.filter((_, idx) => idx !== selectedIdx);
        setAnnotations(updated);
        setSelectedIdx(null);
    };

    const handleSaveAll = async () => {
        // Only save new annotations (not ones loaded from previous reports)
        const newAnnotations = annotations.filter(a => !a.isExisting && !a.id);

        if (newAnnotations.length === 0) {
            toast.error("No new annotations to save");
            return;
        }

        if (workOrderId && selectedReportIds.length === 0) {
            toast.error("Please select at least one quality report to link annotations to");
            return;
        }

        setIsSaving(true);
        let successCount = 0;
        let failCount = 0;

        const reportsToLink = workOrderId ? selectedReportIds : qualityReportIds;

        try {
            for (const annotation of newAnnotations) {
                try {
                    await createAnnotation.mutateAsync({
                        model: modelId,
                        part: partId,
                        quality_reports: reportsToLink,
                        position_x: annotation.position_x,
                        position_y: annotation.position_y,
                        position_z: annotation.position_z,
                        defect_type: annotation.defect_type,
                        severity: annotation.severity,
                        notes: annotation.notes,
                    });
                    successCount++;
                } catch (error) {
                    console.error("Failed to create annotation:", error);
                    failCount++;
                }
            }

            if (successCount > 0) {
                toast.success(`Successfully saved ${successCount} annotation${successCount > 1 ? 's' : ''}`);
                setAnnotations([]);
                setSelectedReportIds([]);
                onSaveComplete?.();
            }

            if (failCount > 0) {
                toast.error(`Failed to save ${failCount} annotation${failCount > 1 ? 's' : ''}`);
            }
        } finally {
            setIsSaving(false);
        }
    };

    // Loading state
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

    // Error state
    if (modelError || !modelData) {
        console.error('[PartAnnotator] Error details:', modelError);
        return (
            <div className="flex items-center justify-center h-screen">
                <div className="text-center p-8 max-w-md">
                    <AlertTriangle className="h-12 w-12 mx-auto mb-4 text-destructive" />
                    <h3 className="text-lg font-semibold mb-2">Failed to Load Model</h3>
                    <p className="text-sm text-muted-foreground mb-4">
                        {modelError ? String(modelError) : "Model not found"}
                    </p>
                    <p className="text-xs text-muted-foreground font-mono">
                        Model ID: {modelId}
                    </p>
                    <p className="text-xs text-muted-foreground mt-2">
                        Check browser console for details
                    </p>
                </div>
            </div>
        );
    }

    const modelUrl = normalizeMediaUrl(modelData.file);
    console.log('[PartAnnotator] Model URL:', modelUrl);

    return (<div
            className={`relative flex flex-col ${showHeader ? 'h-[calc(100vh-8rem)]' : 'h-full'} w-full bg-background overflow-hidden ${className}`}>
            {/* Header */}
            {showHeader && (<div className="flex items-center justify-between p-4 border-b bg-card shrink-0">
                    <div>
                        <h1 className="text-xl font-semibold">Part Annotator</h1>
                        <p className="text-sm text-muted-foreground">
                            {newAnnotationsCount} new annotation{newAnnotationsCount !== 1 ? 's' : ''} ready to save
                            {annotations.length > newAnnotationsCount && ` (${annotations.length - newAnnotationsCount} existing)`}
                        </p>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button
                            onClick={handleSaveAll}
                            disabled={isSaving || newAnnotationsCount === 0}
                            variant="default"
                            className="gap-2"
                        >
                            <Save className="h-4 w-4"/>
                            {isSaving ? "Saving..." : `Save New (${newAnnotationsCount})`}
                        </Button>
                        <Select value={mode} onValueChange={(value: any) => setMode(value)}>
                            <SelectTrigger className="w-40">
                                <SelectValue/>
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="annotate">
                                    <div className="flex items-center gap-2">
                                        <Edit3 className="h-4 w-4"/>
                                        Annotate Defects
                                    </div>
                                </SelectItem>
                                <SelectItem value="navigate">
                                    <div className="flex items-center gap-2">
                                        <Navigation className="h-4 w-4"/>
                                        Navigate View
                                    </div>
                                </SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                </div>)}

            {/* Quality Report Selector (only shown when workOrderId is provided) */}
            {workOrderId && (
                <div className="px-4 py-3 border-b bg-muted/30">
                    {isLoadingReports ? (
                        <div className="flex items-center gap-2">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            <span className="text-sm text-muted-foreground">Loading quality reports...</span>
                        </div>
                    ) : reportsRequiringAnnotation.length === 0 ? (
                        <div className="text-sm text-muted-foreground">
                            No quality reports requiring 3D annotation found for this work order
                        </div>
                    ) : (
                        <div className="flex items-center gap-3">
                            <Label className="text-sm font-medium shrink-0">Quality Report:</Label>
                            <Select
                                value={selectedReportIds[0]?.toString() || ""}
                                onValueChange={(value) => setSelectedReportIds(value ? [value] : [])}
                            >
                                <SelectTrigger className="flex-1">
                                    <SelectValue placeholder="Select a report to annotate..." />
                                </SelectTrigger>
                                <SelectContent>
                                    {reportsRequiringAnnotation.map(report => {
                                        const errorNames = report.errors
                                            ?.map(errorId => errorTypesData?.results.find(et => et.id === errorId)?.error_name)
                                            .filter((name): name is string => name !== undefined && name !== null)
                                            .join(", ") || "No errors";

                                        return (
                                            <SelectItem key={report.id} value={report.id.toString()}>
                                                <div className="flex items-center gap-2">
                                                    <span>Report #{report.id}</span>
                                                    <Badge variant="destructive" className="text-xs">
                                                        {report.status}
                                                    </Badge>
                                                    <span className="text-muted-foreground">- {errorNames}</span>
                                                </div>
                                            </SelectItem>
                                        );
                                    })}
                                </SelectContent>
                            </Select>
                        </div>
                    )}
                </div>
            )}

            {/* Compact Save Bar (only shown in embedded mode when there are new annotations) */}
            {!showHeader && newAnnotationsCount > 0 && (
                <div className="px-4 py-2 border-b bg-card flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <span className="text-sm font-medium">
                            {newAnnotationsCount} new annotation{newAnnotationsCount !== 1 ? 's' : ''} ready
                        </span>
                        <Select value={mode} onValueChange={(value: any) => setMode(value)}>
                            <SelectTrigger className="w-32 h-8 text-xs">
                                <SelectValue/>
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="annotate">
                                    <div className="flex items-center gap-2">
                                        <Edit3 className="h-3 w-3"/>
                                        Annotate
                                    </div>
                                </SelectItem>
                                <SelectItem value="navigate">
                                    <div className="flex items-center gap-2">
                                        <Navigation className="h-3 w-3"/>
                                        Navigate
                                    </div>
                                </SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                    <Button
                        onClick={handleSaveAll}
                        disabled={isSaving}
                        size="sm"
                        className="gap-1"
                    >
                        <Save className="h-3 w-3"/>
                        {isSaving ? "Saving..." : `Save New (${newAnnotationsCount})`}
                    </Button>
                </div>
            )}

            {/* 3D Viewport */}
            <div className="flex-1 relative min-h-0">
                <ThreeDModelViewer
                    modelUrl={modelUrl}
                    mode={mode}
                    onModelClick={handleClick}
                    isLoading={isLoading}
                    onLoadingComplete={() => setIsLoading(false)}
                    instructions={mode === "annotate" ? "Tap model to add defect" : "WASD move • Space/Ctrl up/down • QE yaw • RF pitch • ZC roll"}
                >
                    {annotations.map((annotation, idx) => (<AnnotationPoint
                            key={idx}
                            position={[annotation.position_x, annotation.position_y, annotation.position_z]}
                            selected={idx === selectedIdx}
                            severity={annotation.severity}
                            mode={mode}
                            onClick={() => {
                                setSelectedIdx(idx);
                                setShowEditDialog(true);
                            }}
                        />))}
                </ThreeDModelViewer>

                {/* Annotations List */}
                <AnnotationsList
                    annotations={annotations}
                    selectedIdx={selectedIdx}
                    expanded={annotationsExpanded}
                    onToggleExpanded={() => setAnnotationsExpanded(!annotationsExpanded)}
                    onAnnotationClick={(idx) => {
                        setSelectedIdx(idx);
                        setShowEditDialog(true);
                        setAnnotationsExpanded(false);
                    }}
                />
            </div>

            {/* Edit Annotation Dialog */}
            <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
                <DialogContent className="w-[95vw] max-w-md">
                    <DialogHeader>
                        <DialogTitle>Edit Defect Annotation</DialogTitle>
                        <DialogDescription>
                            Update the defect details and severity level
                        </DialogDescription>
                    </DialogHeader>

                    {selectedIdx !== null && annotations[selectedIdx] && (<div className="space-y-4 py-4">
                            <div>
                                <Label>Error Type</Label>
                                <Select
                                    value={annotations[selectedIdx].defect_type}
                                    onValueChange={(value) => handleUpdateAnnotation("defect_type", value)}
                                >
                                    <SelectTrigger className="mt-2">
                                        <SelectValue/>
                                    </SelectTrigger>
                                    <SelectContent>
                                        {availableErrorTypes.length > 0 ? (
                                            availableErrorTypes.map((type) => (
                                                <SelectItem key={type.id} value={type.error_name}>
                                                    {type.error_name}
                                                </SelectItem>
                                            ))
                                        ) : (
                                            <div className="p-2 text-sm text-muted-foreground text-center">
                                                {workOrderId
                                                    ? "Select a quality report to see available error types"
                                                    : "No error types require 3D annotation"
                                                }
                                            </div>
                                        )}
                                    </SelectContent>
                                </Select>
                            </div>

                            <div>
                                <Label>Severity Level</Label>
                                <Select
                                    value={annotations[selectedIdx].severity}
                                    onValueChange={(value) => handleUpdateAnnotation("severity", value)}
                                >
                                    <SelectTrigger className="mt-2">
                                        <SelectValue/>
                                    </SelectTrigger>
                                    <SelectContent>
                                        {SEVERITY_LEVELS.map((level) => (<SelectItem key={level} value={level}>
                                                {level.charAt(0).toUpperCase() + level.slice(1)}
                                            </SelectItem>))}
                                    </SelectContent>
                                </Select>
                            </div>

                            <div>
                                <Label>Notes</Label>
                                <Textarea
                                    value={annotations[selectedIdx].notes}
                                    onChange={(e) => handleUpdateAnnotation("notes", e.target.value)}
                                    placeholder="Describe the defect in detail..."
                                    className="mt-2 min-h-[100px]"
                                />
                            </div>
                        </div>)}

                    <DialogFooter className="flex-col gap-2 sm:flex-row">
                        <Button
                            onClick={() => {
                                handleDeleteAnnotation();
                                setShowEditDialog(false);
                            }}
                            variant="destructive"
                            className="w-full sm:w-auto"
                        >
                            <Trash2 className="h-4 w-4 mr-2"/>
                            Delete
                        </Button>
                        <Button
                            onClick={() => setShowEditDialog(false)}
                            className="w-full sm:w-auto"
                        >
                            Done
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>);
}
