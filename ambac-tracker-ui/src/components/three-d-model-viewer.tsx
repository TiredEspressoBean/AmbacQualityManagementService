import { Canvas, type ThreeEvent, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, useGLTF } from "@react-three/drei";
import { Suspense, useRef, useEffect, ReactNode, useState } from "react";
import * as THREE from "three";
import { Loader2, AlertTriangle } from "lucide-react";
import { ThreeDErrorBoundary } from "./three-d-error-boundary";
import { Button } from "@/components/ui/button";
import { createHeatMapMaterial } from "./heatmap-shader";

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

        const speed = keys.current.shift ? 0.2 : 0.1;

        const direction = new THREE.Vector3();
        const right = new THREE.Vector3();
        const up = new THREE.Vector3(0, 1, 0);

        camera.getWorldDirection(direction);
        right.crossVectors(up, direction).normalize();

        const movement = new THREE.Vector3();

        if (keys.current.w) movement.add(direction.clone().multiplyScalar(speed));
        if (keys.current.s) movement.add(direction.clone().multiplyScalar(-speed));
        if (keys.current.a) movement.add(right.clone().multiplyScalar(speed));
        if (keys.current.d) movement.add(right.clone().multiplyScalar(-speed));
        if (keys.current.space) movement.add(up.clone().multiplyScalar(speed));
        if (keys.current.ctrl) movement.add(up.clone().multiplyScalar(-speed));

        if (movement.length() > 0) {
            camera.position.add(movement);

            if (controlsRef?.current) {
                controlsRef.current.target.add(movement);
                controlsRef.current.update();
            }
        }

        const rotSpeed = keys.current.shift ? 0.04 : 0.02;

        if (keys.current.q) camera.rotateY(rotSpeed);
        if (keys.current.e) camera.rotateY(-rotSpeed);
        if (keys.current.r) camera.rotateX(-rotSpeed);
        if (keys.current.f) camera.rotateX(rotSpeed);
        if (keys.current.z) camera.rotateZ(rotSpeed);
        if (keys.current.c) camera.rotateZ(-rotSpeed);

        if (keys.current.q || keys.current.e || keys.current.r || keys.current.f || keys.current.z || keys.current.c) {
            if (controlsRef?.current) {
                const direction = new THREE.Vector3();
                camera.getWorldDirection(direction);
                controlsRef.current.target.copy(camera.position).add(direction);
                controlsRef.current.update();
            }
        }
    });

    return null;
}

function PartModel({
    url,
    onClick,
    onError,
    neutralColor,
    heatmapEnabled,
    heatmapPositions,
    heatmapRadius,
    heatmapIntensity
}: {
    url: string;
    onClick?: (e: ThreeEvent<MouseEvent>) => void;
    onError?: (error: Error) => void;
    neutralColor?: string;
    heatmapEnabled?: boolean;
    heatmapPositions?: THREE.Vector3[];
    heatmapRadius?: number;
    heatmapIntensity?: number;
}) {
    const { scene: originalScene } = useGLTF(url);

    // Clone the scene to avoid mutating the cached version
    const scene = originalScene.clone(true);

    // Calculate bounding box for auto-centering and scaling
    const box = new THREE.Box3().setFromObject(scene);
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());

    // Get the largest dimension to calculate scale
    const maxDim = Math.max(size.x, size.y, size.z);
    const scale = 3 / maxDim; // Target size of 3 units

    // Center the model at origin
    scene.position.x = -center.x * scale;
    scene.position.y = -center.y * scale;
    scene.position.z = -center.z * scale;

    // Apply uniform scale
    scene.scale.setScalar(scale);

    // Apply materials based on mode
    if (heatmapEnabled && heatmapPositions && heatmapPositions.length > 0) {
        // Apply heatmap shader
        const heatmapMaterial = createHeatMapMaterial({
            annotationPositions: heatmapPositions,
            heatRadius: heatmapRadius || 0.5,
            heatIntensity: heatmapIntensity || 1.0,
            baseColor: new THREE.Color(neutralColor || "#94a3b8"),
        });

        scene.traverse((child) => {
            if ((child as THREE.Mesh).isMesh) {
                const mesh = child as THREE.Mesh;
                mesh.material = heatmapMaterial;
            }
        });
    } else if (neutralColor) {
        // Override materials with neutral color if specified
        scene.traverse((child) => {
            if ((child as THREE.Mesh).isMesh) {
                const mesh = child as THREE.Mesh;
                if (mesh.material) {
                    mesh.material = new THREE.MeshStandardMaterial({
                        color: neutralColor,
                        metalness: 0.3,
                        roughness: 0.7,
                    });
                }
            }
        });
    }

    return <primitive object={scene} onClick={onClick} />;
}

