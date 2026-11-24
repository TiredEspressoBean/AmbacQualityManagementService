/** OptionalPartUsedCapture — "Used?" for one OPTIONAL BOM line at its consuming step.
 *
 * An optional part (an O-ring kit fitted when the old one is cracked) is drawn only when
 * someone says it went in. This node asks, per unit: used or not, and how many (up to
 * the line's quantity), with the lot(s) taken. The answer is required — the unit can't
 * leave the step without it — and the server draws from it when the unit leaves
 * (services/mes/optional_usage), so a line asked about here is never also drawn at its
 * usage %.
 *
 * Operator response (OperatorResponseContext, keyed by node_id):
 *   { used: boolean, quantity: string, lots: [{ lot_id, qty }] }
 * `build-captures` sends it as kind `optional_part_used`.
 */
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Node, mergeAttributes } from "@tiptap/core";
import { NodeViewWrapper, ReactNodeViewRenderer, type NodeViewProps } from "@tiptap/react";
import { PackageCheck, Plus, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { api } from "@/lib/api/generated";
import { NodeCard } from "../shared/NodeCard";
import { AuthoringPopover } from "../shared/AuthoringPopover";
import { useDebouncedAttrs } from "../shared/useDebouncedAttrs";
import { TextAttrRow } from "../shared/AttrInputs";
import { useOperatorResponse } from "../shared/OperatorResponseContext";
import { useSubstepAuthoringContext } from "../shared/SubstepAuthoringContext";

type Attrs = { node_id: string; label: string; required: boolean; bom_line_id: string };
type LotRow = { lot_id: string; qty: string };
export type OptionalPartAnswer = { used?: boolean; quantity?: string; lots?: LotRow[] };

const lineName = (l: { material_name?: string | null; component_type_name?: string | null } | undefined) =>
    l?.material_name || l?.component_type_name || "Optional part";

function useLine(id: string) {
    return useQuery({
        queryKey: ["dwi-optional-part", "line", id],
        queryFn: () => api.api_BOMLines_retrieve({ params: { id } }),
        enabled: !!id,
    });
}

export function OptionalPartUsedCaptureEditForm({ node, updateAttributes }: NodeViewProps) {
    const a = node.attrs as Attrs;
    const update = useDebouncedAttrs(updateAttributes, 250);
    const { stepId, partTypeId } = useSubstepAuthoringContext();
    // The step's optional lines: optional, of this part type's BOMs, consumed here.
    const linesQ = useQuery({
        queryKey: ["dwi-optional-part", "lines", partTypeId, stepId],
        queryFn: () => api.api_BOMLines_list({ queries: {
            bom__part_type: partTypeId, is_optional: true, limit: 200 } }),
        enabled: !!partTypeId,
    });
    const lines = (linesQ.data?.results ?? []).filter(
        (l) => !stepId || String(l.consumed_at_step ?? "") === String(stepId));
    return (
        <div className="space-y-3">
            <TextAttrRow attrName="label" label="Label" initial={a.label} update={update} />
            <div className="space-y-1">
                <Label className="text-xs">Optional BOM line</Label>
                <Select value={a.bom_line_id || undefined}
                        onValueChange={(v) => updateAttributes({ bom_line_id: v })}>
                    <SelectTrigger className="h-8 text-sm"><SelectValue placeholder="Pick the optional part" /></SelectTrigger>
                    <SelectContent>
                        {lines.map((l) => (
                            <SelectItem key={l.id} value={String(l.id)}>
                                {lineName(l)} × {Number(l.quantity)} {l.unit_of_measure}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>
                {linesQ.isSuccess && lines.length === 0 && (
                    <p className="text-[11px] text-amber-700 dark:text-amber-400">
                        This step consumes no optional BOM lines. Mark a line optional and set
                        its consumed-at step to this one first.
                    </p>
                )}
            </div>
            <p className="text-[11px] text-muted-foreground">
                Asked per unit, and required: the unit can't leave the step until it's
                answered. The part is drawn from the answer as the unit leaves — the line's
                usage % then only plans it. Not for batch steps (the answer is per unit).
            </p>
        </div>
    );
}

function asAnswer(value: unknown): OptionalPartAnswer {
    return value && typeof value === "object" ? (value as OptionalPartAnswer) : {};
}

function OperatorRuntime({ lineId, answer, setAnswer }: {
    lineId: string; answer: OptionalPartAnswer; setAnswer: (next: OptionalPartAnswer) => void;
}) {
    const lineQ = useLine(lineId);
    const line = lineQ.data;
    const maxQty = Number(line?.quantity ?? 1);
    const item = line?.material
        ? { material: String(line.material) }
        : line?.component_type ? { material_type: String(line.component_type) } : null;
    const lotsQ = useQuery({
        queryKey: ["dwi-optional-part", "lots", item],
        queryFn: () => api.api_MaterialLots_list({ queries: { ...item, on_hand: "true", limit: 50 } }),
        enabled: !!item && answer.used === true,
    });
    const lots = lotsQ.data?.results ?? [];
    const rows = answer.lots ?? [];
    const setRows = (next: LotRow[]) => setAnswer({ ...answer, lots: next });

    if (!lineId) return <p className="text-xs text-amber-700 dark:text-amber-400">No BOM line picked for this question.</p>;
    if (lineQ.isLoading) return <p className="text-xs text-muted-foreground">Loading…</p>;
    return (
        <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm">{lineName(line)}</span>
                <Button size="sm" variant={answer.used === true ? "default" : "outline"}
                        onClick={() => setAnswer({ used: true, quantity: answer.quantity ?? String(maxQty), lots: rows })}>
                    Used
                </Button>
                <Button size="sm" variant={answer.used === false ? "default" : "outline"}
                        onClick={() => setAnswer({ used: false, quantity: "0", lots: [] })}>
                    Not used
                </Button>
            </div>
            {answer.used === true && (
                <div className="space-y-2">
                    <label className="flex items-center gap-2 text-xs">
                        How many
                        <Input type="number" min={1} max={maxQty} step="any" className="h-8 w-24"
                               value={answer.quantity ?? ""}
                               onChange={(e) => setAnswer({ ...answer, quantity: e.target.value })} />
                        <span className="text-muted-foreground">of up to {maxQty} {line?.unit_of_measure}</span>
                    </label>
                    {rows.map((r, i) => (
                        <div key={i} className="flex items-center gap-2">
                            <Select value={r.lot_id || undefined}
                                    onValueChange={(v) => setRows(rows.map((x, j) => (j === i ? { ...x, lot_id: v } : x)))}>
                                <SelectTrigger className="h-8 w-64 text-sm"><SelectValue placeholder="Which lot" /></SelectTrigger>
                                <SelectContent>
                                    {lots.map((l) => (
                                        <SelectItem key={l.id} value={String(l.id)}>
                                            {l.lot_number} — {Number(l.quantity_remaining)} left
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            <Button size="icon" variant="ghost" className="h-8 w-8"
                                    onClick={() => setRows(rows.filter((_, j) => j !== i))}>
                                <X className="h-4 w-4" />
                            </Button>
                        </div>
                    ))}
                    <Button size="sm" variant="ghost" onClick={() => setRows([...rows, { lot_id: "", qty: "" }])}>
                        <Plus className="mr-1 h-4 w-4" /> {rows.length ? "Took another lot" : "Name the lot"}
                    </Button>
                    <p className="text-[11px] text-muted-foreground">
                        No lot named: drawn from the lot kitted for the job, else the oldest.
                    </p>
                </div>
            )}
        </div>
    );
}

function View(props: NodeViewProps) {
    const { node, editor } = props;
    const a = node.attrs as Attrs;
    const isOperator = !editor.isEditable;
    const { value, setValue } = useOperatorResponse(a.node_id);
    const answer = useMemo(() => asAnswer(value), [value]);
    const answered = typeof answer.used === "boolean";

    return (
        <NodeViewWrapper className="my-3 not-prose">
            <AuthoringPopover isEditable={editor.isEditable} nodeId={a.node_id}>
                <NodeCard
                    icon={<PackageCheck className="h-4 w-4 text-muted-foreground" />}
                    label={a.label || "Optional part used?"}
                    badges={<>
                        <Badge variant="secondary" className="text-[10px]">Required</Badge>
                        {isOperator && answered && (
                            <Badge variant="default" className="text-[10px]">
                                {answer.used ? `Used ${answer.quantity}` : "Not used"} ✓
                            </Badge>
                        )}
                    </>}
                >
                    <div contentEditable={false} className="space-y-2 text-sm">
                        {isOperator ? (
                            <OperatorRuntime lineId={a.bom_line_id} answer={answer}
                                             setAnswer={(next) => setValue(next)} />
                        ) : (
                            <div className="rounded-md border border-dashed bg-muted/30 p-3 text-xs text-muted-foreground">
                                Operator-only surface. At runtime the operator answers whether this
                                optional part was used, and how many.
                            </div>
                        )}
                    </div>
                </NodeCard>
            </AuthoringPopover>
        </NodeViewWrapper>
    );
}

export const OptionalPartUsedCapture = Node.create({
    name: "optionalPartUsed",
    group: "block",
    atom: true,
    selectable: true,
    draggable: true,
    addAttributes() {
        return {
            node_id: { default: "" },
            label: { default: "Optional part used?" },
            // Always required: a "used?" left blank would decide the draw by default.
            required: { default: true },
            bom_line_id: { default: "" },
        };
    },
    parseHTML() {
        return [{ tag: 'div[data-type="optional-part-used"]' }];
    },
    renderHTML({ HTMLAttributes }) {
        return [
            "div",
            mergeAttributes(HTMLAttributes, { "data-type": "optional-part-used" }),
            `[USED?] ${HTMLAttributes.label || "Optional part used?"}`,
        ];
    },
    addNodeView() {
        return ReactNodeViewRenderer(View);
    },
});

export const SAMPLE_OPTIONAL_PART_USED = {
    type: "optionalPartUsed",
    attrs: {
        node_id: "seed-optional-used-1",
        label: "Was the O-ring kit used?",
        required: true,
        bom_line_id: "",
    },
};
