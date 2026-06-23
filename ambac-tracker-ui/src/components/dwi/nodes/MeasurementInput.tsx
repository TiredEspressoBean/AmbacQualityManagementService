/**
 * MeasurementInput — active numeric capture. Engineer authors the spec
 * (nominal/tolerance/unit) or links to a `MeasurementDefinition` via the
 * Linked spec dropdown which autofills the rest. Operator sees a numeric
 * input and a live in-spec / out-of-spec badge.
 */
import { useRef, useState } from "react";
import { Node, mergeAttributes } from "@tiptap/core";
import {
    NodeViewWrapper,
    ReactNodeViewRenderer,
    type NodeViewProps,
} from "@tiptap/react";
import { Ruler, Check, ChevronsUpDown } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover";
import {
    Command,
    CommandEmpty,
    CommandGroup,
    CommandInput,
    CommandItem,
    CommandList,
} from "@/components/ui/command";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { NodeCard } from "../shared/NodeCard";
import { AuthoringPopover } from "../shared/AuthoringPopover";
import { useDebouncedAttrs } from "../shared/useDebouncedAttrs";
import { DecimalAttrInput, TextAttrRow } from "../shared/AttrInputs";
import { useOperatorResponse } from "../shared/OperatorResponseContext";
import { useSubstepAuthoringContext } from "../shared/SubstepAuthoringContext";
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
    /** "NUMERIC" → operator types a value; "PASS_FAIL" → operator picks Pass/Fail. */
    measurement_type: string;
};

type MeasurementDefShape = {
    id: string | number;
    label?: string | null;
    unit?: string | null;
    nominal?: number | null;
    upper_tol?: number | null;
    lower_tol?: number | null;
    type?: string | null;
};

