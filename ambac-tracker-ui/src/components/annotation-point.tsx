import { type ThreeEvent } from "@react-three/fiber";

interface AnnotationPointProps {
    position: [number, number, number];
    selected: boolean;
    onClick: () => void;
    severity?: string;
}

export function AnnotationPoint({ position, selected, onClick, severity }: AnnotationPointProps) {
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
        e.stopPropagation(); // Prevent event from bubbling to the model
        onClick();
    };

    return (
        <mesh position={position} onClick={handleClick}>
            <sphereGeometry args={[0.025, 16, 16]} />
            <meshStandardMaterial color={getColor()} />
        </mesh>
    );
}
