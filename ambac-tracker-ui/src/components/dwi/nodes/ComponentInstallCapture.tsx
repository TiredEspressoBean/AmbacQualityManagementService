/** ComponentInstallCapture — reman REBUILD DWI node: what went into each slot.
 *
 * The rebuild half of reman capture; HarvestedComponentCapture is the teardown half. A
 * core is a part (Documents/CORE_AS_PART_DESIGN.md), so the runtime already knows the
 * unit (`PartContext.part_id`); its `core_role` reaches the rebuild plan, which says
 * slot by slot what should go in and why. The operator confirms what they actually
 * fitted:
 *
 * - REUSE / RECONDITION — the unit's own component, preselected: confirm it went back.
 * - REPLACE_POOL — pick which recovered part from stock was fitted.
 * - REPLACE_BUY — shown, not recorded: a bought part is drawn from its lot by material
 *   consumption when the step completes, which is already its traceability.
 *
 * Operator response (OperatorResponseContext, keyed by node_id):
 *   { rows: [{ bom_line_id, position, harvested_id?, part_id? }] }  — one per fitted slot
 * `build-captures` sends it as kind `component_install`; the server records each row
 * through `install_component`, which holds the rules (a repair-and-return unit only
 * ever takes its own parts).
 */
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Node, mergeAttributes } from "@tiptap/core";
import { NodeViewWrapper, ReactNodeViewRenderer, type NodeViewProps } from "@tiptap/react";
import { Wrench } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { api } from "@/lib/api/generated";
import { rebuildPlanOptions } from "@/hooks/useRebuildPlan";
import type { Schema } from "@/lib/api/types";
import { NodeCard } from "../shared/NodeCard";
import { AuthoringPopover } from "../shared/AuthoringPopover";
import { useDebouncedAttrs } from "../shared/useDebouncedAttrs";
import { TextAttrRow } from "../shared/AttrInputs";
import { useOperatorResponse } from "../shared/OperatorResponseContext";
import { usePartContext } from "../shared/PartContext";

type Attrs = { node_id: string; label: string; required: boolean };

type Slot = Schema<"RebuildPlan">["slots"][number];

type InstallRow = {
    bom_line_id: string | null;
    position: string;
    harvested_id?: string;
    part_id?: string;
};
type CapturedValue = { rows: InstallRow[] };

const RESOLUTION_LABEL: Record<string, string> = {
    REUSE: "Reuse the unit's own",
    RECONDITION: "Recondition the unit's own",
    REPLACE_POOL: "Replace from recovered stock",
    REPLACE_BUY: "Replace with a purchased part",
};

export function ComponentInstallCaptureEditForm({ node, updateAttributes }: NodeViewProps) {
    const a = node.attrs as Attrs;
    const update = useDebouncedAttrs(updateAttributes, 250);
    return (
        <div className="space-y-3">
            <TextAttrRow attrName="label" label="Label" initial={a.label} update={update} />
            <p className="text-[11px] text-muted-foreground">
                At runtime this lists the slots of the unit's rebuild plan, and the operator
                confirms what was fitted in each. Place it on the rebuild step where the
                components go in.
            </p>
            <div className="flex items-center justify-between border-t pt-2">
                <Label className="text-xs">Required to complete substep</Label>
                <Switch checked={a.required}
                        onCheckedChange={(checked) => updateAttributes({ required: checked })} />
            </div>
        </div>
    );
}

function asCaptured(value: unknown): CapturedValue {
    if (value && typeof value === "object" && Array.isArray((value as CapturedValue).rows)) {
        return value as CapturedValue;
    }
    return { rows: [] };
}

function slotKey(slot: Slot, i: number) {
    return `${slot.bom_line_id ?? "none"}:${slot.position ?? ""}:${i}`;
}

