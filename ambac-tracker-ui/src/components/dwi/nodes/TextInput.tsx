/** TextInput — short single-line or long textarea capture. */
import { Node, mergeAttributes } from "@tiptap/core";
import {
    NodeViewWrapper,
    ReactNodeViewRenderer,
    type NodeViewProps,
} from "@tiptap/react";
import { Type } from "lucide-react";
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
import { useOperatorResponse } from "../shared/OperatorResponseContext";

type Kind = "short" | "long";
type Attrs = {
    node_id: string;
    label: string;
    kind: Kind;
    placeholder: string;
    required: boolean;
};

export function TextInputEditForm({ node, updateAttributes }: NodeViewProps) {
    const a = node.attrs as Attrs;
    const update = useDebouncedAttrs(updateAttributes, 250);
    return (
        <div className="space-y-3">
            <div className="space-y-1">
                <Label className="text-xs">Kind</Label>
                <Select
                    value={a.kind}
                    onValueChange={(v) => updateAttributes({ kind: v })}
                >
                    <SelectTrigger className="h-8 text-sm">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="short">Short (single line)</SelectItem>
                        <SelectItem value="long">Long (textarea)</SelectItem>
                    </SelectContent>
                </Select>
            </div>
            <TextAttrRow attrName="label" label="Label" initial={a.label} update={update} />
            <TextAttrRow attrName="placeholder" label="Placeholder" initial={a.placeholder} update={update} />
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
    const kind = (a.kind ?? "short") as Kind;
    const required = a.required === true;
    const isOperator = !editor.isEditable;
    const { value, setValue } = useOperatorResponse(a.node_id);
    const v = typeof value === "string" ? value : "";

    const card = (
        <NodeCard
            icon={<Type className="h-4 w-4 text-muted-foreground" />}
            label={a.label || "Text input"}
            badges={
                <>
                    <Badge variant="outline" className="text-[10px] capitalize">{kind}</Badge>
                    {required && <Badge variant="secondary" className="text-[10px]">Required</Badge>}
                    {isOperator && v && (
                        <Badge variant="default" className="text-[10px]">Captured ✓</Badge>
                    )}
                </>
            }
        >
            <div contentEditable={false}>
                {kind === "short" ? (
                    <input
                        type="text"
                        disabled={!isOperator}
                        placeholder={a.placeholder || "—"}
                        value={v}
                        onChange={(e) => isOperator && setValue(e.target.value)}
                        className="w-full rounded border bg-background px-2 py-1 text-sm"
                    />
                ) : (
                    <textarea
                        disabled={!isOperator}
                        rows={3}
                        placeholder={a.placeholder || "—"}
                        value={v}
                        onChange={(e) => isOperator && setValue(e.target.value)}
                        className="w-full rounded border bg-background px-2 py-1 text-sm"
                    />
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

export const TextInput = Node.create({
    name: "textInput",
    group: "block",
    atom: true,
    selectable: true,
    draggable: true,
    addAttributes() {
        return {
            node_id: { default: "" },
            label: { default: "" },
            kind: { default: "short" },
            placeholder: { default: "" },
            required: { default: false },
        };
    },
    parseHTML() {
        return [{ tag: 'div[data-type="text-input"]' }];
    },
    renderHTML({ HTMLAttributes }) {
        return [
            "div",
            mergeAttributes(HTMLAttributes, { "data-type": "text-input" }),
            `${HTMLAttributes.label || "Text"}: ___`,
        ];
    },
    addNodeView() {
        return ReactNodeViewRenderer(View);
    },
});

export const SAMPLE_TEXT_INPUT_SHORT = {
    type: "textInput",
    attrs: {
        node_id: "seed-text-short-1",
        label: "Material lot #",
        kind: "short",
        placeholder: "e.g. LOT-2026-04421",
        required: true,
    },
};

export const SAMPLE_TEXT_INPUT_LONG = {
    type: "textInput",
    attrs: {
        node_id: "seed-text-long-1",
        label: "Setup notes",
        kind: "long",
        placeholder: "Anything unusual?",
        required: false,
    },
};
