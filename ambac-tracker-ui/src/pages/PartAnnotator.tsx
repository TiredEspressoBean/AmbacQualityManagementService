import { Canvas, type ThreeEvent, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, useGLTF } from "@react-three/drei";
import { Suspense, useState, useEffect, useRef } from "react";
import * as THREE from "three";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Trash2, Navigation, Edit3, AlertTriangle, Loader2, ChevronDown, List } from "lucide-react";

const ERROR_TYPES = ["Crack", "Burn", "Porosity", "Overspray"];
const SEVERITY_LEVELS = ["Low", "Medium", "High", "Critical"];

function KeyboardControls({ enabled, controlsRef }: { enabled: boolean; controlsRef: React.RefObject<any> }) {
    const { camera } = useThree();
    
    const keys = useRef({
        w: false,        // Forward
        s: false,        // Back
        a: false,        // Strafe left
        d: false,        // Strafe right
        space: false,    // Up
        ctrl: false,     // Down
        q: false,        // Yaw left
        e: false,        // Yaw right
        r: false,        // Pitch up
        f: false,        // Pitch down
        z: false,        // Roll left
        c: false,        // Roll right
        shift: false,    // Sprint
    });


    useEffect(() => {
        const handleKeyDown = (event: KeyboardEvent) => {
            if (!enabled) return;
            const key = event.key.toLowerCase();
            
            if (key === ' ') {
                keys.current.space = true;
                event.preventDefault();
            } else if (key === 'control') {
                keys.current.ctrl = true;
                event.preventDefault();
            } else if (key === 'shift') {
                keys.current.shift = true;
                event.preventDefault();
            } else if (key in keys.current) {
                keys.current[key as keyof typeof keys.current] = true;
                event.preventDefault();
            }
        };

        const handleKeyUp = (event: KeyboardEvent) => {
            if (!enabled) return;
            const key = event.key.toLowerCase();
            
            if (key === ' ') {
                keys.current.space = false;
                event.preventDefault();
            } else if (key === 'control') {
                keys.current.ctrl = false;
                event.preventDefault();
            } else if (key === 'shift') {
                keys.current.shift = false;
                event.preventDefault();
            } else if (key in keys.current) {
                keys.current[key as keyof typeof keys.current] = false;
                event.preventDefault();
            }
        };


        window.addEventListener('keydown', handleKeyDown);
        window.addEventListener('keyup', handleKeyUp);

        return () => {
            window.removeEventListener('keydown', handleKeyDown);
            window.removeEventListener('keyup', handleKeyUp);
        };
    }, [enabled]);

    useFrame(() => {
        if (!enabled || !camera) return;

        const speed = keys.current.shift ? 0.2 : 0.1; // Sprint with shift
        
        // Movement
        const direction = new THREE.Vector3();
        const right = new THREE.Vector3();
        const up = new THREE.Vector3(0, 1, 0); // World up
        
        // Get camera's forward and right vectors
        camera.getWorldDirection(direction);
        right.crossVectors(up, direction).normalize();

        // Calculate movement
        const movement = new THREE.Vector3();
        
        if (keys.current.w) movement.add(direction.clone().multiplyScalar(speed));
        if (keys.current.s) movement.add(direction.clone().multiplyScalar(-speed));
        if (keys.current.a) movement.add(right.clone().multiplyScalar(speed));
        if (keys.current.d) movement.add(right.clone().multiplyScalar(-speed));
        if (keys.current.space) movement.add(up.clone().multiplyScalar(speed));
        if (keys.current.ctrl) movement.add(up.clone().multiplyScalar(-speed));

        // Apply movement
        if (movement.length() > 0) {
            camera.position.add(movement);
            
            // Update OrbitControls target to maintain relative position
            if (controlsRef?.current) {
                controlsRef.current.target.add(movement);
                controlsRef.current.update();
            }
        }

        // Rotation controls - update OrbitControls target when rotating
        const rotSpeed = keys.current.shift ? 0.04 : 0.02;
        
        // Apply rotations directly like movement
        if (keys.current.q) camera.rotateY(rotSpeed);   // Yaw left
        if (keys.current.e) camera.rotateY(-rotSpeed);  // Yaw right
        if (keys.current.r) camera.rotateX(-rotSpeed);  // Pitch up
        if (keys.current.f) camera.rotateX(rotSpeed);   // Pitch down
        if (keys.current.z) camera.rotateZ(rotSpeed);   // Roll left
        if (keys.current.c) camera.rotateZ(-rotSpeed);  // Roll right
        
        // Update OrbitControls target to match new camera direction
        if (keys.current.q || keys.current.e || keys.current.r || keys.current.f || keys.current.z || keys.current.c) {
            if (controlsRef?.current) {
                const direction = new THREE.Vector3();
                camera.getWorldDirection(direction);
                controlsRef.current.target.copy(camera.position).add(direction);
                controlsRef.current.update();
            }
        }

        // Mouse look removed - using keyboard controls only
    });

    return null;
}

