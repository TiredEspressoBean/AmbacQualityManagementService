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
import { Bug } from "lucide-react";
import { Badge } from "@/components/ui/badge";
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
import { DefectRowsEditor } from "@/components/quality/DefectRowsEditor";

type Severity = "MINOR" | "MAJOR" | "CRITICAL";

const SEVERITY_LABELS: Record<Severity, string> = {
    MINOR: "Minor",
    MAJOR: "Major",
    CRITICAL: "Critical",
};
const SEVERITIES: Severity[] = ["MINOR", "MAJOR", "CRITICAL"];

type Attrs = {
    node_id: string;
    label: string;
    required: boolean;
    min_rows: number;
    default_severity: Severity;
};

// The shape DefectRowsEditor edits (DefectRow).
type ResponseRow = {
    // QualityErrorsList UUID (string) — was `number`, and the select's onChange
    // ran Number() on the UUID (NaN whenever the operator changed defect type).
    error_type_id: string;
    severity: Severity;
    location?: string;
    notes?: string;
    count: number;
};

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

    const update = (next: ResponseRow[]) => {
        if (!isOperator) return;
        setValue(next);
    };

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
            <div contentEditable={false}>
                {/* The shared defect editor (components/quality/DefectRowsEditor). */}
                <DefectRowsEditor
                    rows={rows}
                    onChange={update}
                    disabled={!isOperator}
                    defaultSeverity={(a.default_severity || "MAJOR") as Severity}
                    emptyText={isOperator ? "No defects found." : "Operator logs defects here."}
                />
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
