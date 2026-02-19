import { useRef, useEffect, useCallback } from "react";
import SignaturePad from "react-signature-canvas";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface SignatureCanvasProps {
    value?: string;
    onChange: (data: string) => void;
    height?: number;
    disabled?: boolean;
    className?: string;
}

export function SignatureCanvas({
    value,
    onChange,
    height = 150,
    disabled = false,
    className,
}: SignatureCanvasProps) {
    const sigPadRef = useRef<SignaturePad>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    // Resize canvas to match container width
    const resizeCanvas = useCallback(() => {
        if (sigPadRef.current && containerRef.current) {
            const canvas = sigPadRef.current.getCanvas();
            const container = containerRef.current;
            const ratio = Math.max(window.devicePixelRatio || 1, 1);

            // Get the actual container width
            const containerWidth = container.offsetWidth;

            // Store current signature data before resize
            const currentData = !sigPadRef.current.isEmpty()
                ? sigPadRef.current.toDataURL("image/png")
                : null;

            // Set canvas dimensions with pixel ratio for crisp rendering
            canvas.width = containerWidth * ratio;
            canvas.height = height * ratio;
            canvas.style.width = `${containerWidth}px`;
            canvas.style.height = `${height}px`;

            // Scale the context
            const ctx = canvas.getContext("2d");
            if (ctx) {
                ctx.scale(ratio, ratio);
            }

            // Clear and restore background
            sigPadRef.current.clear();

            // Restore signature if there was one
            if (currentData) {
                sigPadRef.current.fromDataURL(currentData, {
                    width: containerWidth,
                    height: height
                });
            } else if (value) {
                sigPadRef.current.fromDataURL(value, {
                    width: containerWidth,
                    height: height
                });
            }
        }
    }, [height, value]);

    // Initial setup and resize handling
    useEffect(() => {
        // Small delay to ensure container is rendered
        const timer = setTimeout(resizeCanvas, 50);

        window.addEventListener("resize", resizeCanvas);
        return () => {
            clearTimeout(timer);
            window.removeEventListener("resize", resizeCanvas);
        };
    }, [resizeCanvas]);

    // Load existing signature if provided (only on mount or value change from empty)
    useEffect(() => {
        if (value && sigPadRef.current && containerRef.current) {
            const containerWidth = containerRef.current.offsetWidth;
            sigPadRef.current.fromDataURL(value, {
                width: containerWidth,
                height: height
            });
        }
    }, [value, height]);

    const handleClear = () => {
        if (sigPadRef.current) {
            sigPadRef.current.clear();
            onChange("");
        }
    };

    const handleEnd = () => {
        if (sigPadRef.current && !sigPadRef.current.isEmpty()) {
            const dataUrl = sigPadRef.current.toDataURL("image/png");
            onChange(dataUrl);
        }
    };

    return (
        <div className={cn("space-y-2", className)}>
            <div
                ref={containerRef}
                className={cn(
                    "border rounded-md bg-white relative w-full",
                    disabled && "opacity-50 pointer-events-none"
                )}
                style={{ height }}
            >
                <SignaturePad
                    ref={sigPadRef}
                    canvasProps={{
                        className: "rounded-md absolute inset-0",
                        style: { touchAction: "none" },
                    }}
                    onEnd={handleEnd}
                    penColor="black"
                    backgroundColor="white"
                />
                {!value && (
                    <div className="absolute inset-0 flex items-center justify-center pointer-events-none text-muted-foreground text-sm">
                        Sign here
                    </div>
                )}
            </div>
            <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleClear}
                disabled={disabled}
            >
                Clear Signature
            </Button>
        </div>
    );
}
