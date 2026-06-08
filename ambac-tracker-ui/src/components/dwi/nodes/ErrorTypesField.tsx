/**
 * ErrorTypesField — captures defect findings on an inspection event. Each
 * row is one finding: an `ErrorType` (from `QualityErrorsList`) plus per-
 * instance severity / location / notes / count. Maps to
 * `QualityReportDefect` rows when the substep promotes to `QualityReports`.
 *
 * This is the multi-row node that carries the Pareto-analysis fields the
 * existing QA form already collects, just exposed as a composable substep
 * primitive so any inspection-point substep can request defect findings.
 *
 * Engineer authoring: label, required, allowed error-type filter (TODO —
 * for now operator sees all error types), min_rows.
 * Operator capture: array of `{ error_type_id, severity, location?, notes?, count }`.
 */
import { Node, mergeAttributes } from "@tiptap/core";
import {
    NodeViewWrapper,
    ReactNodeViewRenderer,
    type NodeViewProps,
} from "@tiptap/react";
import { Bug, Plus, X } from "lucide-react";
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
import { useRetrieveErrorTypes } from "@/hooks/useRetrieveErrorTypes";

type Severity = "MINOR" | "MAJOR" | "CRITICAL";

const SEVERITY_LABELS: Record<Severity, string> = {
    MINOR: "Minor",
    MAJOR: "Major",
    CRITICAL: "Critical",
};
const SEVERITIES: Severity[] = ["MINOR", "MAJOR", "CRITICAL"];
const SEVERITY_CLS: Record<Severity, string> = {
    MINOR: "text-blue-600",
    MAJOR: "text-amber-600",
    CRITICAL: "text-destructive",
};

type Attrs = {
    node_id: string;
    label: string;
    required: boolean;
    min_rows: number;
    default_severity: Severity;
};

type ResponseRow = {
    error_type_id: number;
    severity: Severity;
    location?: string;
    notes?: string;
    count: number;
};

type ErrorTypeShape = { id: number; error_name: string };

export function ErrorTypesFieldEditForm({ node, updateAttributes }: NodeViewProps) {
    const a = node.attrs as Attrs;
    const update = useDebouncedAttrs(updateAttributes, 250);
    return (
        <div className="space-y-3">
            <TextAttrRow attrName="label" label="Label" initial={a.label} update={update} />
            <div className="space-y-1">
                <Label className="text-xs">Default severity for new rows</Label>
                <Select
                    value={a.default_severity}
                    onValueChange={(v) => updateAttributes({ default_severity: v })}
                >
                    <SelectTrigger className="h-8 text-sm">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        {SEVERITIES.map((s) => (
                            <SelectItem key={s} value={s}>{SEVERITY_LABELS[s]}</SelectItem>
                        ))}
                    </SelectContent>
                </Select>
            </div>
            <div className="grid grid-cols-3 items-center gap-2">
                <Label className="text-xs">Min rows</Label>
                <Input
                    type="number"
                    min={0}
                    value={String(a.min_rows ?? 0)}
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

    const { data: errorTypesResp } = useRetrieveErrorTypes();
    const errorTypes = (errorTypesResp?.results ?? []) as ErrorTypeShape[];

    const update = (next: ResponseRow[]) => {
        if (!isOperator) return;
        setValue(next);
    };
    const addRow = () => {
        const first = errorTypes[0];
        if (!first) return;
        update([
            ...rows,
            {
                error_type_id: first.id,
                severity: (a.default_severity || "MAJOR") as Severity,
                count: 1,
            },
        ]);
    };
    const setRow = (i: number, patch: Partial<ResponseRow>) => {
        const next = rows.slice();
        next[i] = { ...next[i], ...patch };
        update(next);
    };
    const removeRow = (i: number) => update(rows.filter((_, j) => j !== i));

    const card = (
        <NodeCard
            icon={<Bug className="h-4 w-4 text-muted-foreground" />}
            label={a.label || "Defect findings"}
            badges={
                <>
                    {a.required && <Badge variant="secondary" className="text-[10px]">Required</Badge>}
                    {isOperator && rows.length > 0 && (
                        <Badge variant="destructive" className="text-[10px]">
                            {rows.length} finding{rows.length === 1 ? "" : "s"}
                        </Badge>
                    )}
                </>
            }
        >
            <div className="space-y-1.5" contentEditable={false}>
                {rows.map((row, i) => (
                    <div key={i} className="space-y-1 rounded border bg-background p-1.5">
                        <div className="flex items-center gap-1">
                            <select
                                disabled={!isOperator}
                                value={row.error_type_id}
                                onChange={(e) => setRow(i, { error_type_id: Number(e.target.value) })}
                                className="h-7 flex-1 rounded border bg-background px-2 text-xs"
                            >
                                {errorTypes.map((et) => (
                                    <option key={et.id} value={et.id}>{et.error_name}</option>
                                ))}
                            </select>
                            <select
                                disabled={!isOperator}
                                value={row.severity}
                                onChange={(e) => setRow(i, { severity: e.target.value as Severity })}
                                className={`h-7 w-24 rounded border bg-background px-1 text-xs font-medium ${SEVERITY_CLS[row.severity]}`}
                            >
                                {SEVERITIES.map((s) => (
                                    <option key={s} value={s}>{SEVERITY_LABELS[s]}</option>
                                ))}
                            </select>
                            {isOperator && (
                                <Button
                                    type="button"
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => removeRow(i)}
                                    className="h-7 w-7 p-0"
                                >
                                    <X className="h-3 w-3" />
                                </Button>
                            )}
                        </div>
                        <div className="flex items-center gap-1">
                            <Input
                                type="text"
                                disabled={!isOperator}
                                value={row.location ?? ""}
                                placeholder="Location (e.g. near bore #3)"
                                onChange={(e) => setRow(i, { location: e.target.value })}
                                className="h-7 flex-1 text-xs"
                            />
                            <Input
                                type="number"
                                min={1}
                                disabled={!isOperator}
                                value={String(row.count ?? 1)}
                                onChange={(e) => setRow(i, { count: Math.max(1, Number(e.target.value) || 1) })}
                                className="h-7 w-14 text-xs"
                                title="Count"
                            />
                        </div>
                    </div>
                ))}
                {rows.length === 0 && (
                    <div className="text-xs italic text-muted-foreground">
                        {isOperator ? "No defects found." : "Operator logs defects here."}
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
                        <Plus className="mr-1 h-3 w-3" /> Add defect
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

export const ErrorTypesField = Node.create({
    name: "errorTypesField",
    group: "block",
    atom: true,
    selectable: true,
    draggable: true,
    addAttributes() {
        return {
            node_id: { default: "" },
            label: { default: "Defect findings" },
            required: { default: false },
            min_rows: { default: 0 },
            default_severity: { default: "MAJOR" },
        };
    },
    parseHTML() {
        return [{ tag: 'div[data-type="error-types-field"]' }];
    },
    renderHTML({ HTMLAttributes }) {
        return [
            "div",
            mergeAttributes(HTMLAttributes, { "data-type": "error-types-field" }),
            `[DEFECTS] ${HTMLAttributes.label || ""}`,
        ];
    },
    addNodeView() {
        return ReactNodeViewRenderer(View);
    },
});

export const SAMPLE_ERROR_TYPES = {
    type: "errorTypesField",
    attrs: {
        node_id: "seed-error-types-1",
        label: "Defects observed",
        required: false,
        min_rows: 0,
        default_severity: "MAJOR",
    },
};
