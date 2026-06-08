/** HarvestedComponentCapture — reman teardown DWI node.
 *
 * Engineer authors the node into a teardown substep. Operator runtime resolves
 * the Core from the parent StepExecution, enumerates rows from
 * DisassemblyBOMLine (or a manual component-type list), and captures
 * condition_grade / position / condition_notes per row. The submit handler
 * routes captures through `services.dwi.harvested_component_capture` which
 * creates HarvestedComponent rows + dispatches scrap_component for SCRAP rows.
 *
 * v1 scope:
 * - Authoring UI for enumerate_from + strict_enumeration toggles.
 * - Operator runtime: row table, grade Select per row, position + notes
 *   inputs, missing toggle, "add unexpected component" button.
 * - Inline Accept-to-inventory per row gated by permission (Q5) — deferred
 *   until backend exposes the permission flag through the operator view.
 *
 * Operator response shape (lands in OperatorResponseContext keyed by node_id):
 *   { rows: [{component_type_id, condition_grade, position, condition_notes, is_missing, original_part_number}] }
 *
 * The submit handler in `services/dwi/operator_capture.py` reads this and
 * passes it as the `rows` argument to create_harvested_components_from_capture.
 */
import { useMemo } from "react";
import { Node, mergeAttributes } from "@tiptap/core";
import {
    NodeViewWrapper,
    ReactNodeViewRenderer,
    type NodeViewProps,
} from "@tiptap/react";
import { Wrench } from "lucide-react";
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

type EnumerateFrom = "disassembly_bom" | "manual";

type Attrs = {
    node_id: string;
    label: string;
    enumerate_from: EnumerateFrom;
    manual_component_types: string[];
    strict_enumeration: boolean;
    required: boolean;
};

type CapturedRow = {
    component_type_id: string;
    condition_grade: "" | "A" | "B" | "C" | "SCRAP";
    position: string;
    condition_notes: string;
    is_missing: boolean;
    original_part_number: string;
};

type CapturedValue = { rows: CapturedRow[] };

const EMPTY_VALUE: CapturedValue = { rows: [] };

export function HarvestedComponentCaptureEditForm({ node, updateAttributes }: NodeViewProps) {
    const a = node.attrs as Attrs;
    const update = useDebouncedAttrs(updateAttributes, 250);
    return (
        <div className="space-y-3">
            <TextAttrRow attrName="label" label="Label" initial={a.label} update={update} />
            <div className="space-y-1">
                <Label className="text-xs">Enumerate components from</Label>
                <Select
                    value={a.enumerate_from}
                    onValueChange={(v) => updateAttributes({ enumerate_from: v })}
                >
                    <SelectTrigger className="h-8 text-sm">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="disassembly_bom">
                            DisassemblyBOMLine (per core_type)
                        </SelectItem>
                        <SelectItem value="manual">Manual component-type list</SelectItem>
                    </SelectContent>
                </Select>
                <p className="text-[11px] text-muted-foreground">
                    BOM-driven mode enumerates rows from the current Core's DisassemblyBOMLine
                    rows. Manual mode uses the engineer-supplied component_type list.
                </p>
            </div>
            <div className="flex items-center justify-between border-t pt-2">
                <div className="space-y-0.5">
                    <Label className="text-xs">Strict enumeration</Label>
                    <p className="text-[11px] text-muted-foreground">
                        Operator must grade every expected row or mark it missing.
                    </p>
                </div>
                <Switch
                    checked={a.strict_enumeration}
                    onCheckedChange={(checked) =>
                        updateAttributes({ strict_enumeration: checked })
                    }
                />
            </div>
            <div className="flex items-center justify-between border-t pt-2">
                <Label className="text-xs">Required to complete substep</Label>
                <Switch
                    checked={a.required}
                    onCheckedChange={(checked) => updateAttributes({ required: checked })}
                />
            </div>
        </div>
    );
}

function asCapturedValue(value: unknown): CapturedValue {
    if (value && typeof value === "object" && Array.isArray((value as CapturedValue).rows)) {
        return value as CapturedValue;
    }
    return EMPTY_VALUE;
}

