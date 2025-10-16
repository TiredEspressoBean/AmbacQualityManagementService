import { useState, useEffect, useMemo } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { ThreeDModelViewer } from "@/components/three-d-model-viewer";
import { AnnotationPoint } from "@/components/annotation-point";
import { AnnotationsList } from "@/components/annotations-list";
import { useRetrieveHeatMapAnnotations } from "@/hooks/useRetrieveHeatMapAnnotations";
import type { HeatMapAnnotations } from "@/lib/api/generated";
import { Loader2 } from "lucide-react";
import * as THREE from "three";

interface HeatMapViewerProps {
    modelId: number;
    partId: number;
    modelUrl: string;
    className?: string;
    showHeader?: boolean;
}

export function HeatMapViewer({
    modelId,
    partId,
    modelUrl,
    className = "",
    showHeader = true,
}: HeatMapViewerProps) {
    const [annotations, setAnnotations] = useState<HeatMapAnnotations[]>([]);
    const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [annotationsExpanded, setAnnotationsExpanded] = useState(true);
    const [useNeutralColor, setUseNeutralColor] = useState(true);
    const [heatmapEnabled, setHeatmapEnabled] = useState(true);
    const [heatmapRadius, setHeatmapRadius] = useState(0.5);
    const [heatmapIntensity, setHeatmapIntensity] = useState(1.0);

    // Fetch existing annotations
    const { data: annotationsData, isLoading: isFetchingAnnotations } = useRetrieveHeatMapAnnotations({
        queries: {
            model: modelId,
            part: partId,
        },
    });

    // Load annotations when data arrives
    useEffect(() => {
        if (annotationsData?.results) {
            setAnnotations(annotationsData.results);
        }
    }, [annotationsData]);

    // Count annotations by severity
    const severityCounts = annotations.reduce((acc, annotation) => {
        const severity = annotation.severity || "unknown";
        acc[severity] = (acc[severity] || 0) + 1;
        return acc;
    }, {} as Record<string, number>);

    // Convert annotation positions to Vector3 array
    const heatmapPositions = useMemo(() => {
        return annotations.map(
            (a) => new THREE.Vector3(a.position_x, a.position_y, a.position_z)
        );
    }, [annotations]);

    return (
        <div className={`relative flex flex-col h-[calc(100vh-8rem)] w-full bg-background overflow-hidden ${className}`}>
            {/* Header */}
            {showHeader && (
                <div className="flex items-center justify-between p-4 border-b bg-card shrink-0">
                    <div>
                        <h1 className="text-xl font-semibold">Defect Heat Map</h1>
                        <p className="text-sm text-muted-foreground">
                            Viewing {annotations.length} annotation{annotations.length !== 1 ? 's' : ''}
                        </p>
                    </div>
                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-4 border-r pr-4">
                            <div className="flex items-center gap-2">
                                <Switch
                                    id="heatmap"
                                    checked={heatmapEnabled}
                                    onCheckedChange={setHeatmapEnabled}
                                />
                                <Label htmlFor="heatmap" className="text-sm cursor-pointer">
                                    Heatmap
                                </Label>
                            </div>
                            {heatmapEnabled && (
                                <>
                                    <div className="flex flex-col gap-1 min-w-[120px]">
                                        <Label className="text-xs">Radius: {heatmapRadius.toFixed(2)}</Label>
                                        <Slider
                                            value={[heatmapRadius]}
                                            onValueChange={([value]) => setHeatmapRadius(value)}
                                            min={0.1}
                                            max={2}
                                            step={0.1}
                                            className="w-full"
                                        />
                                    </div>
                                    <div className="flex flex-col gap-1 min-w-[120px]">
                                        <Label className="text-xs">Intensity: {heatmapIntensity.toFixed(2)}</Label>
                                        <Slider
                                            value={[heatmapIntensity]}
                                            onValueChange={([value]) => setHeatmapIntensity(value)}
                                            min={0.1}
                                            max={3}
                                            step={0.1}
                                            className="w-full"
                                        />
                                    </div>
                                </>
                            )}
                        </div>
                        <div className="flex items-center gap-2">
                            {Object.entries(severityCounts).map(([severity, count]) => {
                                const variant =
                                    severity === "critical" ? "destructive" :
                                    severity === "high" ? "destructive" :
                                    severity === "medium" ? "secondary" :
                                    "outline";
                                return (
                                    <Badge key={severity} variant={variant}>
                                        {severity}: {count}
                                    </Badge>
                                );
                            })}
                        </div>
                    </div>
                </div>
            )}

            {/* Loading State */}
            {isFetchingAnnotations && (
                <div className="flex-1 flex items-center justify-center">
                    <div className="flex items-center gap-2 text-muted-foreground">
                        <Loader2 className="h-6 w-6 animate-spin" />
                        <span>Loading annotations...</span>
                    </div>
                </div>
            )}

            {/* 3D Viewport */}
            {!isFetchingAnnotations && (
                <div className="flex-1 relative min-h-0">
                    <ThreeDModelViewer
                        modelUrl={modelUrl}
                        mode="navigate"
                        isLoading={isLoading}
                        onLoadingComplete={() => setIsLoading(false)}
                        instructions="Use mouse to rotate, zoom, and pan • WASD for advanced navigation"
                        neutralColor={useNeutralColor ? "#94a3b8" : undefined}
                        heatmapEnabled={heatmapEnabled}
                        heatmapPositions={heatmapPositions}
                        heatmapRadius={heatmapRadius}
                        heatmapIntensity={heatmapIntensity}
                    >
                        {annotations.map((annotation, idx) => (
                            <AnnotationPoint
                                key={annotation.id || idx}
                                position={[annotation.position_x, annotation.position_y, annotation.position_z]}
                                selected={idx === selectedIdx}
                                severity={annotation.severity || undefined}
                                onClick={() => setSelectedIdx(idx)}
                            />
                        ))}
                    </ThreeDModelViewer>

                    {/* Annotations List */}
                    <AnnotationsList
                        annotations={annotations}
                        selectedIdx={selectedIdx}
                        expanded={annotationsExpanded}
                        onToggleExpanded={() => setAnnotationsExpanded(!annotationsExpanded)}
                        onAnnotationClick={(idx) => {
                            setSelectedIdx(idx);
                            setAnnotationsExpanded(false);
                        }}
                    />

                    {/* Selected Annotation Details */}
                    {selectedIdx !== null && annotations[selectedIdx] && (
                        <div className="absolute top-4 right-4 max-w-sm">
                            <Card>
                                <CardHeader>
                                    <CardTitle className="text-sm flex items-center justify-between">
                                        <span>{annotations[selectedIdx].defect_type || "Unknown"}</span>
                                        <Badge variant={
                                            annotations[selectedIdx].severity === "critical" ? "destructive" :
                                            annotations[selectedIdx].severity === "high" ? "destructive" :
                                            annotations[selectedIdx].severity === "medium" ? "secondary" :
                                            "outline"
                                        }>
                                            {annotations[selectedIdx].severity || "N/A"}
                                        </Badge>
                                    </CardTitle>
                                </CardHeader>
                                {annotations[selectedIdx].notes && (
                                    <CardContent>
                                        <p className="text-sm text-muted-foreground">
                                            {annotations[selectedIdx].notes}
                                        </p>
                                    </CardContent>
                                )}
                            </Card>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
