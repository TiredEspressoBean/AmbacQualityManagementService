/** HarvestedComponentCapture — reman teardown DWI node.
 *
 * Engineer authors the node into a teardown substep. Operator runtime resolves
 * the Core from the parent StepExecution, enumerates rows from
 * DisassemblyBOMLine (or a manual component-type list), and captures
 * condition_grade / position / condition_notes per row. The submit handler
 * routes captures through `services.dwi.harvested_component_capture` which
 * creates HarvestedComponent rows + dispatches scrap_component for SCRAP rows.
 *
 * - Authoring UI for enumerate_from + strict_enumeration toggles.
 * - Operator runtime: one row per expected component and position, from the unit's
 *   core type (a core is a part, so the runtime's PartContext already names it); a
 *   grade per row, a missing toggle, notes, and a picker for anything unexpected.
 * - Inline Accept-to-inventory per row is not here: accepting is a disposition, held
 *   under its own permission on the Harvested Components page.
 *
 * Operator response shape (lands in OperatorResponseContext keyed by node_id):
 *   { rows: [{component_type_id, condition_grade, position, condition_notes, is_missing, original_part_number}] }
 *
 * The submit handler in `services/dwi/operator_capture.py` reads this and
 * passes it as the `rows` argument to create_harvested_components_from_capture.
 */
