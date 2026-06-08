/** Timer — hybrid display/capture for "wait N seconds" (countdown) or
 * "time how long" (stopwatch). The operator's start/stop generates a
 * TimerResponse with elapsed_seconds. */
import { useEffect, useState } from "react";
import { Node, mergeAttributes } from "@tiptap/core";
import {
    NodeViewWrapper,
    ReactNodeViewRenderer,
    type NodeViewProps,
} from "@tiptap/react";
import { Timer as TimerIcon, Play, Square } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { NodeCard } from "../shared/NodeCard";
import { AuthoringPopover } from "../shared/AuthoringPopover";
import { useDebouncedAttrs } from "../shared/useDebouncedAttrs";
import { DecimalAttrInput, TextAttrRow } from "../shared/AttrInputs";
import { useOperatorResponse } from "../shared/OperatorResponseContext";

type Direction = "countdown" | "stopwatch";
type TimerResponse = {
    started_at: string;
    completed_at: string;
    elapsed_seconds: number;
    direction: Direction;
};
type Attrs = {
    node_id: string;
    label: string;
    duration_seconds: number;
    direction: Direction;
    required: boolean;
};

function formatMMSS(totalSeconds: number) {
    const s = Math.max(0, Math.floor(totalSeconds));
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}

export function TimerEditForm({ node, updateAttributes }: NodeViewProps) {
    const a = node.attrs as Attrs;
    const update = useDebouncedAttrs(updateAttributes, 250);
    return (
        <div className="space-y-3">
            <div className="space-y-1">
                <Label className="text-xs">Direction</Label>
                <Select
                    value={a.direction}
                    onValueChange={(v) => updateAttributes({ direction: v })}
                >
                    <SelectTrigger className="h-8 text-sm">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="countdown">Countdown (wait N seconds)</SelectItem>
                        <SelectItem value="stopwatch">Stopwatch (time how long)</SelectItem>
                    </SelectContent>
                </Select>
            </div>
            <TextAttrRow attrName="label" label="Label" initial={a.label} update={update} />
            {a.direction === "countdown" && (
                <DecimalAttrInput
                    attrName="duration_seconds"
                    label="Duration (s)"
                    initial={a.duration_seconds ?? null}
                    update={update}
                />
            )}
            <div className="flex items-center justify-between border-t pt-2">
                <Label className="text-xs">Required</Label>
                <Switch
                    checked={a.required}
                    onCheckedChange={(checked) => updateAttributes({ required: checked })}
                />
            </div>
        </div>
    );
}

