import { Canvas, type ThreeEvent, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, useGLTF } from "@react-three/drei";
import { Suspense, useRef, useEffect, type ReactNode, useState, useMemo } from "react";
import * as THREE from "three";
import { Loader2, AlertTriangle, SunDim } from "lucide-react";
import { ThreeDErrorBoundary } from "./three-d-error-boundary";
import { Button } from "@/components/ui/button";
import { createHeatMapMaterial } from "./heatmap-shader";
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover";
import { Slider } from "@/components/ui/slider";
import { Label } from "@/components/ui/label";

// Lighting presets for light/dark themes
const THEME_LIGHTING = {
    light: {
        ambient: 0.5,
        mainLight: 1.0,
        fillLight: 0.4,
        backgroundColor: "hsl(var(--muted))",
    },
    dark: {
        ambient: 0.3,
        mainLight: 0.8,
        fillLight: 0.2,
        backgroundColor: "hsl(var(--muted))",
    },
} as const;

interface LightingSettings {
    ambient: number;
    mainLight: number;
    fillLight: number;
}

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
        const up = new THREE.Vector3();

        // Get camera's actual orientation vectors
        camera.getWorldDirection(direction);
        up.copy(camera.up).normalize();
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

        const rotSpeed = keys.current.shift ? 0.015 : 0.008;

        if (keys.current.q) camera.rotateY(rotSpeed);
        if (keys.current.e) camera.rotateY(-rotSpeed);
        if (keys.current.r) camera.rotateX(-rotSpeed);
        if (keys.current.f) camera.rotateX(rotSpeed);

        // Roll controls - disable OrbitControls temporarily and update its up vector
        if (keys.current.z || keys.current.c) {
            if (controlsRef?.current) {
                controlsRef.current.enabled = false;
            }

            if (keys.current.z) camera.rotateZ(-rotSpeed);
            if (keys.current.c) camera.rotateZ(rotSpeed);

            // Update OrbitControls up vector to match camera's new orientation
            if (controlsRef?.current) {
                const newUp = new THREE.Vector3(0, 1, 0);
                newUp.applyQuaternion(camera.quaternion);
                controlsRef.current.object.up.copy(newUp);
                controlsRef.current.enabled = true;
                controlsRef.current.update();
            }
        }

        if (keys.current.q || keys.current.e || keys.current.r || keys.current.f) {
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
    _onError,
    onBoundsCalculated,
    neutralColor,
    heatmapEnabled,
    heatmapPositions,
    heatmapIntensities,
    heatmapRadius,
    heatmapIntensity
}: {
    url: string;
    onClick?: (e: ThreeEvent<MouseEvent>) => void;
    onError?: (error: Error) => void;
    onBoundsCalculated?: (bounds: ModelBounds) => void;
    neutralColor?: string;
    heatmapEnabled?: boolean;
    heatmapPositions?: THREE.Vector3[];
    heatmapIntensities?: number[];
    heatmapRadius?: number;
    heatmapIntensity?: number;
}) {
    const { scene: originalScene } = useGLTF(url);
    const materialsRef = useRef<THREE.Material[]>([]);
    const boundsReportedRef = useRef(false);

    // Clone the scene ONCE to avoid mutating the cached version
    // useMemo ensures this only happens when the URL changes, not on every render
    const { scene, bounds } = useMemo(() => {
        const cloned = originalScene.clone(true);

        // Calculate bounding box for auto-centering and scaling
        const box = new THREE.Box3().setFromObject(cloned);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());

        // Get the largest dimension to calculate scale
        const maxDim = Math.max(size.x, size.y, size.z);
        const scale = 3 / maxDim; // Target size of 3 units

        // Center the model at origin
        cloned.position.x = -center.x * scale;
        cloned.position.y = -center.y * scale;
        cloned.position.z = -center.z * scale;

        // Apply uniform scale
        cloned.scale.setScalar(scale);

        // Calculate scaled bounds (what the model looks like after scaling)
        const scaledBounds: ModelBounds = {
            size: { x: size.x * scale, y: size.y * scale, z: size.z * scale },
            maxDimension: maxDim * scale, // This will be ~3 units
            scale: scale,
        };

        return { scene: cloned, bounds: scaledBounds };
    }, [originalScene]);

    // Report bounds once when calculated
    useEffect(() => {
        if (bounds && onBoundsCalculated && !boundsReportedRef.current) {
            boundsReportedRef.current = true;
            onBoundsCalculated(bounds);
        }
    }, [bounds, onBoundsCalculated]);

    // Apply materials in useEffect to properly manage lifecycle and disposal
    useEffect(() => {
        // Dispose of previous materials
        materialsRef.current.forEach(mat => mat.dispose());
        materialsRef.current = [];

        if (heatmapEnabled && heatmapPositions && heatmapPositions.length > 0) {
            // Apply heatmap shader
            const heatmapMaterial = createHeatMapMaterial({
                annotationPositions: heatmapPositions,
                annotationIntensities: heatmapIntensities,
                heatRadius: heatmapRadius || 0.5,
                heatIntensity: heatmapIntensity || 1.0,
                baseColor: new THREE.Color(neutralColor || "#94a3b8"),
            });
            materialsRef.current.push(heatmapMaterial);

            scene.traverse((child) => {
                if ((child as THREE.Mesh).isMesh) {
                    const mesh = child as THREE.Mesh;
                    mesh.material = heatmapMaterial;
                }
            });
        } else if (neutralColor) {
            // Override materials with neutral color if specified
            const neutralMaterial = new THREE.MeshStandardMaterial({
                color: neutralColor,
                metalness: 0.3,
                roughness: 0.7,
            });
            materialsRef.current.push(neutralMaterial);

            scene.traverse((child) => {
                if ((child as THREE.Mesh).isMesh) {
                    const mesh = child as THREE.Mesh;
                    mesh.material = neutralMaterial;
                }
            });
        }

        // Cleanup on unmount
        return () => {
            materialsRef.current.forEach(mat => mat.dispose());
            materialsRef.current = [];
        };
    }, [scene, heatmapEnabled, heatmapPositions, heatmapIntensities, heatmapRadius, heatmapIntensity, neutralColor]);

    return <primitive object={scene} onClick={onClick} />;
}

