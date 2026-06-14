/**
 * PartAnnotation — embeds the existing 3D `PartAnnotator` widget inside a
 * substep so operators can place defect annotations against the part
 * directly in the work flow. Maps to `HeatMapAnnotation` rows; when the
 * substep is an inspection point, captured annotations link to the
 * pending `QualityReports` via the existing `qualityReportIds` prop on
 * `PartAnnotator`.
 *
 * Engineer authoring: pick the 3D model (model_id), label, required flag.
 * Operator capture: handled entirely by `PartAnnotator` (it persists
 * annotations directly via its own hooks). The operator-runtime layer
 * provides `part_id` + `work_order_id` + `quality_report_id` via
 * `PartContext`; when the context is missing (authoring spike) we render
 * a placeholder.
 *
 * NOTE: author-time *instructional* callouts live in the separate
 * `PartCallout` node. This node is operator-runtime defect capture only —
 * it carries a `node_id` + `required` and participates in the substep's
 * proceed-gate; `PartCallout` deliberately does neither.
 */
import { useState } from "react";
import { Node, mergeAttributes } from "@tiptap/core";
import {
    NodeViewWrapper,
    ReactNodeViewRenderer,
    type NodeViewProps,
} from "@tiptap/react";
import { Loader2, ScanSearch } from "lucide-react";
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
import { TextAttrRow } from "../shared/AttrInputs";
import { usePartContext } from "../shared/PartContext";
import { useRetrieveThreeDModels } from "@/hooks/useRetrieveThreeDModels";
import { useRetrieveThreeDModel } from "@/hooks/useRetrieveThreeDModel";
import { ThreeDModelViewer, type SavedView } from "@/components/three-d-model-viewer";
import { normalizeMediaUrl } from "./PartCallout";
import { PartAnnotator } from "@/pages/PartAnnotator";

type Attrs = {
    node_id: string;
    label: string;
    model_id: string;
    required: boolean;
    /** Author-saved camera framing for the operator's defect-capture view. */
    default_view: SavedView | null;
};

type ThreeDModel = { id: string | number; name?: string; part_type?: { name?: string } };

/** Compact authoring viewer: the engineer orbits the model and saves a default
 *  camera framing for the operator's defect-capture view. Framing only — no
 *  annotation placement happens here (that's operator runtime in PartAnnotator). */
