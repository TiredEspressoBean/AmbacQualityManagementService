/** ScanInput — barcode / QR text capture (free-text in spike, scanner-aware
 * input in production). */
import { Node, mergeAttributes } from "@tiptap/core";
import {
    NodeViewWrapper,
    ReactNodeViewRenderer,
    type NodeViewProps,
} from "@tiptap/react";
import { ScanLine } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { NodeCard } from "../shared/NodeCard";
import { AuthoringPopover } from "../shared/AuthoringPopover";
import { useDebouncedAttrs } from "../shared/useDebouncedAttrs";
import { TextAttrRow } from "../shared/AttrInputs";
import { useOperatorResponse } from "../shared/OperatorResponseContext";

type Attrs = { node_id: string; label: string; required: boolean };

export function ScanInputEditForm({ node, updateAttributes }: NodeViewProps) {
    const a = node.attrs as Attrs;
    const update = useDebouncedAttrs(updateAttributes, 250);
    return (
        <div className="space-y-3">
            <TextAttrRow attrName="label" label="Label" initial={a.label} update={update} />
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
    const isOperator = !editor.isEditable;
    const { value, setValue } = useOperatorResponse(a.node_id);
    const v = typeof value === "string" ? value : "";

    const card = (
        <NodeCard
            icon={<ScanLine className="h-4 w-4 text-muted-foreground" />}
            label={a.label || "Scan"}
            badges={
                <>
                    <Badge variant="outline" className="text-[10px]">Barcode / QR</Badge>
                    {a.required && <Badge variant="secondary" className="text-[10px]">Required</Badge>}
                    {isOperator && v && (
                        <Badge variant="default" className="text-[10px]">Captured ✓</Badge>
                    )}
                </>
            }
        >
            <div contentEditable={false}>
                <input
                    type="text"
                    disabled={!isOperator}
                    placeholder="Scan into field…"
                    value={v}
                    onChange={(e) => isOperator && setValue(e.target.value)}
                    className="w-full rounded border bg-background px-2 py-1 font-mono text-sm"
                />
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

export const ScanInput = Node.create({
    name: "scanInput",
    group: "block",
    atom: true,
    selectable: true,
    draggable: true,
    addAttributes() {
        return { node_id: { default: "" }, label: { default: "" }, required: { default: false } };
    },
    parseHTML() {
        return [{ tag: 'div[data-type="scan-input"]' }];
    },
    renderHTML({ HTMLAttributes }) {
        return [
            "div",
            mergeAttributes(HTMLAttributes, { "data-type": "scan-input" }),
            `[SCAN] ${HTMLAttributes.label || ""}`,
        ];
    },
    addNodeView() {
        return ReactNodeViewRenderer(View);
    },
});

export const SAMPLE_SCAN = {
    type: "scanInput",
    attrs: { node_id: "seed-scan-1", label: "Scan tool barcode", required: true },
};
