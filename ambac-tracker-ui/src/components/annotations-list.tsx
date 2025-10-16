import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AlertTriangle, ChevronDown, List } from "lucide-react";

interface Annotation {
    id?: number;
    defect_type?: string | null;
    severity?: string | null;
    notes?: string;
}

interface AnnotationsListProps {
    annotations: Annotation[];
    selectedIdx: number | null;
    expanded: boolean;
    onToggleExpanded: () => void;
    onAnnotationClick: (index: number) => void;
}

export function AnnotationsList({
    annotations,
    selectedIdx,
    expanded,
    onToggleExpanded,
    onAnnotationClick
}: AnnotationsListProps) {
    const getSeverityBadgeVariant = (severity?: string | null) => {
        switch (severity) {
            case "critical": return "destructive";
            case "high": return "destructive";
            case "medium": return "secondary";
            case "low": return "outline";
            default: return "outline";
        }
    };

    return (
        <>
            {/* Floating List Button */}
            <div className="absolute bottom-4 left-4">
                <Button
                    onClick={onToggleExpanded}
                    className="rounded-full w-12 h-12 shadow-lg"
                    variant={annotations.length > 0 ? "default" : "secondary"}
                >
                    <List className="h-5 w-5" />
                    {annotations.length > 0 && (
                        <Badge
                            className="absolute -top-2 -right-2 w-6 h-6 rounded-full p-0 flex items-center justify-center text-xs"
                            variant="destructive"
                        >
                            {annotations.length}
                        </Badge>
                    )}
                </Button>
            </div>

            {/* Bottom Sheet */}
            {expanded && (
                <div className="absolute bottom-0 left-0 right-0 bg-background border-t rounded-t-lg shadow-lg max-h-48 sm:max-h-64 overflow-hidden z-10">
                    <div
                        className="flex items-center justify-between p-4 border-b cursor-pointer"
                        onClick={onToggleExpanded}
                    >
                        <div className="flex items-center gap-2">
                            <h3 className="font-semibold">Annotations</h3>
                            <Badge variant="secondary">{annotations.length}</Badge>
                        </div>
                        <ChevronDown className="h-4 w-4" />
                    </div>
                    <div className="overflow-y-auto max-h-32 sm:max-h-48 p-4 space-y-2">
                        {annotations.length === 0 ? (
                            <div className="text-center py-6 text-sm text-muted-foreground">
                                <AlertTriangle className="h-6 w-6 mx-auto mb-2 opacity-50" />
                                No defects marked yet
                            </div>
                        ) : (
                            annotations.map((annotation, idx) => (
                                <div
                                    key={idx}
                                    className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                                        idx === selectedIdx
                                            ? 'border-primary bg-primary/5'
                                            : 'border-border hover:border-primary/50'
                                    }`}
                                    onClick={() => onAnnotationClick(idx)}
                                >
                                    <div className="flex items-center justify-between mb-1">
                                        <span className="font-medium text-sm">
                                            {annotation.defect_type || "Unknown"}
                                        </span>
                                        <Badge variant={getSeverityBadgeVariant(annotation.severity)} className="text-xs">
                                            {annotation.severity || "N/A"}
                                        </Badge>
                                    </div>
                                    {annotation.notes && (
                                        <p className="text-xs text-muted-foreground line-clamp-1">
                                            {annotation.notes}
                                        </p>
                                    )}
                                </div>
                            ))
                        )}
                    </div>
                </div>
            )}
        </>
    );
}
