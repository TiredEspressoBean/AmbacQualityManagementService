/**
 * MeasurementSpec — read-only measurement target reference (the "spec" itself,
 * not a capture). Attributes mirror the `MeasurementDefinition` model at
 * PartsTracker/Tracker/models/mes_lite.py:309.
 */
import { Node, mergeAttributes } from "@tiptap/core";
import {
    NodeViewWrapper,
    ReactNodeViewRenderer,
    type NodeViewProps,
} from "@tiptap/react";
import { Gauge } from "lucide-react";
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
import { AuthoringPopover } from "../shared/AuthoringPopover";
import { useDebouncedAttrs } from "../shared/useDebouncedAttrs";
import {
    DecimalAttrInput,
    TextAttrRow,
} from "../shared/AttrInputs";

type MeasurementSpecAttrs = {
    label: string;
    type: "NUMERIC" | "PASS_FAIL";
    unit: string;
    nominal: number | null;
    upper_tol: number | null;
    lower_tol: number | null;
    required: boolean;
    characteristic_number: string;
};

export function MeasurementSpecEditForm({ node, updateAttributes }: NodeViewProps) {
    const a = node.attrs as MeasurementSpecAttrs;
    const update = useDebouncedAttrs(updateAttributes, 250);
    return (
        <div className="space-y-3">
            <div className="space-y-1">
                <Label className="text-xs">Kind</Label>
                <Select
                    value={a.type}
                    onValueChange={(v) => updateAttributes({ type: v })}
                >
                    <SelectTrigger className="h-8 text-sm">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="NUMERIC">Numeric</SelectItem>
                        <SelectItem value="PASS_FAIL">Pass / Fail</SelectItem>
                    </SelectContent>
                </Select>
            </div>
            <TextAttrRow attrName="label" label="Label" initial={a.label} update={update} />
            <TextAttrRow attrName="characteristic_number" label="Characteristic" initial={a.characteristic_number} update={update} monospace />
            <TextAttrRow attrName="unit" label="Unit" initial={a.unit} update={update} />
            {a.type === "NUMERIC" && (
                <>
                    <DecimalAttrInput attrName="nominal" label="Nominal" initial={a.nominal} update={update} />
                    <DecimalAttrInput attrName="upper_tol" label="+ Tol" initial={a.upper_tol} update={update} />
                    <DecimalAttrInput attrName="lower_tol" label="− Tol" initial={a.lower_tol} update={update} />
                </>
            )}
            <div className="flex items-center justify-between border-t pt-2">
                <Label htmlFor="spec-required" className="text-xs">Required</Label>
                <Switch
                    id="spec-required"
                    checked={a.required}
                    onCheckedChange={(checked) => updateAttributes({ required: checked })}
                />
            </div>
        </div>
    );
}

function View(props: NodeViewProps) {
    const { node, editor } = props;
    const a = node.attrs as MeasurementSpecAttrs;
    const tolerance =
        a.type === "NUMERIC" && a.nominal != null
            ? `${a.nominal}${a.upper_tol != null ? ` +${a.upper_tol}` : ""}${
                  a.lower_tol != null ? ` −${a.lower_tol}` : ""
              }${a.unit ? ` ${a.unit}` : ""}`
            : null;

    const card = (
        <div className="rounded-md border bg-muted/30 p-3">
            <div className="flex flex-wrap items-center gap-2">
                <Gauge className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium">{a.label || "Untitled measurement"}</span>
                {a.characteristic_number && (
                    <Badge variant="outline" className="font-mono text-[10px]">
                        {a.characteristic_number}
                    </Badge>
                )}
                {a.required && (
                    <Badge variant="secondary" className="text-[10px]">Required</Badge>
                )}
                <span className="ml-auto text-xs text-muted-foreground">
                    {a.type === "NUMERIC" ? "Numeric" : "Pass / Fail"}
                </span>
            </div>
            {tolerance && (
                <div className="mt-2 font-mono text-sm tabular-nums">{tolerance}</div>
            )}
        </div>
    );

    return (
        <NodeViewWrapper className="my-3 not-prose">
            <AuthoringPopover isEditable={editor.isEditable}>
                {card}
            </AuthoringPopover>
        </NodeViewWrapper>
    );
}

export const MeasurementSpec = Node.create({
    name: "measurementSpec",
    group: "block",
    atom: true,
    selectable: true,
    draggable: true,

    addAttributes() {
        return {
            label: { default: "" },
            type: { default: "NUMERIC" },
            unit: { default: "" },
            nominal: { default: null },
            upper_tol: { default: null },
            lower_tol: { default: null },
            required: { default: true },
            characteristic_number: { default: "" },
        };
    },

    parseHTML() {
        return [{ tag: 'div[data-type="measurement-spec"]' }];
    },

    renderHTML({ HTMLAttributes }) {
        return [
            "div",
            mergeAttributes(HTMLAttributes, {
                "data-type": "measurement-spec",
                class: "my-3 rounded-md border bg-muted/30 p-3 font-mono text-sm",
            }),
            `${HTMLAttributes.label || "Measurement"}: ${HTMLAttributes.nominal ?? "?"}${
                HTMLAttributes.upper_tol ? ` +${HTMLAttributes.upper_tol}` : ""
            }${HTMLAttributes.lower_tol ? ` −${HTMLAttributes.lower_tol}` : ""}${
                HTMLAttributes.unit ? ` ${HTMLAttributes.unit}` : ""
            }`,
        ];
    },

    addNodeView() {
        return ReactNodeViewRenderer(View);
    },
});

export const SAMPLE_MEASUREMENT_SPEC = {
    type: "measurementSpec",
    attrs: {
        label: "Outer Diameter",
        type: "NUMERIC",
        unit: "in",
        nominal: 1.247,
        upper_tol: 0.002,
        lower_tol: 0.002,
        required: true,
        characteristic_number: "B12",
    },
};