function View(props: NodeViewProps) {
    const { node, editor } = props;
    const a = node.attrs as Attrs;
    const duration = Number(a.duration_seconds) || 0;
    const direction = (a.direction ?? "countdown") as Direction;
    const required = a.required === true;
    const isOperator = !editor.isEditable;
    const { value, setValue } = useOperatorResponse(a.node_id);

    const [startMs, setStartMs] = useState<number | null>(null);
    const [tick, setTick] = useState(0);

    useEffect(() => {
        if (startMs == null) return;
        const id = window.setInterval(() => setTick((t) => t + 1), 200);
        return () => window.clearInterval(id);
    }, [startMs]);

    const captured = value as TimerResponse | undefined;
    const elapsed = startMs != null ? (Date.now() - startMs) / 1000 : 0;
    const remaining = Math.max(0, duration - elapsed);

    useEffect(() => {
        if (
            startMs != null &&
            direction === "countdown" &&
            duration > 0 &&
            elapsed >= duration
        ) {
            const completedAt = new Date().toISOString();
            const startedAt = new Date(startMs).toISOString();
            setValue({
                started_at: startedAt,
                completed_at: completedAt,
                elapsed_seconds: Math.round(elapsed * 10) / 10,
                direction,
            } satisfies TimerResponse);
            setStartMs(null);
        }
        // tick is included so we re-evaluate as the timer advances
    }, [tick, startMs, direction, duration, elapsed, setValue]);

    const handleStart = () => setStartMs(Date.now());
    const handleStop = () => {
        if (startMs == null) return;
        const completedAt = new Date().toISOString();
        const startedAt = new Date(startMs).toISOString();
        setValue({
            started_at: startedAt,
            completed_at: completedAt,
            elapsed_seconds: Math.round(elapsed * 10) / 10,
            direction,
        } satisfies TimerResponse);
        setStartMs(null);
    };
    const handleReset = () => {
        setValue(undefined);
        setStartMs(null);
    };

    const running = startMs != null;
    const display = running
        ? formatMMSS(direction === "countdown" ? remaining : elapsed)
        : captured
            ? formatMMSS(captured.elapsed_seconds)
            : formatMMSS(duration);

    const card = (
        <NodeCard
            icon={<TimerIcon className="h-4 w-4 text-muted-foreground" />}
            label={a.label || (direction === "countdown" ? "Wait timer" : "Stopwatch")}
            badges={
                <>
                    <Badge variant="outline" className="text-[10px] capitalize">{direction}</Badge>
                    {direction === "countdown" && duration > 0 && (
                        <Badge variant="outline" className="font-mono text-[10px]">
                            {formatMMSS(duration)}
                        </Badge>
                    )}
                    {required && <Badge variant="secondary" className="text-[10px]">Required</Badge>}
                    {isOperator && captured && (
                        <Badge variant="default" className="text-[10px]">Captured ✓</Badge>
                    )}
                </>
            }
        >
            <div className="flex items-center gap-3" contentEditable={false}>
                <span className="font-mono text-2xl tabular-nums">{display}</span>
                {isOperator ? (
                    captured ? (
                        <button
                            type="button"
                            onClick={handleReset}
                            className="rounded border px-3 py-1 text-xs text-muted-foreground hover:bg-muted"
                        >
                            Reset
                        </button>
                    ) : running ? (
                        direction === "stopwatch" ? (
                            <button
                                type="button"
                                onClick={handleStop}
                                className="flex items-center gap-1 rounded bg-destructive px-3 py-1 text-xs text-destructive-foreground"
                            >
                                <Square className="h-3 w-3" /> Stop
                            </button>
                        ) : (
                            <span className="text-xs text-muted-foreground">
                                Counting down — completes automatically
                            </span>
                        )
                    ) : (
                        <button
                            type="button"
                            onClick={handleStart}
                            className="flex items-center gap-1 rounded bg-primary px-3 py-1 text-xs text-primary-foreground"
                        >
                            <Play className="h-3 w-3" /> Start
                        </button>
                    )
                ) : (
                    <span className="text-xs text-muted-foreground">
                        (Start button shown to operator)
                    </span>
                )}
            </div>
        </NodeCard>
    );

    return (
        <NodeViewWrapper className="my-3 not-prose">
            <AuthoringPopover isEditable={editor.isEditable} nodeId={a.node_id}>
                {card}
            </AuthoringPopover>
        </NodeViewWrapper>
    );
}

export const Timer = Node.create({
    name: "timer",
    group: "block",
    atom: true,
    selectable: true,
    draggable: true,
    addAttributes() {
        return {
            node_id: { default: "" },
            label: { default: "" },
            duration_seconds: { default: 30 },
            direction: { default: "countdown" },
            required: { default: false },
        };
    },
    parseHTML() {
        return [{ tag: 'div[data-type="timer"]' }];
    },
    renderHTML({ HTMLAttributes }) {
        return [
            "div",
            mergeAttributes(HTMLAttributes, { "data-type": "timer" }),
            `[${HTMLAttributes.direction?.toUpperCase() || "TIMER"}] ${
                HTMLAttributes.label || ""
            } (${HTMLAttributes.duration_seconds || 0}s)`,
        ];
    },
    addNodeView() {
        return ReactNodeViewRenderer(View);
    },
});

export const SAMPLE_TIMER_COUNTDOWN = {
    type: "timer",
    attrs: {
        node_id: "seed-timer-countdown-1",
        label: "Wait for coolant to stabilize",
        duration_seconds: 30,
        direction: "countdown",
        required: true,
    },
};

export const SAMPLE_TIMER_STOPWATCH = {
    type: "timer",
    attrs: {
        node_id: "seed-timer-stopwatch-1",
        label: "Time the dry-run cycle",
        duration_seconds: 0,
        direction: "stopwatch",
        required: false,
    },
};