function AnnotationFramingViewer({
    modelId,
    defaultView,
    onSaveView,
    instructions,
}: {
    modelId: string;
    defaultView: SavedView | null;
    /** Omit for a read-only model preview (no Save-view button). */
    onSaveView?: (view: SavedView) => void;
    instructions?: string;
}) {
    const { data: model, isLoading, error } = useRetrieveThreeDModel(modelId);
    const [viewerLoading, setViewerLoading] = useState(true);

    if (isLoading) {
        return (
            <div className="flex h-24 items-center justify-center text-xs text-muted-foreground">
                <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading model…
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
    return (
        <div className="relative h-[320px] w-full overflow-hidden rounded border">
            <ThreeDModelViewer
                modelUrl={modelUrl}
                mode="annotate"
                isLoading={viewerLoading}
                onLoadingComplete={() => setViewerLoading(false)}
                instructions={instructions ?? (onSaveView ? "Orbit to frame the inspection view, then Save view" : undefined)}
                initialView={defaultView}
                onSaveView={onSaveView}
            />
        </div>
    );
}

export function PartAnnotationEditForm({ node, updateAttributes }: NodeViewProps) {
    const a = node.attrs as Attrs;
    const update = useDebouncedAttrs(updateAttributes, 250);
    const { data: modelsResp } = useRetrieveThreeDModels();
    const models = (modelsResp?.results ?? []) as ThreeDModel[];
    return (
        <div className="space-y-3">
            <TextAttrRow attrName="label" label="Label" initial={a.label} update={update} />
            <div className="space-y-1">
                <Label className="text-xs">3D model</Label>
                <Select
                    value={String(a.model_id ?? "")}
                    onValueChange={(v) => updateAttributes({ model_id: v })}
                >
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
            <div className="flex items-center justify-between border-t pt-2">
                <Label className="text-xs">At least one annotation required</Label>
                <Switch
                    checked={a.required}
                    onCheckedChange={(v) => updateAttributes({ required: v })}
                />
            </div>
        </div>
    );
}

function View(props: NodeViewProps) {
    const { node, editor, updateAttributes } = props;
    const a = node.attrs as Attrs;
    const isOperator = !editor.isEditable;
    const part = usePartContext();

    const hasModel = Boolean(a.model_id);
    const hasPartBinding = Boolean(part.part_id);
    const hasQrBinding = Boolean(part.quality_report_id);

    const card = (
        <NodeCard
            icon={<ScanSearch className="h-4 w-4 text-muted-foreground" />}
            label={a.label || "Part annotation"}
            badges={
                <>
                    <Badge variant="outline" className="text-[10px]">3D</Badge>
                    {a.required && <Badge variant="secondary" className="text-[10px]">Required</Badge>}
                    {!hasModel && (
                        <Badge variant="destructive" className="text-[10px]">No model selected</Badge>
                    )}
                    {isOperator && hasModel && hasPartBinding && !hasQrBinding && (
                        <Badge variant="outline" className="border-amber-500/60 text-[10px] text-amber-600">
                            QR not ready
                        </Badge>
                    )}
                </>
            }
        >
            <div contentEditable={false}>
                {isOperator ? (
                    !hasModel ? (
                        <div className="flex h-24 flex-col items-center justify-center rounded border border-dashed text-center text-xs text-muted-foreground">
                            No 3D model selected for this annotation.
                        </div>
                    ) : hasPartBinding ? (
                        // Live embed — PartAnnotator owns persistence (writes
                        // `HeatMapAnnotation` rows). Opens at the author-saved
                        // framing (`default_view`) when one exists.
                        <PartAnnotator
                            modelId={String(a.model_id)}
                            partId={String(part.part_id)}
                            workOrderId={part.work_order_id ? String(part.work_order_id) : undefined}
                            qualityReportIds={part.quality_report_id ? [String(part.quality_report_id)] : []}
                            initialView={a.default_view ?? null}
                            className="rounded border"
                            showHeader={false}
                            startExpanded
                        />
                    ) : (
                        // Operator preview without a bound part: show the model
                        // read-only at the saved framing. Defect capture turns
                        // on once a part is bound at runtime.
                        <AnnotationFramingViewer
                            modelId={String(a.model_id)}
                            defaultView={a.default_view ?? null}
                            instructions="Preview — operators place defects here once a part is bound."
                        />
                    )
                ) : hasModel ? (
                    // Authoring: frame the inspection view + save it as default.
                    <AnnotationFramingViewer
                        modelId={String(a.model_id)}
                        defaultView={a.default_view ?? null}
                        onSaveView={(view) => updateAttributes({ default_view: view })}
                    />
                ) : (
                    <div className="flex h-24 flex-col items-center justify-center rounded border border-dashed text-center text-xs text-muted-foreground">
                        Pick a 3D model in the properties panel.
                    </div>
                )}
            </div>
        </NodeCard>
    );

    return (
        <NodeViewWrapper className="my-3 not-prose">
            <AuthoringPopover isEditable={editor.isEditable} nodeId={a.node_id}>{card}</AuthoringPopover>
        </NodeViewWrapper>
    );
}

export const PartAnnotation = Node.create({
    name: "partAnnotation",
    group: "block",
    atom: true,
    selectable: true,
    draggable: true,
    addAttributes() {
        return {
            node_id: { default: "" },
            label: { default: "Part annotation" },
            model_id: { default: "" },
            required: { default: false },
            default_view: { default: null as SavedView | null, renderHTML: () => ({}) },
        };
    },
    parseHTML() {
        return [{ tag: 'div[data-type="part-annotation"]' }];
    },
    renderHTML({ HTMLAttributes }) {
        return [
            "div",
            mergeAttributes(HTMLAttributes, { "data-type": "part-annotation" }),
            `[ANNOTATE] ${HTMLAttributes.label || ""} (model ${HTMLAttributes.model_id || "?"})`,
        ];
    },
    addNodeView() {
        return ReactNodeViewRenderer(View);
    },
});

export const SAMPLE_PART_ANNOTATION = {
    type: "partAnnotation",
    attrs: {
        // Left empty on purpose — withFreshNodeId() mints a UUIDv7 on insert
        // (partAnnotation is in CAPTURE_NODE_TYPES). A hardcoded id here would
        // make every inserted node collide.
        node_id: "",
        label: "Place defect annotations on the 3D model",
        model_id: "",
        required: false,
        default_view: null,
    },
};