function PartModel({ url, onClick }: { url: string; onClick: (e: ThreeEvent<MouseEvent>) => void }) {
    const { scene } = useGLTF(url);
    
    // Auto-fit the model to a reasonable size - make it larger
    scene.scale.setScalar(2.5);
    scene.position.set(0, 0, 0);
    
    return <primitive object={scene} onClick={onClick} />;
}

function AnnotationPoint({ position, selected, onClick, severity }: {
    position: [number, number, number];
    selected: boolean;
    onClick: () => void;
    severity?: string;
}) {
    const getColor = () => {
        if (selected) return "yellow";
        switch (severity) {
            case "Critical": return "#ef4444"; // red-500
            case "High": return "#f97316"; // orange-500
            case "Medium": return "#eab308"; // yellow-500
            case "Low": return "#22c55e"; // green-500
            default: return "#ef4444";
        }
    };

    return (
        <mesh position={position} onClick={onClick}>
            <sphereGeometry args={[0.025, 16, 16]} />
            <meshStandardMaterial color={getColor()} />
        </mesh>
    );
}

export function PartAnnotator({ 
    modelUrl = "/models/Duck.glb",
    className = "",
    showHeader = true,
    onAnnotationsChange,
    initialAnnotations = []
}: { 
    modelUrl?: string;
    className?: string;
    showHeader?: boolean;
    onAnnotationsChange?: (annotations: any[]) => void;
    initialAnnotations?: any[];
}) {
    const [annotations, setAnnotations] = useState<any[]>(initialAnnotations);
    const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
    const [mode, setMode] = useState<"navigate" | "annotate">("annotate");
    const [isLoading, setIsLoading] = useState(true);
    const [showEditDialog, setShowEditDialog] = useState(false);
    const [controlsExpanded, setControlsExpanded] = useState(false);
    const [annotationsExpanded, setAnnotationsExpanded] = useState(true);
    const orbitControlsRef = useRef<any>();

    const handleClick = (e: ThreeEvent<MouseEvent>) => {
        if (mode !== "annotate") return;
        const point = e.point;
        const newAnnotations = [
            ...annotations,
            {
                position: [point.x, point.y, point.z],
                type: ERROR_TYPES[0],
                severity: SEVERITY_LEVELS[0],
                note: "",
            },
        ];
        setAnnotations(newAnnotations);
        onAnnotationsChange?.(newAnnotations);
    };

    const updateAnnotation = (field: string, value: string) => {
        if (selectedIdx === null) return;
        const updated = [...annotations];
        updated[selectedIdx][field] = value;
        setAnnotations(updated);
        onAnnotationsChange?.(updated);
    };

    const deleteAnnotation = () => {
        if (selectedIdx === null) return;
        const updated = annotations.filter((_, idx) => idx !== selectedIdx);
        setAnnotations(updated);
        onAnnotationsChange?.(updated);
        setSelectedIdx(null);
    };

    const getSeverityBadgeVariant = (severity: string) => {
        switch (severity) {
            case "Critical": return "destructive";
            case "High": return "destructive";
            case "Medium": return "secondary";
            case "Low": return "outline";
            default: return "outline";
        }
    };

    return (
        <div className={`relative flex flex-col h-[calc(100vh-8rem)] w-full bg-background overflow-hidden ${className}`}>
            {/* Mobile Header */}
            {showHeader && (
                <div className="flex items-center justify-between p-4 border-b bg-card shrink-0">
                <div>
                    <h1 className="text-xl font-semibold">Part Annotator</h1>
                    <p className="text-sm text-muted-foreground">
                        Mark defects on 3D models
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <Select value={mode} onValueChange={(value: any) => setMode(value)}>
                        <SelectTrigger className="w-40">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="annotate">
                                <div className="flex items-center gap-2">
                                    <Edit3 className="h-4 w-4" />
                                    Annotate Defects
                                </div>
                            </SelectItem>
                            <SelectItem value="navigate">
                                <div className="flex items-center gap-2">
                                    <Navigation className="h-4 w-4" />
                                    Navigate View
                                </div>
                            </SelectItem>
                        </SelectContent>
                    </Select>
                </div>
                </div>
            )}

            {/* 3D Viewport - Takes remaining height */}
            <div className="flex-1 relative min-h-0">
                <Canvas 
                    camera={{ position: [2, 2, 2], fov: 60 }}
                    onCreated={() => setIsLoading(false)}
                >
                    <ambientLight intensity={0.4} />
                    <directionalLight position={[10, 10, 5]} intensity={1} />
                    <directionalLight position={[-10, -10, -5]} intensity={0.3} />
                    
                    <Suspense fallback={null}>
                        <PartModel url={modelUrl} onClick={handleClick} />
                    </Suspense>
                    
                    {annotations.map((a, idx) => (
                        <AnnotationPoint
                            key={idx}
                            position={a.position}
                            selected={idx === selectedIdx}
                            severity={a.severity}
                            onClick={() => {
                                setSelectedIdx(idx);
                                setShowEditDialog(true);
                            }}
                        />
                    ))}
                    
                    <OrbitControls 
                        ref={orbitControlsRef}
                        makeDefault 
                        enablePan={true}
                        enableZoom={true}
                        enableRotate={true}
                        disabled={mode === "annotate"}
                        touches={{
                            ONE: 2, // TOUCH.ROTATE
                            TWO: 1, // TOUCH.DOLLY_PAN
                        }}
                    />
                    
                    <KeyboardControls enabled={mode === "navigate"} controlsRef={orbitControlsRef} />
                </Canvas>

                {/* Loading Overlay */}
                {isLoading && (
                    <div className="absolute inset-0 bg-background/80 backdrop-blur-sm flex items-center justify-center">
                        <div className="flex items-center gap-2 text-muted-foreground">
                            <Loader2 className="h-6 w-6 animate-spin" />
                            <span>Loading 3D model...</span>
                        </div>
                    </div>
                )}

                {/* Instructions */}
                <div className="absolute bottom-4 right-4">
                    <div className="bg-background/90 backdrop-blur-sm rounded-lg p-3 max-w-xs">
                        <p className="text-sm text-muted-foreground text-center">
                            {mode === "annotate" 
                                ? "Tap model to add defect" 
                                : "WASD move • Space/Ctrl up/down • QE yaw • RF pitch • ZC roll"
                            }
                        </p>
                    </div>
                </div>

                {/* Annotations List Floating Button */}
                <div className="absolute bottom-4 left-4">
                    <Button
                        onClick={() => setAnnotationsExpanded(!annotationsExpanded)}
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
            </div>

            {/* Mobile Annotations Bottom Sheet - Now inside main container */}
            {annotationsExpanded && (
                <div className="absolute bottom-0 left-0 right-0 bg-background border-t rounded-t-lg shadow-lg max-h-48 sm:max-h-64 overflow-hidden z-10">
                    <div 
                        className="flex items-center justify-between p-4 border-b cursor-pointer" 
                        onClick={() => setAnnotationsExpanded(false)}
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
                                    onClick={() => {
                                        setSelectedIdx(idx);
                                        setShowEditDialog(true);
                                        setAnnotationsExpanded(false);
                                    }}
                                >
                                    <div className="flex items-center justify-between mb-1">
                                        <span className="font-medium text-sm">{annotation.type}</span>
                                        <Badge variant={getSeverityBadgeVariant(annotation.severity)} className="text-xs">
                                            {annotation.severity}
                                        </Badge>
                                    </div>
                                    {annotation.note && (
                                        <p className="text-xs text-muted-foreground line-clamp-1">
                                            {annotation.note}
                                        </p>
                                    )}
                                </div>
                            ))
                        )}
                    </div>
                </div>
            )}


            {/* Edit Annotation Dialog */}
            <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
                <DialogContent className="w-[95vw] max-w-md">
                    <DialogHeader>
                        <DialogTitle>Edit Defect Annotation</DialogTitle>
                        <DialogDescription>
                            Update the defect details and severity level
                        </DialogDescription>
                    </DialogHeader>
                    
                    {selectedIdx !== null && (
                        <div className="space-y-4 py-4">
                            <div>
                                <Label>Error Type</Label>
                                <Select
                                    value={annotations[selectedIdx]?.type}
                                    onValueChange={(value) => updateAnnotation("type", value)}
                                >
                                    <SelectTrigger className="mt-2">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {ERROR_TYPES.map((type) => (
                                            <SelectItem key={type} value={type}>
                                                {type}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>

                            <div>
                                <Label>Severity Level</Label>
                                <Select
                                    value={annotations[selectedIdx]?.severity}
                                    onValueChange={(value) => updateAnnotation("severity", value)}
                                >
                                    <SelectTrigger className="mt-2">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {SEVERITY_LEVELS.map((level) => (
                                            <SelectItem key={level} value={level}>
                                                {level}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>

                            <div>
                                <Label>Notes</Label>
                                <Textarea
                                    value={annotations[selectedIdx]?.note || ""}
                                    onChange={(e) => updateAnnotation("note", e.target.value)}
                                    placeholder="Describe the defect in detail..."
                                    className="mt-2 min-h-[100px]"
                                />
                            </div>
                        </div>
                    )}

                    <DialogFooter className="flex-col gap-2 sm:flex-row">
                        <Button
                            onClick={() => {
                                deleteAnnotation();
                                setShowEditDialog(false);
                            }}
                            variant="destructive"
                            className="w-full sm:w-auto"
                        >
                            <Trash2 className="h-4 w-4 mr-2" />
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
        </div>
    );
}