export function MeasurementInputEditForm({ node, updateAttributes }: NodeViewProps) {
    const a = node.attrs as Attrs;
    const update = useDebouncedAttrs(updateAttributes, 250);
    const isPassFail = a.measurement_type === "PASS_FAIL";
    // Scope the linked-spec dropdown to the step being authored — a measurement
    // belongs to exactly one step, so offering specs from other steps lets an
    // author wire up the wrong characteristic. (Falls back to unscoped only on
    // the spike page, which has no step context.)
    const { stepId } = useSubstepAuthoringContext();
    const { data: defsResp } = useRetrieveMeasurementDefinitions(
        stepId ? { step: stepId } : undefined,
    );
    const defs = (defsResp?.results ?? []) as MeasurementDefShape[];
    const [pickerOpen, setPickerOpen] = useState(false);

    const defLabel = (d: MeasurementDefShape) => d.label ?? `Measurement ${d.id}`;
    const selectedDef = defs.find(
        (d) => String(d.id) === a.measurement_definition_id,
    );

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
            measurement_type: def.type ?? "NUMERIC",
        });
    };

    return (
        <div className="space-y-3">
            <div className="space-y-1">
                <Label className="text-xs">Linked measurement spec</Label>
                <Popover open={pickerOpen} onOpenChange={setPickerOpen}>
                    <PopoverTrigger asChild>
                        <Button
                            variant="outline"
                            role="combobox"
                            aria-expanded={pickerOpen}
                            className="h-8 w-full justify-between text-sm font-normal"
                        >
                            <span className={cn("truncate", !selectedDef && "text-muted-foreground")}>
                                {selectedDef ? defLabel(selectedDef) : "— pick to autofill —"}
                            </span>
                            <ChevronsUpDown className="ml-2 h-3.5 w-3.5 shrink-0 opacity-50" />
                        </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-[260px] p-0" align="start">
                        <Command>
                            <CommandInput placeholder="Search measurements…" className="text-sm" />
                            <CommandList>
                                <CommandEmpty>No measurements for this step.</CommandEmpty>
                                <CommandGroup>
                                    {defs.map((d) => (
                                        <CommandItem
                                            key={String(d.id)}
                                            value={defLabel(d)}
                                            onSelect={() => {
                                                pickDefinition(String(d.id));
                                                setPickerOpen(false);
                                            }}
                                            className="text-sm"
                                        >
                                            <Check
                                                className={cn(
                                                    "mr-2 h-3.5 w-3.5",
                                                    a.measurement_definition_id === String(d.id)
                                                        ? "opacity-100"
                                                        : "opacity-0",
                                                )}
                                            />
                                            {defLabel(d)}
                                        </CommandItem>
                                    ))}
                                </CommandGroup>
                            </CommandList>
                        </Command>
                    </PopoverContent>
                </Popover>
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

            <div className="flex items-center justify-between">
                <Label className="text-xs">Pass / Fail spec</Label>
                <Switch
                    checked={isPassFail}
                    onCheckedChange={(checked) =>
                        updateAttributes({ measurement_type: checked ? "PASS_FAIL" : "NUMERIC" })
                    }
                />
            </div>

            {!isPassFail && (
                <>
                    <TextAttrRow attrName="unit" label="Unit" initial={a.unit} update={update} />
                    <DecimalAttrInput attrName="nominal" label="Nominal" initial={a.nominal} update={update} />
                    <DecimalAttrInput attrName="upper_tol" label="+ Tol" initial={a.upper_tol} update={update} />
                    <DecimalAttrInput attrName="lower_tol" label="− Tol" initial={a.lower_tol} update={update} />
                </>
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
    const { label, unit, nominal, upper_tol, lower_tol, required, characteristic_number } = a;
    const isPassFail = a.measurement_type === "PASS_FAIL";
    const isOperator = !editor.isEditable;
    const { value, setValue } = useOperatorResponse(a.node_id);

    const rawValue = typeof value === "string" ? value : "";
    // in-spec: pass/fail → "PASS" passes; numeric → within nominal ± tolerance.
    let inSpec: boolean | null = null;
    if (isOperator && rawValue) {
        if (isPassFail) {
            inSpec = rawValue === "PASS";
        } else {
            const parsedValue = Number(rawValue);
            inSpec =
                Number.isFinite(parsedValue) && nominal != null
                    ? parsedValue >= nominal - (lower_tol ?? 0) &&
                      parsedValue <= nominal + (upper_tol ?? 0)
                    : null;
        }
    }

    // Flow #3: surface an OOS warning when the operator LEAVES the field
    // (on blur) — NOT per keystroke, which stacked a toast for every
    // intermediate value while typing (1 → 12 → 128). The operator continues;
    // QA dispositions later — we don't disposition here (operators aren't
    // authorized). The ref de-dupes repeated blurs on an unchanged value.
    const lastOOSValueRef = useRef<string | null>(null);
    const handleOperatorBlur = () => {
        if (!isOperator) return;
        if (inSpec === false && rawValue !== lastOOSValueRef.current) {
            lastOOSValueRef.current = rawValue;
            toast.warning(`${label || "Measurement"} out of spec — flagged for QA review.`, {
                description: "You can continue. A QA inspector will disposition.",
            });
        } else if (inSpec !== false) {
            lastOOSValueRef.current = null;
        }
    };

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
                isPassFail
                    ? "Pass / Fail"
                    : nominal != null
                        ? `${nominal}${upper_tol != null ? ` +${upper_tol}` : ""}${
                              lower_tol != null ? ` −${lower_tol}` : ""
                          }${unit ? ` ${unit}` : ""}`
                        : "no target"
            }
        >
            <div className="flex items-center gap-2" contentEditable={false}>
                {isPassFail ? (
                    <Select
                        value={rawValue}
                        disabled={!isOperator}
                        onValueChange={(v) => {
                            if (!isOperator) return;
                            setValue(v);
                            if (v === "FAIL") {
                                toast.warning(
                                    `${label || "Measurement"} failed — flagged for QA review.`,
                                    { description: "You can continue. A QA inspector will disposition." },
                                );
                            }
                        }}
                    >
                        <SelectTrigger className="h-8 w-32 text-sm">
                            <SelectValue placeholder="—" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="PASS">Pass</SelectItem>
                            <SelectItem value="FAIL">Fail</SelectItem>
                        </SelectContent>
                    </Select>
                ) : (
                    <>
                        <input
                            type="text"
                            inputMode="decimal"
                            disabled={!isOperator}
                            placeholder="—"
                            value={rawValue}
                            onChange={(e) => isOperator && setValue(e.target.value)}
                            onBlur={handleOperatorBlur}
                            className="w-32 rounded border bg-background px-2 py-1 text-sm font-mono"
                        />
                        {unit && <span className="text-sm text-muted-foreground">{unit}</span>}
                    </>
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
            measurement_type: { default: "NUMERIC" },
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
