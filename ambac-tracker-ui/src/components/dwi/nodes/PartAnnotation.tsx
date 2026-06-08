/**
 * PartAnnotation — embeds the existing 3D `PartAnnotator` widget inside a
 * substep so operators can place defect annotations against the part
 * directly in the work flow. Maps to `HeatMapAnnotation` rows; when the
 * substep is an inspection point, captured annotations link to the
 * pending `QualityReports` via the existing `qualityReportIds` prop on
 * `PartAnnotator`.
 *
 * Engineer authoring: pick the 3D model (model_id), label, required flag,
 * optional `defect_type_filter` to restrict which error types operators
 * can pick.
 * Operator capture: handled entirely by `PartAnnotator` (it persists
 * annotations directly via its own hooks). The operator-runtime layer
 * provides `part_id` + `work_order_id` + `quality_report_id` via
 * `PartContext`; when the context is missing (authoring spike) we render
 * a placeholder.
 */
import { Node, mergeAttributes } from "@tiptap/core";
import {
    NodeViewWrapper,
    ReactNodeViewRenderer,
    type NodeViewProps,
} from "@tiptap/react";
import { ScanSearch } from "lucide-react";
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
import { PartAnnotator } from "@/pages/PartAnnotator";

type Attrs = {
    node_id: string;
    label: string;
    model_id: string;
    required: boolean;
};

type ThreeDModel = { id: string | number; name?: string; part_type?: { name?: string } };

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
    const { node, editor } = props;
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
                {isOperator && hasModel && hasPartBinding ? (
                    // Live embed — PartAnnotator owns persistence (writes
                    // `HeatMapAnnotation` rows linked to the bound part and
                    // the pre-bound QualityReport when present). When the
                    // QR isn't ready yet (substep hasn't been submitted on
                    // this part yet), the widget falls into its standalone
                    // QR-picker behavior — which surfaces a list of failed
                    // QRs on the WO. For most operator-runtime workflows,
                    // the QR is pre-bound by the runtime's eager
                    // ensure-inspection-qr call.
                    <PartAnnotator
                        modelId={String(a.model_id)}
                        partId={String(part.part_id)}
                        workOrderId={part.work_order_id ? String(part.work_order_id) : undefined}
                        qualityReportIds={part.quality_report_id ? [String(part.quality_report_id)] : []}
                        className="rounded border"
                        showHeader={false}
                        startExpanded
                    />
                ) : (
                    <div className="flex h-24 flex-col items-center justify-center rounded border border-dashed text-center text-xs text-muted-foreground">
                        {!hasModel ? (
                            <>Pick a 3D model in the properties panel.</>
                        ) : !hasPartBinding ? (
                            <>3D annotator will load when a part is bound (operator runtime).</>
                        ) : (
                            <>Annotator ready.</>
                        )}
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
        node_id: "seed-part-annotation-1",
        label: "Place defect annotations on the 3D model",
        model_id: "",
        required: false,
    },
};
