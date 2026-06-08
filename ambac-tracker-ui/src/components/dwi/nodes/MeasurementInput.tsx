/**
 * MeasurementInput — active numeric capture. Engineer authors the spec
 * (nominal/tolerance/unit) or links to a `MeasurementDefinition` via the
 * Linked spec dropdown which autofills the rest. Operator sees a numeric
 * input and a live in-spec / out-of-spec badge.
 */
import { useEffect, useRef } from "react";
import { Node, mergeAttributes } from "@tiptap/core";
import {
    NodeViewWrapper,
    ReactNodeViewRenderer,
    type NodeViewProps,
} from "@tiptap/react";
import { Ruler } from "lucide-react";
import { toast } from "sonner";
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
import { useRetrieveMeasurementDefinitions } from "@/hooks/useRetrieveMeasurementDefinitions";

type Attrs = {
    node_id: string;
    label: string;
    unit: string;
    nominal: number | null;
    upper_tol: number | null;
    lower_tol: number | null;
    required: boolean;
    characteristic_number: string;
    measurement_definition_id: string | null;
};

type MeasurementDefShape = {
    id: string | number;
    label?: string | null;
    unit?: string | null;
    nominal?: number | null;
    upper_tol?: number | null;
    lower_tol?: number | null;
};

export function MeasurementInputEditForm({ node, updateAttributes }: NodeViewProps) {
    const a = node.attrs as Attrs;
    const update = useDebouncedAttrs(updateAttributes, 250);
    const { data: defsResp } = useRetrieveMeasurementDefinitions();
    const defs = (defsResp?.results ?? []) as MeasurementDefShape[];

    const pickDefinition = (id: string) => {
        const def = defs.find((d) => String(d.id) === id);
        if (!def) return;
        // Atomic write — linked-spec picks bypass the debounce so all fields
        // hit the doc in one transaction.
        updateAttributes({
            measurement_definition_id: String(def.id),
            label: def.label ?? "",
            unit: def.unit ?? "",
            nominal: def.nominal ?? null,
            upper_tol: def.upper_tol ?? null,
            lower_tol: def.lower_tol ?? null,
        });
    };

    return (
        <div className="space-y-3">
            <div className="space-y-1">
                <Label className="text-xs">Linked measurement spec</Label>
                <Select
                    value={a.measurement_definition_id ?? ""}
                    onValueChange={(v) => v && pickDefinition(v)}
                >
                    <SelectTrigger className="h-8 text-sm">
                        <SelectValue placeholder="— pick to autofill —" />
                    </SelectTrigger>
                    <SelectContent>
                        {defs.map((d) => (
                            <SelectItem key={String(d.id)} value={String(d.id)} className="text-sm">
                                {d.label ?? `Measurement ${d.id}`}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>
                {a.measurement_definition_id && (
                    <button
                        type="button"
                        onClick={() => updateAttributes({ measurement_definition_id: null })}
                        className="text-[10px] text-muted-foreground hover:underline"
                    >
                        Unlink (keep fields)
                    </button>
                )}
            </div>

            <TextAttrRow attrName="label" label="Label" initial={a.label} update={update} />
            <TextAttrRow attrName="characteristic_number" label="Characteristic" initial={a.characteristic_number} update={update} monospace />
            <TextAttrRow attrName="unit" label="Unit" initial={a.unit} update={update} />

            <DecimalAttrInput attrName="nominal" label="Nominal" initial={a.nominal} update={update} />
            <DecimalAttrInput attrName="upper_tol" label="+ Tol" initial={a.upper_tol} update={update} />
            <DecimalAttrInput attrName="lower_tol" label="− Tol" initial={a.lower_tol} update={update} />

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
    const { label, unit, nominal, upper_tol, lower_tol, required, characteristic_number } = a;
    const isOperator = !editor.isEditable;
    const { value, setValue } = useOperatorResponse(a.node_id);

    const rawValue = typeof value === "string" ? value : "";
    const parsedValue = rawValue === "" ? null : Number(rawValue);
    const numericValid = parsedValue != null && Number.isFinite(parsedValue);
    const inSpec =
        isOperator && numericValid && nominal != null
            ? parsedValue! >= nominal - (lower_tol ?? 0) &&
              parsedValue! <= nominal + (upper_tol ?? 0)
            : null;

    // Flow #3: surface an OOS toast exactly once when the operator's
    // committed value crosses from in-spec (or empty) to out-of-spec.
    // The operator continues; QA dispositions later. We don't disposition
    // here — operators aren't authorized.
    const lastOOSValueRef = useRef<string | null>(null);
    useEffect(() => {
        if (!isOperator) return;
        if (inSpec === false && rawValue !== lastOOSValueRef.current) {
            lastOOSValueRef.current = rawValue;
            toast.warning(`${label || "Measurement"} out of spec — flagged for QA review.`, {
                description: "You can continue. A QA inspector will disposition.",
            });
        } else if (inSpec !== false) {
            lastOOSValueRef.current = null;
        }
    }, [inSpec, rawValue, isOperator, label]);

    const card = (
        <NodeCard
            icon={<Ruler className="h-4 w-4 text-muted-foreground" />}
            label={label || "Measurement Input"}
            badges={
                <>
                    {characteristic_number && (
                        <Badge variant="outline" className="font-mono text-[10px]">
                            {characteristic_number}
                        </Badge>
                    )}
                    {required && <Badge variant="secondary" className="text-[10px]">Required</Badge>}
                    {inSpec === true && (
                        <Badge className="bg-green-600 text-[10px] text-white">In spec</Badge>
                    )}
                    {inSpec === false && (
                        <Badge variant="destructive" className="text-[10px]">Out of spec</Badge>
                    )}
                </>
            }
            rightSlot={
                nominal != null
                    ? `${nominal}${upper_tol != null ? ` +${upper_tol}` : ""}${
                          lower_tol != null ? ` −${lower_tol}` : ""
                      }${unit ? ` ${unit}` : ""}`
                    : "no target"
            }
        >
            <div className="flex items-center gap-2" contentEditable={false}>
                <input
                    type="text"
                    inputMode="decimal"
                    disabled={!isOperator}
                    placeholder="—"
                    value={rawValue}
                    onChange={(e) => isOperator && setValue(e.target.value)}
                    className="w-32 rounded border bg-background px-2 py-1 text-sm font-mono"
                />
                {unit && <span className="text-sm text-muted-foreground">{unit}</span>}
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

export const MeasurementInput = Node.create({
    name: "measurementInput",
    group: "block",
    atom: true,
    selectable: true,
    draggable: true,
    addAttributes() {
        return {
            node_id: { default: "" },
            label: { default: "" },
            unit: { default: "" },
            nominal: { default: null },
            upper_tol: { default: null },
            lower_tol: { default: null },
            required: { default: true },
            characteristic_number: { default: "" },
            measurement_definition_id: { default: null },
        };
    },
    parseHTML() {
        return [{ tag: 'div[data-type="measurement-input"]' }];
    },
    renderHTML({ HTMLAttributes }) {
        return [
            "div",
            mergeAttributes(HTMLAttributes, { "data-type": "measurement-input" }),
            `${HTMLAttributes.label || "Measurement"}: ___ ${HTMLAttributes.unit || ""}`,
        ];
    },
    addNodeView() {
        return ReactNodeViewRenderer(View);
    },
});

export const SAMPLE_MEASUREMENT_INPUT = {
    type: "measurementInput",
    attrs: {
        node_id: "seed-meas-input-1",
        label: "OD measurement (record actual)",
        unit: "in",
        nominal: 1.247,
        upper_tol: 0.002,
        lower_tol: 0.002,
        required: true,
        characteristic_number: "B12",
    },
};
