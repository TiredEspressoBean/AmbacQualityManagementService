/**
 * QualityStatusField — operator picks PASS / FAIL / PENDING for the
 * substep's inspection event. Maps to `QualityReports.status` when the
 * containing substep has `is_inspection_point=True`.
 *
 * Engineer authoring: label, required, allowed values (default all three).
 * Operator capture: single status string.
 */
import { Node, mergeAttributes } from "@tiptap/core";
import {
    NodeViewWrapper,
    ReactNodeViewRenderer,
    type NodeViewProps,
} from "@tiptap/react";
import { ShieldCheck, ShieldAlert, ShieldQuestion } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { NodeCard } from "../shared/NodeCard";
import { AuthoringPopover } from "../shared/AuthoringPopover";
import { useDebouncedAttrs } from "../shared/useDebouncedAttrs";
import { TextAttrRow } from "../shared/AttrInputs";
import { useOperatorResponse } from "../shared/OperatorResponseContext";

type Status = "PASS" | "FAIL" | "PENDING";

type Attrs = {
    node_id: string;
    label: string;
    required: boolean;
    allowed: Status[];
};

const STATUS_META: Record<Status, { label: string; icon: React.ComponentType<{ className?: string }>; cls: string }> = {
    PASS: { label: "Pass", icon: ShieldCheck, cls: "bg-green-600 text-white" },
    FAIL: { label: "Fail", icon: ShieldAlert, cls: "bg-destructive text-destructive-foreground" },
    PENDING: { label: "Pending", icon: ShieldQuestion, cls: "bg-amber-500 text-white" },
};
const ALL_STATUSES: Status[] = ["PASS", "FAIL", "PENDING"];

export function QualityStatusFieldEditForm({ node, updateAttributes }: NodeViewProps) {
    const a = node.attrs as Attrs;
    const update = useDebouncedAttrs(updateAttributes, 250);
    const allowed = new Set(Array.isArray(a.allowed) ? a.allowed : ALL_STATUSES);
    const toggle = (s: Status) => {
        const next = new Set(allowed);
        if (next.has(s)) next.delete(s);
        else next.add(s);
        // Keep at least one allowed value so the operator always has a choice.
        if (next.size === 0) return;
        updateAttributes({ allowed: ALL_STATUSES.filter((x) => next.has(x)) });
    };
    return (
        <div className="space-y-3">
            <TextAttrRow attrName="label" label="Label" initial={a.label} update={update} />
            <div className="space-y-1">
                <Label className="text-xs">Allowed values</Label>
                <div className="grid grid-cols-3 gap-1">
                    {ALL_STATUSES.map((s) => (
                        <button
                            key={s}
                            type="button"
                            onClick={() => toggle(s)}
                            className={`rounded border px-2 py-1 text-xs ${
                                allowed.has(s) ? STATUS_META[s].cls : "text-muted-foreground"
                            }`}
                        >
                            {STATUS_META[s].label}
                        </button>
                    ))}
                </div>
            </div>
            <div className="flex items-center justify-between border-t pt-2">
                <Label className="text-xs">Required</Label>
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
    const { value, setValue } = useOperatorResponse(a.node_id);
    const allowed = (Array.isArray(a.allowed) && a.allowed.length > 0
        ? a.allowed
        : ALL_STATUSES) as Status[];
    const v = (typeof value === "string" ? value : "") as Status | "";

    const card = (
        <NodeCard
            icon={<ShieldCheck className="h-4 w-4 text-muted-foreground" />}
            label={a.label || "Quality status"}
            badges={
                <>
                    {a.required && <Badge variant="secondary" className="text-[10px]">Required</Badge>}
                    {isOperator && v && (
                        <Badge className={`text-[10px] ${STATUS_META[v as Status].cls}`}>
                            {STATUS_META[v as Status].label}
                        </Badge>
                    )}
                </>
            }
        >
            <div className="flex gap-1.5" contentEditable={false}>
                {allowed.map((s) => {
                    const Icon = STATUS_META[s].icon;
                    const active = v === s;
                    return (
                        <button
                            key={s}
                            type="button"
                            disabled={!isOperator}
                            onClick={() => isOperator && setValue(s)}
                            className={`flex flex-1 items-center justify-center gap-1.5 rounded border px-3 py-2 text-sm transition ${
                                active
                                    ? STATUS_META[s].cls
                                    : "bg-background hover:bg-muted disabled:opacity-60"
                            }`}
                        >
                            <Icon className="h-4 w-4" />
                            {STATUS_META[s].label}
                        </button>
                    );
                })}
            </div>
        </NodeCard>
    );

    return (
        <NodeViewWrapper className="my-3 not-prose">
            <AuthoringPopover isEditable={editor.isEditable} nodeId={a.node_id}>{card}</AuthoringPopover>
        </NodeViewWrapper>
    );
}

export const QualityStatusField = Node.create({
    name: "qualityStatusField",
    group: "block",
    atom: true,
    selectable: true,
    draggable: true,
    addAttributes() {
        return {
            node_id: { default: "" },
            label: { default: "Inspection status" },
            required: { default: true },
            allowed: { default: ALL_STATUSES },
        };
    },
    parseHTML() {
        return [{ tag: 'div[data-type="quality-status-field"]' }];
    },
    renderHTML({ HTMLAttributes }) {
        return [
            "div",
            mergeAttributes(HTMLAttributes, { "data-type": "quality-status-field" }),
            `[STATUS] ${HTMLAttributes.label || "Inspection status"}`,
        ];
    },
    addNodeView() {
        return ReactNodeViewRenderer(View);
    },
});

export const SAMPLE_QUALITY_STATUS = {
    type: "qualityStatusField",
    attrs: {
        node_id: "seed-status-1",
        label: "Inspection result",
        required: true,
        allowed: ALL_STATUSES,
    },
};