// Lighting Controls Panel Component
function LightingControlsPanel({
    settings,
    onSettingsChange,
    onReset,
}: {
    settings: LightingSettings;
    onSettingsChange: (settings: LightingSettings) => void;
    onReset: () => void;
}) {
    const updateSetting = (key: keyof LightingSettings, value: number) => {
        onSettingsChange({
            ...settings,
            [key]: value,
        });
    };

    return (
        <Popover>
            <PopoverTrigger asChild>
                <Button
                    variant="secondary"
                    size="icon"
                    className="h-9 w-9 shadow-md"
                    title="Lighting Settings"
                >
                    <SunDim className="h-4 w-4" />
                </Button>
            </PopoverTrigger>
            <PopoverContent className="w-64" align="start">
                <div className="space-y-4">
                    <div className="flex items-center justify-between">
                        <Label className="text-sm font-medium">Lighting</Label>
                        <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={onReset}>
                            Reset
                        </Button>
                    </div>

                    <div className="space-y-3">
                        <div className="space-y-1.5">
                            <div className="flex justify-between">
                                <Label className="text-xs">Ambient</Label>
                                <span className="text-xs text-muted-foreground">{Math.round(settings.ambient * 100)}%</span>
                            </div>
                            <Slider
                                value={[settings.ambient]}
                                onValueChange={([v]) => updateSetting("ambient", v)}
                                min={0}
                                max={1}
                                step={0.05}
                            />
                        </div>

                        <div className="space-y-1.5">
                            <div className="flex justify-between">
                                <Label className="text-xs">Main Light</Label>
                                <span className="text-xs text-muted-foreground">{Math.round(settings.mainLight * 100)}%</span>
                            </div>
                            <Slider
                                value={[settings.mainLight]}
                                onValueChange={([v]) => updateSetting("mainLight", v)}
                                min={0}
                                max={2}
                                step={0.05}
                            />
                        </div>

                        <div className="space-y-1.5">
                            <div className="flex justify-between">
                                <Label className="text-xs">Fill Light</Label>
                                <span className="text-xs text-muted-foreground">{Math.round(settings.fillLight * 100)}%</span>
                            </div>
                            <Slider
                                value={[settings.fillLight]}
                                onValueChange={([v]) => updateSetting("fillLight", v)}
                                min={0}
                                max={1}
                                step={0.05}
                            />
                        </div>
                    </div>
                </div>
            </PopoverContent>
        </Popover>
    );
}

interface CameraConfig {
    position?: [number, number, number];
    fov?: number;
}

export interface ModelBounds {
    size: { x: number; y: number; z: number };
    maxDimension: number;
    scale: number;
}

