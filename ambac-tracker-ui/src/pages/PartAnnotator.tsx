import { Canvas, type ThreeEvent } from "@react-three/fiber";
import { OrbitControls, useGLTF } from "@react-three/drei";
import { Suspense, useState } from "react";

const ERROR_TYPES = ["Crack", "Burn", "Porosity", "Overspray"];
const SEVERITY_LEVELS = ["Low", "Medium", "High", "Critical"];

function PartModel({ url, onClick }: { url: string; onClick: (e: ThreeEvent<MouseEvent>) => void }) {
    const { scene } = useGLTF(url);
    return <primitive object={scene} onClick={onClick} />;
}

function AnnotationPoint({ position, selected, onClick }: {
    position: [number, number, number];
    selected: boolean;
    onClick: () => void;
}) {
    return (
        <mesh position={position} onClick={onClick}>
            <sphereGeometry args={[0.01, 16, 16]} />
            <meshStandardMaterial color={selected ? "yellow" : "red"} />
        </mesh>
    );
}

export function PartAnnotator({ modelUrl = "/models/Duck.glb" }: { modelUrl?: string }) {
    const [annotations, setAnnotations] = useState<any[]>([]);
    const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
    const [mode, setMode] = useState<"navigate" | "annotate">("annotate");

    const handleClick = (e: ThreeEvent<MouseEvent>) => {
        if (mode !== "annotate") return;
        const point = e.point;
        setAnnotations((prev) => [
            ...prev,
            {
                position: [point.x, point.y, point.z],
                type: ERROR_TYPES[0],
                severity: SEVERITY_LEVELS[0],
                note: "",
            },
        ]);
    };

    const updateAnnotation = (field: string, value: string) => {
        if (selectedIdx === null) return;
        const updated = [...annotations];
        updated[selectedIdx][field] = value;
        setAnnotations(updated);
    };

    const deleteAnnotation = () => {
        if (selectedIdx === null) return;
        setAnnotations((prev) => prev.filter((_, idx) => idx !== selectedIdx));
        setSelectedIdx(null);
    };

    return (
        <div className="w-full h-[600px] bg-black relative">
            <Canvas camera={{ position: [0, 0, 3], fov: 45 }}>
                <ambientLight intensity={0.6} />
                <directionalLight position={[5, 5, 5]} />
                <Suspense fallback={null}>
                    <PartModel url={modelUrl} onClick={handleClick} />
                </Suspense>
                {annotations.map((a, idx) => (
                    <AnnotationPoint
                        key={idx}
                        position={a.position}
                        selected={idx === selectedIdx}
                        onClick={() => setSelectedIdx(idx)}
                    />
                ))}
                {mode === "navigate" && <OrbitControls makeDefault />}
            </Canvas>

            {/* UI */}
            <div className="absolute top-2 left-2 p-3 space-y-3 bg-opacity-90 rounded shadow text-sm max-w-xs">
                <div>
                    <label className="font-medium mr-2">Mode:</label>
                    <select
                        value={mode}
                        onChange={(e) => setMode(e.target.value as any)}
                        className="border rounded px-2 py-1"
                    >
                        <option value="annotate">🖊️ Annotate</option>
                        <option value="navigate">🕹️ Navigate</option>
                    </select>
                </div>

                {selectedIdx !== null && (
                    <div className="space-y-2">
                        <div>
                            <label className="block">Error Type:</label>
                            <select
                                value={annotations[selectedIdx]?.type}
                                onChange={(e) => updateAnnotation("type", e.target.value)}
                                className="border rounded px-2 py-1 w-full"
                            >
                                {ERROR_TYPES.map((type) => (
                                    <option key={type}>{type}</option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label className="block">Severity:</label>
                            <select
                                value={annotations[selectedIdx]?.severity}
                                onChange={(e) => updateAnnotation("severity", e.target.value)}
                                className="border rounded px-2 py-1 w-full"
                            >
                                {SEVERITY_LEVELS.map((level) => (
                                    <option key={level}>{level}</option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label className="block">Note:</label>
                            <textarea
                                value={annotations[selectedIdx]?.note}
                                onChange={(e) => updateAnnotation("note", e.target.value)}
                                className="w-full border rounded px-2 py-1"
                            />
                        </div>
                        <button
                            onClick={deleteAnnotation}
                            className="px-2 py-1 rounded bg-red-500 text-white hover:bg-red-600"
                        >
                            Delete Annotation
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
