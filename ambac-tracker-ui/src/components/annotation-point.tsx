import { type ThreeEvent } from "@react-three/fiber";

interface AnnotationPointProps {
    position: [number, number, number];
    selected: boolean;
    onClick: () => void;
    severity?: string;
    mode?: "navigate" | "annotate";
}

export function AnnotationPoint({ position, selected, onClick, severity, mode: _mode = "navigate" }: AnnotationPointProps) {

    const getColor = () => {
        if (selected) return "yellow";
        switch (severity) {
            case "critical": return "#ef4444"; // red-500
            case "high": return "#f97316"; // orange-500
            case "medium": return "#eab308"; // yellow-500
            case "low": return "#22c55e"; // green-500
            default: return "#ef4444";
        }
    };

    const handleClick = (e: ThreeEvent<MouseEvent>) => {
        e.stopPropagation();
        onClick();
    };

    // Always render as a 3D sphere, clickable in both modes
    return (
        <mesh position={position} onClick={handleClick}>
            <sphereGeometry args={[0.025, 16, 16]} />
            <meshStandardMaterial color={getColor()} />
        </mesh>
    );
}