function OperatorRuntime({ captured, setCaptured }: {
    captured: CapturedValue;
    setCaptured: (next: CapturedValue) => void;
}) {
    const { part_id } = usePartContext();
    const partQ = useQuery({
        queryKey: ["dwi-install", "part", part_id],
        queryFn: () => api.api_Parts_retrieve({ params: { id: String(part_id) } }),
        enabled: !!part_id,
    });
    const coreId = partQ.data?.core_role ? String(partQ.data.core_role) : null;
    const planQ = useQuery({ ...rebuildPlanOptions(coreId ?? ""), enabled: !!coreId });

    const slots = planQ.data?.slots ?? [];
    // What the operator recorded, per slot. A slot is "fitted" when a row names it.
    const rowFor = useMemo(() => {
        const m = new Map<string, InstallRow>();
        slots.forEach((slot, i) => {
            const r = captured.rows.find((row) =>
                row.bom_line_id === (slot.bom_line_id ?? null) && row.position === (slot.position ?? ""));
            if (r) m.set(slotKey(slot, i), r);
        });
        return m;
    }, [slots, captured.rows]);

    const setSlot = (slot: Slot, row: InstallRow | null) => {
        const others = captured.rows.filter((r) =>
            !(r.bom_line_id === (slot.bom_line_id ?? null) && r.position === (slot.position ?? "")));
        setCaptured({ rows: row ? [...others, row] : others });
    };

    if (!part_id) return <p className="text-xs text-muted-foreground">Open this step on a unit to record what was fitted.</p>;
    if (partQ.isLoading || planQ.isLoading) return <p className="text-xs text-muted-foreground">Loading the rebuild plan…</p>;
    if (!coreId) return <p className="text-xs text-muted-foreground">This unit is not a reman core, so there is no rebuild plan to fit against.</p>;
    if (slots.length === 0) return <p className="text-xs text-amber-700 dark:text-amber-400">The rebuild plan has no slots — check that the core type has a released assembly BOM.</p>;

    return (
        <div className="space-y-2">
            {slots.map((slot, i) => {
                const key = slotKey(slot, i);
                const row = rowFor.get(key);
                const base = { bom_line_id: slot.bom_line_id ?? null, position: slot.position ?? "" };
                const own = slot.candidates.find((c) => c.kind === "HARVESTED_THIS_CORE");
                const pool = slot.candidates.filter((c) => c.kind === "HARVESTED_POOL");
                const buy = slot.resolution === "REPLACE_BUY";
                return (
                    <div key={key} className="grid grid-cols-[minmax(0,1fr)_minmax(0,16rem)] items-center gap-3 rounded border p-2">
                        <div className="min-w-0 text-sm">
                            <div className="truncate font-medium">{slot.component_type_name}</div>
                            <div className="text-xs text-muted-foreground">
                                {slot.position || "no position"} · {RESOLUTION_LABEL[slot.resolution] ?? slot.resolution}
                            </div>
                        </div>
                        {buy ? (
                            <p className="text-xs text-muted-foreground">
                                Purchased — drawn from stock when this step completes.
                            </p>
                        ) : own && (slot.resolution === "REUSE" || slot.resolution === "RECONDITION") ? (
                            <label className="flex items-center justify-end gap-2 text-xs">
                                <Switch
                                    checked={!!row?.harvested_id}
                                    onCheckedChange={(checked) =>
                                        setSlot(slot, checked ? { ...base, harvested_id: own.id } : null)}
                                />
                                Fitted {own.label}{own.grade ? ` (grade ${own.grade})` : ""}
                            </label>
                        ) : pool.length > 0 ? (
                            <Select
                                value={row?.part_id ?? undefined}
                                onValueChange={(v) => setSlot(slot, { ...base, part_id: v })}
                            >
                                <SelectTrigger className="h-8 text-sm"><SelectValue placeholder="Which part was fitted?" /></SelectTrigger>
                                <SelectContent>
                                    {pool.map((c) => (
                                        <SelectItem key={c.id} value={c.id}>
                                            {c.label}{c.grade ? ` — grade ${c.grade}` : ""}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        ) : (
                            <p className="text-xs text-amber-700 dark:text-amber-400">
                                Nothing available to fit — see the rebuild plan.
                            </p>
                        )}
                    </div>
                );
            })}
            <p className="text-xs text-muted-foreground tabular-nums">
                {captured.rows.length} of {slots.filter((s) => s.resolution !== "REPLACE_BUY").length} fitted slots recorded
            </p>
        </div>
    );
}

function View(props: NodeViewProps) {
    const { node, editor } = props;
    const a = node.attrs as Attrs;
    const isOperator = !editor.isEditable;
    const { value, setValue } = useOperatorResponse(a.node_id);
    const captured = useMemo(() => asCaptured(value), [value]);

    return (
        <NodeViewWrapper className="my-3 not-prose">
            <AuthoringPopover isEditable={editor.isEditable} nodeId={a.node_id}>
                <NodeCard
                    icon={<Wrench className="h-4 w-4 text-muted-foreground" />}
                    label={a.label || "Components installed"}
                    badges={<>
                        {a.required && <Badge variant="secondary" className="text-[10px]">Required</Badge>}
                        {isOperator && captured.rows.length > 0 && (
                            <Badge variant="default" className="text-[10px]">{captured.rows.length} fitted ✓</Badge>
                        )}
                    </>}
                >
                    <div contentEditable={false} className="space-y-2 text-sm">
                        {isOperator ? (
                            <OperatorRuntime captured={captured} setCaptured={(next) => setValue(next)} />
                        ) : (
                            <div className="rounded-md border border-dashed bg-muted/30 p-3 text-xs text-muted-foreground">
                                Operator-only surface. At runtime this lists the slots of the unit's
                                rebuild plan, and the operator confirms what was fitted in each.
                            </div>
                        )}
                    </div>
                </NodeCard>
            </AuthoringPopover>
        </NodeViewWrapper>
    );
}

export const ComponentInstallCapture = Node.create({
    name: "componentInstallCapture",
    group: "block",
    atom: true,
    selectable: true,
    draggable: true,
    addAttributes() {
        return {
            node_id: { default: "" },
            label: { default: "Components installed" },
            required: { default: false },
        };
    },
    parseHTML() {
        return [{ tag: 'div[data-type="component-install-capture"]' }];
    },
    renderHTML({ HTMLAttributes }) {
        return [
            "div",
            mergeAttributes(HTMLAttributes, { "data-type": "component-install-capture" }),
            `[INSTALLED] ${HTMLAttributes.label || "Components installed"}`,
        ];
    },
    addNodeView() {
        return ReactNodeViewRenderer(View);
    },
});

export const SAMPLE_COMPONENT_INSTALL_CAPTURE = {
    type: "componentInstallCapture",
    attrs: {
        node_id: "seed-install-1",
        label: "Record components fitted",
        required: true,
    },
};
