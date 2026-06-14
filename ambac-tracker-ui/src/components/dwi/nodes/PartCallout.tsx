/**
 * PartCallout — author-placed instructional callouts on a 3D model.
 *
 * DISTINCT from `PartAnnotation`: that node is operator-runtime *defect
 * capture* (writes `HeatMapAnnotation` rows). This node is *authoring
 * guidance* — numbered, labeled balloons an engineer places to point the
 * operator at features ("torque here", "inspect this seat"). Callouts live
 * in this node's `callouts` attr (body_blocks JSON); nothing is captured at
 * runtime and no backend row is written. The operator sees them read-only.
 *
 * Each callout carries its OWN camera framing (`view`): focusing a callout
 * (clicking its marker or list row) flies the camera to that framing, and the
 * per-row camera button captures the current framing onto that callout.
 */
import { useRef, useState } from "react";
import { Node, mergeAttributes } from "@tiptap/core";
import {
    NodeViewWrapper,
    ReactNodeViewRenderer,
    type NodeViewProps,
} from "@tiptap/react";
import type { ThreeEvent } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import { Camera, ChevronLeft, ChevronRight, Loader2, MapPin, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { NodeCard } from "../shared/NodeCard";
import { AuthoringPopover } from "../shared/AuthoringPopover";
import { TextAttrRow } from "../shared/AttrInputs";
import { useRetrieveThreeDModels } from "@/hooks/useRetrieveThreeDModels";
import { useRetrieveThreeDModel } from "@/hooks/useRetrieveThreeDModel";
import { ThreeDModelViewer, type SavedView, type ViewerViewApi } from "@/components/three-d-model-viewer";

/** A numbered, labeled callout in the model's normalized (auto-centered +
 *  scaled-to-3-units) space — the space `ThreeDModelViewer` reports clicks in.
 *  `view` is this callout's own saved camera framing (optional). */
type Callout = {
    id: string;
    n: number;
    x: number;
    y: number;
    z: number;
    label: string;
    view?: SavedView | null;
};

type Attrs = {
    label: string;
    model_id: string;
    callouts: Callout[];
};

type ThreeDModel = { id: string | number; name?: string; part_type?: { name?: string } };

/** Normalize an absolute media URL to a relative `/media/...` path so the
 *  Vite dev proxy serves it (mirrors the helper in PartAnnotator). */
export function normalizeMediaUrl(url?: string | null): string | undefined {
    if (!url) return undefined;
    try {
        const parsed = new URL(url, window.location.origin);
        return parsed.pathname.startsWith("/media/") ? parsed.pathname : url;
    } catch {
        return url;
    }
}

/** Numbered callout badge anchored at a 3D point (drei `<Html>` inside the Canvas). */
function CalloutMarker({
    n,
    position,
    selected,
    onSelect,
}: {
    n: number;
    position: [number, number, number];
    selected: boolean;
    onSelect?: () => void;
}) {
    return (
        <group position={position}>
            <Html center zIndexRange={[20, 0]}>
                <button
                    type="button"
                    onClick={(e) => {
                        e.stopPropagation();
                        onSelect?.();
                    }}
                    className={
                        "flex h-6 w-6 items-center justify-center rounded-full border-2 border-white text-[11px] font-bold shadow-md transition-transform " +
                        (selected ? "scale-125 bg-amber-500 text-white" : "bg-sky-600 text-white hover:scale-110")
                    }
                >
                    {n}
                </button>
            </Html>
        </group>
    );
}

/** Shared 3D panel. `editable` → click-to-place + editable list (authoring);
 *  otherwise → read-only viewer + a numbered legend (operator runtime).
 *  Focusing a callout flies the camera to that callout's saved `view`. */
function PartCalloutPanel({
    modelId,
    callouts,
    editable,
    onChange,
}: {
    modelId: string;
    callouts: Callout[];
    editable: boolean;
    onChange?: (callouts: Callout[]) => void;
}) {
    const { data: model, isLoading, error } = useRetrieveThreeDModel(modelId);
    const [selectedId, setSelectedId] = useState<string | null>(null);
    const [viewerLoading, setViewerLoading] = useState(true);
    const viewApiRef = useRef<ViewerViewApi | null>(null);

    if (isLoading) {
        return (
            <div className="flex h-24 items-center justify-center text-xs text-muted-foreground">
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Loading model…
            </div>
        );
    }
    if (error || !model) {
        return (
            <div className="flex h-24 items-center justify-center rounded border border-dashed text-xs text-destructive">
                Could not load the selected 3D model.
            </div>
        );
    }
    const modelUrl = normalizeMediaUrl(model.file);
    if (!modelUrl) {
        return (
            <div className="flex h-24 items-center justify-center rounded border border-dashed text-xs text-muted-foreground">
                Model is still processing — no viewable file yet.
            </div>
        );
    }

    /** Select a callout and, if it has its own saved framing, fly there. */
    const focusCallout = (c: Callout) => {
        setSelectedId(c.id);
        if (c.view) viewApiRef.current?.applyView(c.view);
    };

    const place =
        editable && onChange
            ? (e: ThreeEvent<MouseEvent>) => {
                  const p = e.point;
                  const callout: Callout = { id: crypto.randomUUID(), n: callouts.length + 1, x: p.x, y: p.y, z: p.z, label: "", view: null };
                  onChange([...callouts, callout]);
                  setSelectedId(callout.id);
              }
            : undefined;

    const updateLabel = (id: string, label: string) => {
        onChange?.(callouts.map((c) => (c.id === id ? { ...c, label } : c)));
    };

    /** Capture the current camera framing onto this specific callout. */
    const setCalloutView = (id: string) => {
        const view = viewApiRef.current?.getView();
        if (view) onChange?.(callouts.map((c) => (c.id === id ? { ...c, view } : c)));
    };

    const removeCallout = (id: string) => {
        // Renumber so badges stay a contiguous 1..N after a delete.
        onChange?.(callouts.filter((c) => c.id !== id).map((c, i) => ({ ...c, n: i + 1 })));
        if (selectedId === id) setSelectedId(null);
    };

    // Open framed on the first callout that has a saved view (≈ callout ①).
    // Applied once on mount by the viewer, so it frames the operator on load
    // without yanking the camera while authoring.
    const initialView = callouts.find((c) => c.view)?.view ?? null;

    // Next/Prev walkthrough: focus each callout in order (flies to its view).
    const currentIndex = selectedId ? callouts.findIndex((c) => c.id === selectedId) : -1;
    const step = (delta: 1 | -1) => {
        if (callouts.length === 0) return;
        const next =
            currentIndex === -1
                ? delta > 0 ? 0 : callouts.length - 1
                : (currentIndex + delta + callouts.length) % callouts.length;
        focusCallout(callouts[next]);
    };

    return (
        <div className="flex flex-col gap-3">
            <div className="relative h-[420px] w-full overflow-hidden rounded border">
                <ThreeDModelViewer
                    modelUrl={modelUrl}
                    mode="annotate"
                    onModelClick={place}
                    isLoading={viewerLoading}
                    onLoadingComplete={() => setViewerLoading(false)}
                    instructions={editable ? "Click the model to drop a numbered callout" : undefined}
                    initialView={initialView}
                    onViewerReady={(api) => {
                        viewApiRef.current = api;
                    }}
                >
                    {callouts.map((c) => (
                        <CalloutMarker
                            key={c.id}
                            n={c.n}
                            position={[c.x, c.y, c.z]}
                            selected={c.id === selectedId}
                            onSelect={() => focusCallout(c)}
                        />
                    ))}
                </ThreeDModelViewer>
            </div>

            {/* Walkthrough stepper — flies the camera to each callout in order. */}
            {callouts.length > 0 && (
                <div className="flex items-center justify-center gap-2">
                    <Button
                        variant="outline"
                        size="sm"
                        className="h-7 gap-1 px-2"
                        onClick={() => step(-1)}
                        title="Previous callout"
                    >
                        <ChevronLeft className="h-3.5 w-3.5" />
                        Prev
                    </Button>
                    <span className="min-w-[5rem] text-center text-xs tabular-nums text-muted-foreground">
                        Callout {currentIndex === -1 ? "–" : callouts[currentIndex].n} / {callouts.length}
                    </span>
                    <Button
                        variant="outline"
                        size="sm"
                        className="h-7 gap-1 px-2"
                        onClick={() => step(1)}
                        title="Next callout"
                    >
                        Next
                        <ChevronRight className="h-3.5 w-3.5" />
                    </Button>
                </div>
            )}

            <div className="flex flex-col gap-2">
                <div className="text-xs font-medium text-muted-foreground">Callouts ({callouts.length})</div>
                {callouts.length === 0 ? (
                    <p className="text-xs text-muted-foreground">
                        {editable ? "Click the model to place your first labeled callout." : "No callouts on this model."}
                    </p>
                ) : editable ? (
                    <div className="flex flex-col gap-1.5">
                        {callouts.map((c) => (
                            <div
                                key={c.id}
                                onMouseDown={() => focusCallout(c)}
                                className={
                                    "flex items-center gap-1.5 rounded border p-1.5 " +
                                    (c.id === selectedId ? "border-amber-500" : "border-transparent")
                                }
                            >
                                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-sky-600 text-[10px] font-bold text-white">
                                    {c.n}
                                </span>
                                <Input
                                    value={c.label}
                                    onChange={(e) => updateLabel(c.id, e.target.value)}
                                    placeholder={`Label for callout ${c.n}`}
                                    className="h-7 text-xs"
                                />
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className={"h-7 w-7 shrink-0 " + (c.view ? "text-sky-600" : "text-muted-foreground")}
                                    onClick={() => setCalloutView(c.id)}
                                    title={c.view ? "Update this callout's saved camera view" : "Save current camera view to this callout"}
                                >
                                    <Camera className="h-3.5 w-3.5" />
                                </Button>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-7 w-7 shrink-0"
                                    onClick={() => removeCallout(c.id)}
                                    title="Remove callout"
                                >
                                    <Trash2 className="h-3.5 w-3.5" />
                                </Button>
                            </div>
                        ))}
                    </div>
                ) : (
                    // Operator: read-only numbered legend; click a row to fly to it.
                    <ol className="flex flex-col gap-1">
                        {callouts.map((c) => (
                            <li key={c.id}>
                                <button
                                    type="button"
                                    onClick={() => focusCallout(c)}
                                    className="flex w-full items-center gap-2 rounded px-1 py-0.5 text-left text-xs hover:bg-muted/60"
                                    title={c.view ? "Fly to this callout" : undefined}
                                >
                                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-sky-600 text-[10px] font-bold text-white">
                                        {c.n}
                                    </span>
                                    <span>{c.label || <span className="text-muted-foreground">(no label)</span>}</span>
                                    {c.view && <Camera className="ml-auto h-3 w-3 shrink-0 text-muted-foreground" />}
                                </button>
                            </li>
                        ))}
                    </ol>
                )}
            </div>
        </div>
    );
}

export function PartCalloutEditForm({ node, updateAttributes }: NodeViewProps) {
    const a = node.attrs as Attrs;
    const { data: modelsResp } = useRetrieveThreeDModels();
    const models = (modelsResp?.results ?? []) as ThreeDModel[];
    return (
        <div className="space-y-3">
            <TextAttrRow attrName="label" label="Label" initial={a.label} update={updateAttributes} />
            <div className="space-y-1">
                <Label className="text-xs">3D model</Label>
                <Select value={String(a.model_id ?? "")} onValueChange={(v) => updateAttributes({ model_id: v })}>
                    <SelectTrigger className="h-8 text-sm">
                        <SelectValue placeholder="— pick a 3D model —" />
                    </SelectTrigger>
                    <SelectContent>
                        {models.map((m) => (
                            <SelectItem key={String(m.id)} value={String(m.id)}>
                                {m.name ?? `Model #${m.id}`}
                                {m.part_type?.name ? ` (${m.part_type.name})` : ""}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>
            </div>
        </div>
    );
}

function View(props: NodeViewProps) {
    const { node, editor, updateAttributes } = props;
    const a = node.attrs as Attrs;
    const isEditable = editor.isEditable;
    const hasModel = Boolean(a.model_id);
    const callouts = a.callouts ?? [];

    const card = (
        <NodeCard
            icon={<MapPin className="h-4 w-4 text-muted-foreground" />}
            label={a.label || "Part callouts"}
            badges={
                <>
                    <Badge variant="outline" className="text-[10px]">3D</Badge>
                    {callouts.length > 0 && (
                        <Badge variant="secondary" className="text-[10px]">{callouts.length} callout{callouts.length === 1 ? "" : "s"}</Badge>
                    )}
                    {!hasModel && <Badge variant="destructive" className="text-[10px]">No model selected</Badge>}
                </>
            }
        >
            <div contentEditable={false}>
                {hasModel ? (
                    <PartCalloutPanel
                        modelId={String(a.model_id)}
                        callouts={callouts}
                        editable={isEditable}
                        onChange={isEditable ? (next) => updateAttributes({ callouts: next }) : undefined}
                    />
                ) : (
                    <div className="flex h-24 flex-col items-center justify-center rounded border border-dashed text-center text-xs text-muted-foreground">
                        {isEditable
                            ? "Pick a 3D model in the properties panel to start placing callouts."
                            : "No 3D model selected for these callouts."}
                    </div>
                )}
            </div>
        </NodeCard>
    );

    return (
        <NodeViewWrapper className="my-3 not-prose">
            <AuthoringPopover isEditable={editor.isEditable}>{card}</AuthoringPopover>
        </NodeViewWrapper>
    );
}

export const PartCallout = Node.create({
    name: "partCallout",
    group: "block",
    atom: true,
    selectable: true,
    draggable: true,
    addAttributes() {
        return {
            label: { default: "Part callouts" },
            model_id: { default: "" },
            // Authoring-only guidance points (each may carry its own `view`);
            // JSON-persisted, not serialized to HTML.
            callouts: { default: [] as Callout[], renderHTML: () => ({}) },
        };
    },
    parseHTML() {
        return [{ tag: 'div[data-type="part-callout"]' }];
    },
    renderHTML({ HTMLAttributes }) {
        return [
            "div",
            mergeAttributes(HTMLAttributes, { "data-type": "part-callout" }),
            `[CALLOUTS] ${HTMLAttributes.label || ""} (model ${HTMLAttributes.model_id || "?"})`,
        ];
    },
    addNodeView() {
        return ReactNodeViewRenderer(View);
    },
});

export const SAMPLE_PART_CALLOUT = {
    type: "partCallout",
    attrs: {
        label: "Part callouts",
        model_id: "",
        callouts: [],
    },
};
