import {type ThreeEvent} from "@react-three/fiber";
import {useState} from "react";
import {Button} from "@/components/ui/button";
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from "@/components/ui/select";
import {Textarea} from "@/components/ui/textarea";
import {Label} from "@/components/ui/label";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle
} from "@/components/ui/dialog";
import {Edit3, Navigation, Save, Trash2} from "lucide-react";
import {toast} from "sonner";
import {ThreeDModelViewer} from "@/components/three-d-model-viewer";
import {AnnotationPoint} from "@/components/annotation-point";
import {AnnotationsList} from "@/components/annotations-list";
import {useCreateHeatMapAnnotation} from "@/hooks/useCreateHeatMapAnnotation";

const ERROR_TYPES = ["Crack", "Burn", "Porosity", "Overspray"];
const SEVERITY_LEVELS = ["low", "medium", "high", "critical"];

interface LocalAnnotation {
    position_x: number;
    position_y: number;
    position_z: number;
    defect_type: string;
    severity: string;
    notes: string;
}

interface PartAnnotatorProps {
    modelId: number;
    partId: number;
    modelUrl: string;
    className?: string;
    showHeader?: boolean;
    onSaveComplete?: () => void;
}

export function PartAnnotator({
                                  modelId, partId, modelUrl, className = "", showHeader = true, onSaveComplete,
                              }: PartAnnotatorProps) {
    const [annotations, setAnnotations] = useState<LocalAnnotation[]>([]);
    const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
    const [mode, setMode] = useState<"navigate" | "annotate">("annotate");
    const [isLoading, setIsLoading] = useState(true);
    const [showEditDialog, setShowEditDialog] = useState(false);
    const [annotationsExpanded, setAnnotationsExpanded] = useState(true);
    const [isSaving, setIsSaving] = useState(false);

    // API mutations
    const createAnnotation = useCreateHeatMapAnnotation();

    const handleClick = (e: ThreeEvent<MouseEvent>) => {
        if (mode !== "annotate") return;

        const point = e.point;

        // Add to local state only
        const newAnnotation: LocalAnnotation = {
            position_x: point.x,
            position_y: point.y,
            position_z: point.z,
            defect_type: ERROR_TYPES[0],
            severity: SEVERITY_LEVELS[0],
            notes: "",
        };

        setAnnotations([...annotations, newAnnotation]);
    };

    const handleUpdateAnnotation = (field: string, value: string) => {
        if (selectedIdx === null) return;

        // Update local state only
        const updated = [...annotations];
        updated[selectedIdx] = {...updated[selectedIdx], [field]: value};
        setAnnotations(updated);
    };

    const handleDeleteAnnotation = () => {
        if (selectedIdx === null) return;

        // Remove from local state only
        const updated = annotations.filter((_, idx) => idx !== selectedIdx);
        setAnnotations(updated);
        setSelectedIdx(null);
    };

    const handleSaveAll = async () => {
        if (annotations.length === 0) {
            toast.error("No annotations to save");
            return;
        }

        setIsSaving(true);
        let successCount = 0;
        let failCount = 0;

        try {
            // Create all annotations sequentially
            for (const annotation of annotations) {
                try {
                    await createAnnotation.mutateAsync({
                        model: modelId, part: partId, ...annotation,
                    });
                    successCount++;
                } catch (error) {
                    console.error("Failed to create annotation:", error);
                    failCount++;
                }
            }

            if (successCount > 0) {
                toast.success(`Successfully saved ${successCount} annotation${successCount > 1 ? 's' : ''}`);
                // Clear local annotations after successful save
                setAnnotations([]);
                onSaveComplete?.();
            }

            if (failCount > 0) {
                toast.error(`Failed to save ${failCount} annotation${failCount > 1 ? 's' : ''}`);
            }
        } finally {
            setIsSaving(false);
        }
    };

    return (<div
            className={`relative flex flex-col h-[calc(100vh-8rem)] w-full bg-background overflow-hidden ${className}`}>
            {/* Header */}
            {showHeader && (<div className="flex items-center justify-between p-4 border-b bg-card shrink-0">
                    <div>
                        <h1 className="text-xl font-semibold">Part Annotator</h1>
                        <p className="text-sm text-muted-foreground">
                            {annotations.length} annotation{annotations.length !== 1 ? 's' : ''} ready to save
                        </p>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button
                            onClick={handleSaveAll}
                            disabled={isSaving || annotations.length === 0}
                            variant="default"
                            className="gap-2"
                        >
                            <Save className="h-4 w-4"/>
                            {isSaving ? "Saving..." : `Save All (${annotations.length})`}
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
                                        {ERROR_TYPES.map((type) => (<SelectItem key={type} value={type}>
                                                {type}
                                            </SelectItem>))}
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