interface ThreeDModelViewerProps {
    modelUrl: string;
    mode: "navigate" | "annotate";
    onModelClick?: (e: ThreeEvent<MouseEvent>) => void;
    children?: ReactNode;
    isLoading?: boolean;
    onLoadingComplete?: () => void;
    onModelBoundsCalculated?: (bounds: ModelBounds) => void;
    onError?: (error: Error) => void;
    instructions?: string;
    camera?: CameraConfig;
    enablePerformanceMode?: boolean;
    neutralColor?: string;
    heatmapEnabled?: boolean;
    heatmapPositions?: THREE.Vector3[];
    heatmapIntensities?: number[];  // Per-annotation intensity weights
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
    onModelBoundsCalculated,
    onError,
    instructions,
    camera = { position: [2, 2, 2], fov: 60 },
    enablePerformanceMode = true,
    neutralColor,
    heatmapEnabled = false,
    heatmapPositions = [],
    heatmapIntensities,
    heatmapRadius = 0.5,
    heatmapIntensity = 1.0
}: ThreeDModelViewerProps) {
    const orbitControlsRef = useRef<any>();
    const [loadError, setLoadError] = useState<Error | null>(null);
    const isDraggingRef = useRef(false);

    // Detect current theme
    const [isDarkTheme, setIsDarkTheme] = useState(() =>
        document.documentElement.classList.contains("dark")
    );

    // Listen for theme changes
    useEffect(() => {
        const observer = new MutationObserver(() => {
            setIsDarkTheme(document.documentElement.classList.contains("dark"));
        });
        observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
        return () => observer.disconnect();
    }, []);

    // Get default lighting for current theme
    const getDefaultLighting = () => {
        const theme = isDarkTheme ? "dark" : "light";
        return {
            ambient: THEME_LIGHTING[theme].ambient,
            mainLight: THEME_LIGHTING[theme].mainLight,
            fillLight: THEME_LIGHTING[theme].fillLight,
        };
    };

    // Initialize lighting settings
    const [lightingSettings, setLightingSettings] = useState<LightingSettings>(getDefaultLighting);

    // Update lighting when theme changes
    useEffect(() => {
        setLightingSettings(getDefaultLighting());
    }, [isDarkTheme]);

    const handleLightingChange = (newSettings: LightingSettings) => {
        setLightingSettings(newSettings);
    };

    const handleLightingReset = () => {
        setLightingSettings(getDefaultLighting());
    };

    const handleModelError = (error: Error) => {
        setLoadError(error);
        onError?.(error);
    };

    // Track OrbitControls dragging state to prevent annotation on drag
    useEffect(() => {
        const controls = orbitControlsRef.current;
        if (!controls) return;

        const onStart = () => {
            isDraggingRef.current = false;
        };

        const onChange = () => {
            isDraggingRef.current = true;
        };

        controls.addEventListener('start', onStart);
        controls.addEventListener('change', onChange);

        return () => {
            controls.removeEventListener('start', onStart);
            controls.removeEventListener('change', onChange);
        };
    }, []);

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
                    frameloop={mode === "navigate" ? "always" : (enablePerformanceMode ? "demand" : "always")}
                    dpr={[1, 2]} // Limit device pixel ratio for performance on high-res displays
                    onCreated={() => onLoadingComplete?.()}
                    className="!bg-muted"
                >
                    <ambientLight intensity={lightingSettings.ambient} />
                    <directionalLight position={[10, 10, 5]} intensity={lightingSettings.mainLight} />
                    <directionalLight position={[-10, -10, -5]} intensity={lightingSettings.fillLight} />

                    <Suspense fallback={null}>
                        <PartModel
                            url={modelUrl}
                            onClick={(e: ThreeEvent<MouseEvent>) => {
                                // Only create annotation if in annotate mode and not dragging
                                if (mode === "annotate" && !isDraggingRef.current && onModelClick) {
                                    onModelClick(e);
                                }
                            }}
                            onError={handleModelError}
                            onBoundsCalculated={onModelBoundsCalculated}
                            neutralColor={neutralColor}
                            heatmapEnabled={heatmapEnabled}
                            heatmapPositions={heatmapPositions}
                            heatmapIntensities={heatmapIntensities}
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
                        touches={{
                            ONE: 2, // TOUCH.ROTATE
                            TWO: 1, // TOUCH.DOLLY_PAN
                        }}
                    />

                    <KeyboardControls enabled={mode === "navigate"} controlsRef={orbitControlsRef} />
                </Canvas>
            </ThreeDErrorBoundary>

            {/* Lighting Controls */}
            <div className="absolute top-4 left-4 z-10">
                <LightingControlsPanel
                    settings={lightingSettings}
                    onSettingsChange={handleLightingChange}
                    onReset={handleLightingReset}
                />
            </div>

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
                <div className="absolute bottom-4 left-4 right-20">
                    <div className="bg-background/90 backdrop-blur-sm rounded-lg px-3 py-2 inline-block">
                        <p className="text-xs text-muted-foreground">
                            {instructions}
                        </p>
                    </div>
                </div>
            )}
        </div>
    );
}
