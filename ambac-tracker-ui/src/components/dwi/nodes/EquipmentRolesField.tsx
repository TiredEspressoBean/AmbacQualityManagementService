/**
 * EquipmentRolesField — captures the equipment used in this inspection event,
 * with a per-row role (PRODUCTION / FIXTURE / TOOL / GAUGE / OTHER). Maps to
 * `QualityReportEquipment` through rows when the substep promotes to
 * `QualityReports` via `is_inspection_point`.
 *
 * Replaces the legacy single-FK `QualityReports.machine` shape — cell ops,
 * multi-station Steps, and fixture/tool combinations are all expressible
 * because each row carries its own role.
 *
 * Engineer authoring: label, required count (default 1+), default role,
 * optional `equipment_type` filter.
 * Operator capture: array of `{ equipment_id, role, notes? }`.
 */
import { Node, mergeAttributes } from "@tiptap/core";
import {
    NodeViewWrapper,
    ReactNodeViewRenderer,
    type NodeViewProps,
} from "@tiptap/react";
import { Wrench, Plus, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
import { useRetrieveEquipments } from "@/hooks/useRetrieveEquipments";

type EquipmentRole = "PRODUCTION" | "FIXTURE" | "TOOL" | "GAUGE" | "OTHER";

const ROLE_LABELS: Record<EquipmentRole, string> = {
    PRODUCTION: "Production",
    FIXTURE: "Fixture",
    TOOL: "Tool",
    GAUGE: "Gauge",
    OTHER: "Other",
};
const ROLES: EquipmentRole[] = ["PRODUCTION", "FIXTURE", "TOOL", "GAUGE", "OTHER"];

type Attrs = {
    node_id: string;
    label: string;
    required: boolean;
    min_rows: number;
    default_role: EquipmentRole;
};

type ResponseRow = { equipment_id: number; role: EquipmentRole; notes?: string };

export function EquipmentRolesFieldEditForm({ node, updateAttributes }: NodeViewProps) {
    const a = node.attrs as Attrs;
    const update = useDebouncedAttrs(updateAttributes, 250);
    return (
        <div className="space-y-3">
            <TextAttrRow attrName="label" label="Label" initial={a.label} update={update} />
            <div className="space-y-1">
                <Label className="text-xs">Default role for new rows</Label>
                <Select
                    value={a.default_role}
                    onValueChange={(v) => updateAttributes({ default_role: v })}
                >
                    <SelectTrigger className="h-8 text-sm">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        {ROLES.map((r) => (
                            <SelectItem key={r} value={r}>{ROLE_LABELS[r]}</SelectItem>
                        ))}
                    </SelectContent>
                </Select>
            </div>
            <div className="grid grid-cols-3 items-center gap-2">
                <Label className="text-xs">Min rows</Label>
                <Input
                    type="number"
                    min={0}
                    value={String(a.min_rows ?? 1)}
                    onChange={(e) => updateAttributes({ min_rows: Number(e.target.value) || 0 })}
                    className="col-span-2 h-8 text-sm"
                />
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
    const rows: ResponseRow[] = Array.isArray(value) ? (value as ResponseRow[]) : [];

    const { data: equipResp } = useRetrieveEquipments();
    const equipments = (equipResp?.results ?? []) as Array<{ id: number; name: string }>;

    const update = (next: ResponseRow[]) => {
        if (!isOperator) return;
        setValue(next);
    };
    const addRow = () => {
        const first = equipments[0];
        if (!first) return;
        update([...rows, { equipment_id: first.id, role: (a.default_role || "PRODUCTION") as EquipmentRole }]);
    };
    const setRow = (i: number, patch: Partial<ResponseRow>) => {
        const next = rows.slice();
        next[i] = { ...next[i], ...patch };
        update(next);
    };
    const removeRow = (i: number) => update(rows.filter((_, j) => j !== i));

    const card = (
        <NodeCard
            icon={<Wrench className="h-4 w-4 text-muted-foreground" />}
            label={a.label || "Equipment used"}
            badges={
                <>
                    {a.required && <Badge variant="secondary" className="text-[10px]">Required</Badge>}
                    {isOperator && rows.length > 0 && (
                        <Badge variant="default" className="text-[10px]">{rows.length} row{rows.length === 1 ? "" : "s"}</Badge>
                    )}
                </>
            }
        >
            <div className="space-y-1.5" contentEditable={false}>
                {rows.map((row, i) => (
                    <div key={i} className="flex items-center gap-1">
                        <select
                            disabled={!isOperator}
                            value={row.equipment_id}
                            onChange={(e) => setRow(i, { equipment_id: Number(e.target.value) })}
                            className="h-8 flex-1 rounded border bg-background px-2 text-sm"
                        >
                            {equipments.map((eq) => (
                                <option key={eq.id} value={eq.id}>{eq.name}</option>
                            ))}
                        </select>
                        <select
                            disabled={!isOperator}
                            value={row.role}
                            onChange={(e) => setRow(i, { role: e.target.value as EquipmentRole })}
                            className="h-8 w-28 rounded border bg-background px-2 text-sm"
                        >
                            {ROLES.map((r) => (
                                <option key={r} value={r}>{ROLE_LABELS[r]}</option>
                            ))}
                        </select>
                        {isOperator && (
                            <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                onClick={() => removeRow(i)}
                                className="h-8 w-8 p-0"
                            >
                                <X className="h-3 w-3" />
                            </Button>
                        )}
                    </div>
                ))}
                {rows.length === 0 && (
                    <div className="text-xs italic text-muted-foreground">
                        {isOperator ? "No equipment captured yet." : "Operator adds equipment rows here."}
                    </div>
                )}
                {isOperator && (
                    <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={addRow}
                        className="h-7 w-full justify-start text-xs text-muted-foreground"
                    >
                        <Plus className="mr-1 h-3 w-3" /> Add equipment
                    </Button>
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

export const EquipmentRolesField = Node.create({
    name: "equipmentRolesField",
    group: "block",
    atom: true,
    selectable: true,
    draggable: true,
    addAttributes() {
        return {
            node_id: { default: "" },
            label: { default: "Equipment used" },
            required: { default: false },
            min_rows: { default: 1 },
            default_role: { default: "PRODUCTION" },
        };
    },
    parseHTML() {
        return [{ tag: 'div[data-type="equipment-roles-field"]' }];
    },
    renderHTML({ HTMLAttributes }) {
        return [
            "div",
            mergeAttributes(HTMLAttributes, { "data-type": "equipment-roles-field" }),
            `[EQUIPMENT] ${HTMLAttributes.label || ""}`,
        ];
    },
    addNodeView() {
        return ReactNodeViewRenderer(View);
    },
});

export const SAMPLE_EQUIPMENT_ROLES = {
    type: "equipmentRolesField",
    attrs: {
        node_id: "seed-equipment-roles-1",
        label: "Equipment used during this inspection",
        required: true,
        min_rows: 1,
        default_role: "PRODUCTION",
    },
};