interface CameraConfig {
    position?: [number, number, number];
    fov?: number;
}

interface ThreeDModelViewerProps {
    modelUrl: string;
    mode: "navigate" | "annotate";
    onModelClick?: (e: ThreeEvent<MouseEvent>) => void;
    children?: ReactNode;
    isLoading?: boolean;
    onLoadingComplete?: () => void;
    onError?: (error: Error) => void;
    instructions?: string;
    camera?: CameraConfig;
    enablePerformanceMode?: boolean;
    neutralColor?: string;
    heatmapEnabled?: boolean;
    heatmapPositions?: THREE.Vector3[];
    heatmapRadius?: number;
    heatmapIntensity?: number;
}

export function ThreeDModelViewer({
    modelUrl,
    mode,
    onModelClick,
    children,
    isLoading = false,
    onLoadingComplete,
    onError,
    instructions,
    camera = { position: [2, 2, 2], fov: 60 },
    enablePerformanceMode = true,
    neutralColor,
    heatmapEnabled = false,
    heatmapPositions = [],
    heatmapRadius = 0.5,
    heatmapIntensity = 1.0
}: ThreeDModelViewerProps) {
    const orbitControlsRef = useRef<any>();
    const [loadError, setLoadError] = useState<Error | null>(null);

    const handleModelError = (error: Error) => {
        setLoadError(error);
        onError?.(error);
    };

    if (loadError) {
        return (
            <div className="flex items-center justify-center h-full w-full bg-background">
                <div className="text-center p-8 max-w-md">
                    <AlertTriangle className="h-12 w-12 mx-auto mb-4 text-destructive" />
                    <h3 className="text-lg font-semibold mb-2">Failed to Load Model</h3>
                    <p className="text-sm text-muted-foreground mb-4">
                        The 3D model could not be loaded. Please check the file path and format.
                    </p>
                    <Button onClick={() => setLoadError(null)} variant="outline">
                        Retry
                    </Button>
                </div>
            </div>
        );
    }

    return (
        <div className="relative w-full h-full">
            <ThreeDErrorBoundary>
                <Canvas
                    camera={{ position: camera.position, fov: camera.fov }}
                    frameloop={enablePerformanceMode ? "demand" : "always"}
                    onCreated={() => onLoadingComplete?.()}
                >
                    <ambientLight intensity={0.4} />
                    <directionalLight position={[10, 10, 5]} intensity={1} />
                    <directionalLight position={[-10, -10, -5]} intensity={0.3} />

                    <Suspense fallback={null}>
                        <PartModel
                            url={modelUrl}
                            onClick={onModelClick}
                            onError={handleModelError}
                            neutralColor={neutralColor}
                            heatmapEnabled={heatmapEnabled}
                            heatmapPositions={heatmapPositions}
                            heatmapRadius={heatmapRadius}
                            heatmapIntensity={heatmapIntensity}
                        />
                    </Suspense>

                    {children}

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
            </ThreeDErrorBoundary>

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
            {instructions && (
                <div className="absolute bottom-4 right-4">
                    <div className="bg-background/90 backdrop-blur-sm rounded-lg p-3 max-w-xs">
                        <p className="text-sm text-muted-foreground text-center">
                            {instructions}
                        </p>
                    </div>
                </div>
            )}
        </div>
    );
}