function View(props: NodeViewProps) {
    const { node, editor } = props;
    const a = node.attrs as Attrs;
    const isOperator = !editor.isEditable;
    const { value, setValue } = useOperatorResponse(a.node_id);

    const captured = useMemo(() => asCapturedValue(value), [value]);
    const rowCount = captured.rows.length;

    const badges = (
        <>
            <Badge variant="outline" className="text-[10px] capitalize">
                {a.enumerate_from === "disassembly_bom" ? "BOM-driven" : "Manual"}
            </Badge>
            {a.strict_enumeration && (
                <Badge variant="secondary" className="text-[10px]">Strict</Badge>
            )}
            {a.required && <Badge variant="secondary" className="text-[10px]">Required</Badge>}
            {isOperator && rowCount > 0 && (
                <Badge variant="default" className="text-[10px]">
                    {rowCount} captured ✓
                </Badge>
            )}
        </>
    );

    const card = (
        <NodeCard
            icon={<Wrench className="h-4 w-4 text-muted-foreground" />}
            label={a.label || "Harvested components"}
            badges={badges}
        >
            <div contentEditable={false} className="space-y-2 text-sm">
                {isOperator ? (
                    <OperatorRuntime
                        attrs={a}
                        captured={captured}
                        setCaptured={(next) => setValue(next)}
                    />
                ) : (
                    <div className="rounded-md border border-dashed bg-muted/30 p-3 text-xs text-muted-foreground">
                        Operator-only surface. At runtime this loads the current Core's
                        DisassemblyBOMLine rows (or the manual component-type list) and
                        captures one row per expected component.
                    </div>
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

/**
 * Operator runtime placeholder.
 *
 * Full runtime requires:
 * (a) A `CurrentCoreContext` exposing the StepExecution's core_id and
 *     core_type_id (needs a parent provider in the substep operator view).
 * (b) A query hook for DisassemblyBOMLine rows by core_type.
 * (c) Inline Accept-to-inventory button gated by `accept_harvestedcomponent`
 *     permission from the user's effective-permissions endpoint.
 *
 * v1 ships with an editable table that captures rows manually so the
 * authoring + submit path is end-to-end testable. The BOM-driven enumeration
 * path lands when (a)+(b) wire in.
 */
function OperatorRuntime({
    attrs,
    captured,
    setCaptured,
}: {
    attrs: Attrs;
    captured: CapturedValue;
    setCaptured: (next: CapturedValue) => void;
}) {
    function addBlankRow() {
        setCaptured({
            rows: [
                ...captured.rows,
                {
                    component_type_id: "",
                    condition_grade: "",
                    position: "",
                    condition_notes: "",
                    is_missing: false,
                    original_part_number: "",
                },
            ],
        });
    }

    function updateRow(idx: number, patch: Partial<CapturedRow>) {
        setCaptured({
            rows: captured.rows.map((r, i) => (i === idx ? { ...r, ...patch } : r)),
        });
    }

    function removeRow(idx: number) {
        setCaptured({ rows: captured.rows.filter((_, i) => i !== idx) });
    }

    return (
        <div className="space-y-2">
            {captured.rows.length === 0 && (
                <div className="text-xs italic text-muted-foreground">
                    {attrs.enumerate_from === "disassembly_bom"
                        ? "BOM-driven enumeration pending CurrentCoreContext wiring; add rows manually for now."
                        : "No components captured yet."}
                </div>
            )}
            {captured.rows.map((row, i) => (
                <div
                    key={i}
                    className="grid grid-cols-[1fr_120px_1fr_auto] items-center gap-2 rounded border bg-background p-2"
                >
                    <input
                        type="text"
                        placeholder="component_type_id"
                        className="rounded border bg-background px-2 py-1 text-xs"
                        value={row.component_type_id}
                        onChange={(e) =>
                            updateRow(i, { component_type_id: e.target.value })
                        }
                    />
                    <select
                        className="rounded border bg-background px-2 py-1 text-xs"
                        value={row.condition_grade}
                        onChange={(e) =>
                            updateRow(i, {
                                condition_grade: e.target.value as CapturedRow["condition_grade"],
                            })
                        }
                    >
                        <option value="">— grade —</option>
                        <option value="A">A</option>
                        <option value="B">B</option>
                        <option value="C">C</option>
                        <option value="SCRAP">SCRAP</option>
                    </select>
                    <input
                        type="text"
                        placeholder="position (e.g. Cyl 1)"
                        className="rounded border bg-background px-2 py-1 text-xs"
                        value={row.position}
                        onChange={(e) => updateRow(i, { position: e.target.value })}
                    />
                    <button
                        type="button"
                        className="rounded px-2 py-1 text-xs text-destructive hover:bg-destructive/10"
                        onClick={() => removeRow(i)}
                    >
                        Remove
                    </button>
                    <textarea
                        placeholder="condition notes (optional)"
                        rows={1}
                        className="col-span-4 rounded border bg-background px-2 py-1 text-xs"
                        value={row.condition_notes}
                        onChange={(e) =>
                            updateRow(i, { condition_notes: e.target.value })
                        }
                    />
                </div>
            ))}
            <button
                type="button"
                onClick={addBlankRow}
                className="text-xs text-primary hover:underline"
            >
                + Add component row
            </button>
        </div>
    );
}

export const HarvestedComponentCapture = Node.create({
    name: "harvestedComponentCapture",
    group: "block",
    atom: true,
    selectable: true,
    draggable: true,
    addAttributes() {
        return {
            node_id: { default: "" },
            label: { default: "Harvested components" },
            enumerate_from: { default: "disassembly_bom" as EnumerateFrom },
            manual_component_types: { default: [] as string[] },
            strict_enumeration: { default: false },
            required: { default: false },
        };
    },
    parseHTML() {
        return [{ tag: 'div[data-type="harvested-component-capture"]' }];
    },
    renderHTML({ HTMLAttributes }) {
        return [
            "div",
            mergeAttributes(HTMLAttributes, {
                "data-type": "harvested-component-capture",
            }),
            `[HARVESTED] ${HTMLAttributes.label || "Harvested components"}`,
        ];
    },
    addNodeView() {
        return ReactNodeViewRenderer(View);
    },
});

export const SAMPLE_HARVESTED_COMPONENT_CAPTURE = {
    type: "harvestedComponentCapture",
    attrs: {
        node_id: "seed-harvested-1",
        label: "Capture harvested components",
        enumerate_from: "disassembly_bom" as EnumerateFrom,
        manual_component_types: [],
        strict_enumeration: false,
        required: true,
    },
};
