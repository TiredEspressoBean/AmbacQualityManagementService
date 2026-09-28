/** RebuildFindingCapture — reman DWI node: a component found worse after teardown.
 *
 * Teardown graded every component, and the grades resolved the rebuild. Sometimes one
 * turns out worse at the bench — a reused nozzle fails its spray test, a seat that
 * looked fine is pitted once cleaned. The operator records it here.
 *
 * A finding is a PROPOSAL, not a change: the grade drives the slot's resolution and so
 * the rebuild's scope, and on a repair-and-return unit scope is the customer's bill. A
 * lead applies or dismisses each finding from the rebuild plan
 * (services/reman/findings.py). This node only ever records.
 *
 * Operator response (OperatorResponseContext, keyed by node_id):
 *   { rows: [{ harvested_id, grade, finding }] } — one per component found worse
 * `build-captures` sends it as kind `rebuild_finding`.
 */
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Node, mergeAttributes } from "@tiptap/core";
import { NodeViewWrapper, ReactNodeViewRenderer, type NodeViewProps } from "@tiptap/react";
import { SearchCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { api } from "@/lib/api/generated";
import { NodeCard } from "../shared/NodeCard";
import { AuthoringPopover } from "../shared/AuthoringPopover";
import { useDebouncedAttrs } from "../shared/useDebouncedAttrs";
import { TextAttrRow } from "../shared/AttrInputs";
import { useOperatorResponse } from "../shared/OperatorResponseContext";
import { usePartContext } from "../shared/PartContext";

type Attrs = { node_id: string; label: string; required: boolean };

export type FindingRow = { harvested_id: string; grade: string; finding: string };
type CapturedValue = { rows: FindingRow[] };

const GRADES = [
    { value: "A", label: "A — serviceable" },
    { value: "B", label: "B — serviceable" },
    { value: "C", label: "C — needs reconditioning" },
    { value: "SCRAP", label: "Scrap — not usable" },
];

export function RebuildFindingCaptureEditForm({ node, updateAttributes }: NodeViewProps) {
    const a = node.attrs as Attrs;
    const update = useDebouncedAttrs(updateAttributes, 250);
    return (
        <div className="space-y-3">
            <TextAttrRow attrName="label" label="Label" initial={a.label} update={update} />
            <p className="text-[11px] text-muted-foreground">
                At runtime this lists the unit's own components, and the operator can flag
                any found worse than teardown graded it. Each finding waits for a lead to
                apply or dismiss it on the rebuild plan — recording one changes nothing.
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

function OperatorRuntime({ captured, setCaptured }: {
    captured: CapturedValue;
    setCaptured: (next: CapturedValue) => void;
}) {
    const { part_id } = usePartContext();
    const partQ = useQuery({
        queryKey: ["dwi-finding", "part", part_id],
        queryFn: () => api.api_Parts_retrieve({ params: { id: String(part_id) } }),
        enabled: !!part_id,
    });
    const coreId = partQ.data?.core_role ? String(partQ.data.core_role) : null;
    const compsQ = useQuery({
        queryKey: ["dwi-finding", "components", coreId],
        queryFn: () => api.api_HarvestedComponents_list({
            queries: { core: coreId!, is_scrapped: false, limit: 200 },
        }),
        enabled: !!coreId,
    });
    const components = compsQ.data?.results ?? [];
    const byId = useMemo(() => new Map(captured.rows.map((r) => [r.harvested_id, r])), [captured.rows]);

    const setRow = (id: string, row: FindingRow | null) => {
        const others = captured.rows.filter((r) => r.harvested_id !== id);
        setCaptured({ rows: row ? [...others, row] : others });
    };

    if (!part_id) return <p className="text-xs text-muted-foreground">Open this step on a unit to record a finding.</p>;
    if (partQ.isLoading || compsQ.isLoading) return <p className="text-xs text-muted-foreground">Loading this unit's components…</p>;
    if (!coreId) return <p className="text-xs text-muted-foreground">This unit is not a reman core, so there are no teardown grades to revisit.</p>;
    if (components.length === 0) return <p className="text-xs text-muted-foreground">No components were recovered from this unit.</p>;

    return (
        <div className="space-y-2">
            {components.map((c) => {
                const id = String(c.id);
                const row = byId.get(id);
                const pending = !!c.proposed_grade;
                return (
                    <div key={id} className={`space-y-2 rounded border p-2 ${row ? "border-amber-400/70 bg-amber-50/40 dark:bg-amber-950/20" : ""}`}>
                        <div className="flex items-center justify-between gap-3">
                            <div className="min-w-0 text-sm">
                                <div className="truncate font-medium">{c.component_type_name}</div>
                                <div className="text-xs text-muted-foreground">
                                    {c.position || "no position"} · teardown grade {c.condition_grade}
                                </div>
                            </div>
                            {pending ? (
                                <Badge variant="outline" className="shrink-0 text-[10px]">
                                    Finding awaiting a lead (grade {c.proposed_grade})
                                </Badge>
                            ) : (
                                <label className="flex shrink-0 items-center gap-2 text-xs">
                                    <Switch
                                        checked={!!row}
                                        onCheckedChange={(on) =>
                                            setRow(id, on ? { harvested_id: id, grade: "", finding: "" } : null)}
                                    />
                                    Found worse
                                </label>
                            )}
                        </div>
                        {row && !pending && (
                            <div className="grid grid-cols-[9rem_minmax(0,1fr)] gap-2">
                                <Select value={row.grade || undefined}
                                        onValueChange={(v) => setRow(id, { ...row, grade: v })}>
                                    <SelectTrigger className="h-8 text-sm"><SelectValue placeholder="New grade" /></SelectTrigger>
                                    <SelectContent>
                                        {GRADES.filter((g) => g.value !== c.condition_grade).map((g) => (
                                            <SelectItem key={g.value} value={g.value}>{g.label}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                                <input
                                    type="text"
                                    placeholder="What did you find?"
                                    className="rounded border bg-background px-2 py-1 text-sm"
                                    value={row.finding}
                                    onChange={(e) => setRow(id, { ...row, finding: e.target.value })}
                                />
                            </div>
                        )}
                    </div>
                );
            })}
            <p className="text-xs text-muted-foreground">
                A finding changes nothing until a lead applies it on the rebuild plan.
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
                    icon={<SearchCheck className="h-4 w-4 text-muted-foreground" />}
                    label={a.label || "Rebuild finding"}
                    badges={<>
                        {a.required && <Badge variant="secondary" className="text-[10px]">Required</Badge>}
                        {isOperator && captured.rows.length > 0 && (
                            <Badge variant="default" className="text-[10px]">{captured.rows.length} finding{captured.rows.length === 1 ? "" : "s"}</Badge>
                        )}
                    </>}
                >
                    <div contentEditable={false} className="space-y-2 text-sm">
                        {isOperator ? (
                            <OperatorRuntime captured={captured} setCaptured={(next) => setValue(next)} />
                        ) : (
                            <div className="rounded-md border border-dashed bg-muted/30 p-3 text-xs text-muted-foreground">
                                Operator-only surface. At runtime this lists the unit's own
                                components so the operator can flag any found worse than teardown
                                graded it, for a lead to decide.
                            </div>
                        )}
                    </div>
                </NodeCard>
            </AuthoringPopover>
        </NodeViewWrapper>
    );
}

export const RebuildFindingCapture = Node.create({
    name: "rebuildFindingCapture",
    group: "block",
    atom: true,
    selectable: true,
    draggable: true,
    addAttributes() {
        return {
            node_id: { default: "" },
            label: { default: "Rebuild finding" },
            required: { default: false },
        };
    },
    parseHTML() {
        return [{ tag: 'div[data-type="rebuild-finding-capture"]' }];
    },
    renderHTML({ HTMLAttributes }) {
        return [
            "div",
            mergeAttributes(HTMLAttributes, { "data-type": "rebuild-finding-capture" }),
            `[FINDING] ${HTMLAttributes.label || "Rebuild finding"}`,
        ];
    },
    addNodeView() {
        return ReactNodeViewRenderer(View);
    },
});

export const SAMPLE_REBUILD_FINDING_CAPTURE = {
    type: "rebuildFindingCapture",
    attrs: {
        node_id: "seed-finding-1",
        label: "Anything found worse than teardown graded it?",
        required: false,
    },
};