import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
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
import { usePartContext } from "../shared/PartContext";

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
    // Recorded, not merely listed: the runtime seeds one blank row per expected
    // component, so counting rows put "3 captured ✓" on a unit nobody had graded.
    const rowCount = captured.rows.filter((r) => r.is_missing || !!r.condition_grade).length;

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
                    {rowCount} recorded ✓
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
 * Operator runtime — one row per component the unit is expected to give up.
 *
 * A core is a part (Documents/CORE_AS_PART_DESIGN.md), so the runtime already knows the
 * unit: `PartContext.part_id`. The part's type IS the core type, and its
 * DisassemblyBOMLine rows say what to expect and where (`positions`), so the operator
 * grades what they find rather than typing ids. This replaces a placeholder that had
 * operators enter raw component-type UUIDs.
 *
 * Rows are seeded once, when nothing has been captured yet, and are then the operator's:
 * a component can be marked missing, and an unexpected one added — teardown finds what
 * it finds. Strict enumeration (an author setting) is enforced twice: the runtime blocks
 * Confirm while an expected row is neither graded nor marked missing
 * (`build-captures.findMissingRequired`), and the server re-checks the submitted rows
 * against the unit's disassembly BOM from the AUTHORED node
 * (`operator_capture._strict_harvest_reason`) — the client sends only recorded rows, so
 * only the server can compare them with what was expected.
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
    const { part_id } = usePartContext();

    const partQ = useQuery({
        queryKey: ["dwi-harvest", "part", part_id],
        queryFn: () => api.api_Parts_retrieve({ params: { id: String(part_id) } }),
        enabled: !!part_id,
    });
    const coreTypeId = partQ.data?.part_type ? String(partQ.data.part_type) : null;

    const linesQ = useQuery({
        queryKey: ["dwi-harvest", "disassembly-bom", coreTypeId],
        queryFn: () => api.api_DisassemblyBOMLines_list({
            queries: { core_type: coreTypeId!, limit: 200 },
        }),
        enabled: !!coreTypeId && attrs.enumerate_from === "disassembly_bom",
    });
    // Names for manual mode, and for the "add an unexpected component" picker.
    const typesQ = useQuery({
        queryKey: ["dwi-harvest", "part-types"],
        queryFn: () => api.api_PartTypes_list({ queries: { limit: 500 } }),
    });
    const typeName = useMemo(() => {
        const m = new Map<string, string>();
        for (const t of typesQ.data?.results ?? []) m.set(String(t.id), t.name);
        for (const l of linesQ.data?.results ?? []) {
            m.set(String(l.component_type), l.component_type_name);
        }
        return m;
    }, [typesQ.data, linesQ.data]);

    // Expected rows: one per unit per position, from the BOM (or the manual list).
    const expected = useMemo<CapturedRow[]>(() => {
        const blank = (component_type_id: string, position: string): CapturedRow => ({
            component_type_id, position, condition_grade: "", condition_notes: "",
            is_missing: false, original_part_number: "",
        });
        if (attrs.enumerate_from === "manual") {
            return (attrs.manual_component_types ?? []).map((id) => blank(String(id), ""));
        }
        const rows: CapturedRow[] = [];
        for (const line of linesQ.data?.results ?? []) {
            const qty = Math.max(1, line.expected_qty ?? 1);
            const positions = Array.isArray(line.positions) ? (line.positions as string[]) : [];
            for (let i = 0; i < qty; i++) {
                rows.push(blank(String(line.component_type), positions[i] ?? ""));
            }
        }
        return rows;
    }, [attrs.enumerate_from, attrs.manual_component_types, linesQ.data]);

    // Seed once. Never overwrite what the operator has already recorded.
    useEffect(() => {
        if (captured.rows.length === 0 && expected.length > 0) {
            setCaptured({ rows: expected });
        }
    }, [expected, captured.rows.length, setCaptured]);

    const update = (idx: number, patch: Partial<CapturedRow>) =>
        setCaptured({ rows: captured.rows.map((r, i) => (i === idx ? { ...r, ...patch } : r)) });
    const remove = (idx: number) =>
        setCaptured({ rows: captured.rows.filter((_, i) => i !== idx) });
    const [unexpectedType, setUnexpectedType] = useState("");
    const addUnexpected = () => {
        if (!unexpectedType) return;
        setCaptured({
            rows: [...captured.rows, {
                component_type_id: unexpectedType, position: "", condition_grade: "",
                condition_notes: "", is_missing: false, original_part_number: "",
            }],
        });
        setUnexpectedType("");
    };

    if (!part_id) {
        return <p className="text-xs text-muted-foreground">Open this step on a unit to record what came out of it.</p>;
    }
    if (partQ.isLoading || linesQ.isLoading) {
        return <p className="text-xs text-muted-foreground">Loading what this unit should give up…</p>;
    }

    const expectedCount = expected.length;
    const graded = captured.rows.filter((r) => r.is_missing || r.condition_grade).length;

    return (
        <div className="space-y-2">
            {expectedCount === 0 && attrs.enumerate_from === "disassembly_bom" && (
                <p className="text-xs text-amber-700 dark:text-amber-400">
                    No disassembly BOM is authored for this core type, so there is nothing to
                    expect. Add each component you find below.
                </p>
            )}
            {captured.rows.length > 0 && (
                <p className="text-xs text-muted-foreground tabular-nums">
                    {graded} of {captured.rows.length} recorded
                    {attrs.strict_enumeration && " · every expected component must be graded or marked missing"}
                </p>
            )}
            {captured.rows.map((row, i) => {
                const unexpected = i >= expectedCount;
                return (
                    <div key={i} className={`grid grid-cols-[minmax(0,1fr)_7rem_7rem_auto] items-center gap-2 rounded border p-2 ${row.is_missing ? "bg-muted/40" : "bg-background"}`}>
                        <div className="min-w-0 text-sm">
                            <div className="truncate font-medium">
                                {typeName.get(row.component_type_id) ?? "Component"}
                            </div>
                            <div className="text-xs text-muted-foreground">
                                {row.position || (unexpected ? "unexpected" : "no position")}
                            </div>
                        </div>
                        <Select
                            value={row.condition_grade || undefined}
                            disabled={row.is_missing}
                            onValueChange={(v) => update(i, { condition_grade: v as CapturedRow["condition_grade"] })}
                        >
                            <SelectTrigger className="h-8 text-sm"><SelectValue placeholder="Grade" /></SelectTrigger>
                            <SelectContent>
                                <SelectItem value="A">A — serviceable</SelectItem>
                                <SelectItem value="B">B — serviceable</SelectItem>
                                <SelectItem value="C">C — recondition</SelectItem>
                                <SelectItem value="SCRAP">Scrap</SelectItem>
                            </SelectContent>
                        </Select>
                        <label className="flex items-center gap-2 text-xs">
                            <Switch
                                checked={row.is_missing}
                                onCheckedChange={(checked) =>
                                    update(i, { is_missing: checked, condition_grade: checked ? "" : row.condition_grade })}
                            />
                            Missing
                        </label>
                        {unexpected ? (
                            <button type="button" className="text-xs text-destructive hover:underline" onClick={() => remove(i)}>
                                Remove
                            </button>
                        ) : <span />}
                        <input
                            type="text"
                            placeholder="Notes (optional)"
                            className="col-span-4 rounded border bg-background px-2 py-1 text-xs"
                            value={row.condition_notes}
                            disabled={row.is_missing}
                            onChange={(e) => update(i, { condition_notes: e.target.value })}
                        />
                    </div>
                );
            })}
            <div className="flex items-center gap-2 pt-1">
                <Select value={unexpectedType || undefined} onValueChange={setUnexpectedType}>
                    <SelectTrigger className="h-8 w-64 text-sm"><SelectValue placeholder="Found something unexpected?" /></SelectTrigger>
                    <SelectContent>
                        {(typesQ.data?.results ?? []).map((t) => (
                            <SelectItem key={String(t.id)} value={String(t.id)}>{t.name}</SelectItem>
                        ))}
                    </SelectContent>
                </Select>
                <button type="button" className="text-xs text-primary hover:underline disabled:opacity-50"
                        disabled={!unexpectedType} onClick={addUnexpected}>
                    + Add
                </button>
            </div>
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
