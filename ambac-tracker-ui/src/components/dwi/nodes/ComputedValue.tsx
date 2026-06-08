/**
 * ComputedValue — declared variables + formula, evaluated live for the
 * operator. Engineer authors:
 *   - variables: [{ name, label, unit }] — N declared input variables
 *   - formula: expression referencing the variables by name
 *   - result_label / result_unit / display_precision
 *   - nominal, upper_tol, lower_tol — unified spec language; same semantics
 *     as MeasurementInput.
 *
 * Operator sees one numeric input per variable; formula evaluates live and
 * an in-spec / out-of-spec badge updates per input.
 */
import { useEffect, useMemo } from "react";
import { Node, mergeAttributes } from "@tiptap/core";
import {
    NodeViewWrapper,
    ReactNodeViewRenderer,
    type NodeViewProps,
} from "@tiptap/react";
import { Calculator, Plus, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { NodeCard } from "../shared/NodeCard";
import { AuthoringPopover } from "../shared/AuthoringPopover";
import { useDebouncedAttrs } from "../shared/useDebouncedAttrs";
import { DecimalAttrInput, TextAttrRow } from "../shared/AttrInputs";
import { useOperatorResponse } from "../shared/OperatorResponseContext";
import { usePartContext } from "../shared/PartContext";
import { FORMULA_PARSER } from "@/lib/dwi/expr";
import { useRetrieveMeasurementDefinitions } from "@/hooks/useRetrieveMeasurementDefinitions";
import { useStepExecutionMeasurements } from "@/hooks/useStepExecutionMeasurements";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";

/** Source of a ComputedValue input variable. Lets engineers bind a formula
 *  input to an existing MeasurementDefinition so the operator doesn't have
 *  to re-type a value they already captured upstream (True Position from
 *  X / Y deviation captures, CPK from accumulated readings, etc.).
 *
 *  - `manual`: operator types the value
 *  - `measurement_definition`: read the most-recent matching
 *    `StepExecutionMeasurement` for the current `StepExecution` (provided
 *    via `PartContext.step_execution_id`)
 *
 *  Future `spc` source (aggregates: last-N average, range, CPK, drift) is
 *  reserved but not wired — drop in once a use case surfaces. */
type VariableSource = "manual" | "measurement_definition";
type ComputedVariable = {
    name: string;
    label: string;
    unit: string;
    source?: VariableSource;
    source_id?: string | number | null;
};
type ComputedResponse = {
    inputs: Record<string, string>;
    result: number | null;
    in_spec: boolean | null;
};

type Attrs = {
    node_id: string;
    label: string;
    variables: ComputedVariable[];
    formula: string;
    result_label: string;
    result_unit: string;
    nominal: number | null;
    upper_tol: number | null;
    lower_tol: number | null;
    display_precision: number;
    required: boolean;
};

function VariablesEditor({
    variables,
    update,
}: {
    variables: ComputedVariable[];
    update: (next: ComputedVariable[]) => void;
}) {
    const { data: defsResp } = useRetrieveMeasurementDefinitions();
    const defs = (defsResp?.results ?? []) as Array<{
        id: string | number;
        label?: string | null;
        unit?: string | null;
    }>;

    const addRow = () => {
        const next = variables.slice();
        const nextName = `X${next.length + 1}`;
        next.push({ name: nextName, label: nextName, unit: "", source: "manual" });
        update(next);
    };
    const setRow = (i: number, partial: Partial<ComputedVariable>) => {
        const next = variables.slice();
        next[i] = { ...next[i], ...partial };
        update(next);
    };
    const removeRow = (i: number) => update(variables.filter((_, j) => j !== i));

    return (
        <div className="space-y-2">
            <Label className="text-xs">Variables</Label>
            {variables.map((v, i) => {
                const source = (v.source ?? "manual") as VariableSource;
                return (
                    <div key={i} className="space-y-1 rounded border bg-background/40 p-1.5">
                        <div className="flex items-center gap-1">
                            <Input
                                value={v.name}
                                onChange={(e) => setRow(i, { name: e.target.value })}
                                className="h-7 w-16 font-mono text-xs"
                                placeholder="name"
                            />
                            <Input
                                value={v.label}
                                onChange={(e) => setRow(i, { label: e.target.value })}
                                className="h-7 flex-1 text-xs"
                                placeholder="label"
                            />
                            <Input
                                value={v.unit}
                                onChange={(e) => setRow(i, { unit: e.target.value })}
                                className="h-7 w-14 text-xs"
                                placeholder="unit"
                            />
                            <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                onClick={() => removeRow(i)}
                                className="h-7 w-7 p-0"
                            >
                                <X className="h-3 w-3" />
                            </Button>
                        </div>
                        <div className="flex items-center gap-1">
                            <Select
                                value={source}
                                onValueChange={(next) => {
                                    if (next === "manual") {
                                        setRow(i, { source: "manual", source_id: null });
                                    } else {
                                        setRow(i, { source: next as VariableSource });
                                    }
                                }}
                            >
                                <SelectTrigger className="h-7 w-44 text-xs">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="manual">Operator input</SelectItem>
                                    <SelectItem value="measurement_definition">
                                        Linked measurement
                                    </SelectItem>
                                </SelectContent>
                            </Select>
                            {source === "measurement_definition" && (
                                <Select
                                    value={v.source_id ? String(v.source_id) : ""}
                                    onValueChange={(next) =>
                                        setRow(i, { source_id: next })
                                    }
                                >
                                    <SelectTrigger className="h-7 flex-1 text-xs">
                                        <SelectValue placeholder="— pick measurement —" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {defs.map((d) => (
                                            <SelectItem
                                                key={String(d.id)}
                                                value={String(d.id)}
                                                className="text-xs"
                                            >
                                                {d.label ?? `Measurement ${d.id}`}
                                                {d.unit ? ` (${d.unit})` : ""}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            )}
                        </div>
                    </div>
                );
            })}
            <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={addRow}
                className="h-7 w-full justify-start text-xs text-muted-foreground"
            >
                <Plus className="mr-1 h-3 w-3" /> Add variable
            </Button>
        </div>
    );
}

export function ComputedValueEditForm({ node, updateAttributes }: NodeViewProps) {
    const a = node.attrs as Attrs;
    const update = useDebouncedAttrs(updateAttributes, 250);
    return (
        <div className="space-y-3">
            <TextAttrRow attrName="label" label="Label" initial={a.label} update={update} />
            <VariablesEditor
                variables={Array.isArray(a.variables) ? a.variables : []}
                update={(next) => updateAttributes({ variables: next })}
            />
            <TextAttrRow
                attrName="formula"
                label="Formula"
                initial={a.formula}
                update={update}
                monospace
            />
            <div className="grid grid-cols-2 gap-2">
                <TextAttrRow attrName="result_label" label="Result label" initial={a.result_label} update={update} />
                <TextAttrRow attrName="result_unit" label="Unit" initial={a.result_unit} update={update} />
            </div>
            <DecimalAttrInput attrName="nominal" label="Nominal" initial={a.nominal} update={update} />
            <DecimalAttrInput attrName="upper_tol" label="+ Tol" initial={a.upper_tol} update={update} />
            <DecimalAttrInput attrName="lower_tol" label="− Tol" initial={a.lower_tol} update={update} />
            <DecimalAttrInput
                attrName="display_precision"
                label="Decimals"
                initial={a.display_precision ?? 4}
                update={update}
            />
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
    const isOperator = !editor.isEditable;
    const { value, setValue } = useOperatorResponse(a.node_id);
    const part = usePartContext();
    const stepExecutionId = part.step_execution_id
        ? String(part.step_execution_id)
        : null;

    const variables = (Array.isArray(a.variables) ? a.variables : []) as ComputedVariable[];

    const { data: defsResp } = useRetrieveMeasurementDefinitions();
    const defLabelById = useMemo(() => {
        const map: Record<string, string> = {};
        const rows = (defsResp?.results ?? []) as Array<{
            id: string | number;
            label?: string | null;
        }>;
        for (const d of rows) map[String(d.id)] = d.label ?? `Measurement ${d.id}`;
        return map;
    }, [defsResp]);

    // Linked-source variables — those bound to a real MeasurementDefinition.
    // Their values come from `StepExecutionMeasurement` queries against the
    // current step_execution, not operator input.
    const linkedVars = useMemo(
        () =>
            variables.filter(
                (v) => v.source === "measurement_definition" && v.source_id,
            ),
        [variables],
    );
    const { data: measurementsResp } = useStepExecutionMeasurements(
        stepExecutionId && linkedVars.length > 0 && isOperator
            ? { step_execution: stepExecutionId }
            : undefined,
    );

    /** measurement_definition_id → most-recent recorded value (as string).
     *  String preserves operator-facing precision when the upstream capture
     *  was a free-typed value. */
    const linkedValuesByDefId = useMemo(() => {
        const map: Record<string, string> = {};
        const rows = (measurementsResp as { results?: unknown[] } | undefined)?.results ?? [];
        // Most recent first by created_at if available
        const sorted = [...rows].sort((a: unknown, b: unknown) => {
            const at = new Date(
                (a as { created_at?: string }).created_at ?? 0,
            ).getTime();
            const bt = new Date(
                (b as { created_at?: string }).created_at ?? 0,
            ).getTime();
            return bt - at;
        });
        for (const v of linkedVars) {
            const sid = String(v.source_id);
            const match = sorted.find((r: unknown) => {
                const row = r as { measurement_definition?: string | number; value?: unknown };
                return String(row.measurement_definition) === sid;
            }) as { value?: unknown; string_value?: unknown } | undefined;
            if (!match) continue;
            const raw = match.value ?? match.string_value;
            if (raw != null && raw !== "") map[sid] = String(raw);
        }
        return map;
    }, [measurementsResp, linkedVars]);
    const formula = (a.formula ?? "") as string;
    const nominal = a.nominal;
    const upperTol = a.upper_tol;
    const lowerTol = a.lower_tol;
    const resultLabel = a.result_label || "Result";
    const resultUnit = a.result_unit || "";
    const required = a.required === true;
    const displayPrecision = Number.isFinite(a.display_precision)
        ? Math.max(0, Math.min(10, Number(a.display_precision)))
        : 4;
    const hasSpec = nominal != null && (upperTol != null || lowerTol != null);

    const captured = (value as ComputedResponse | undefined) ?? null;
    const inputs = captured?.inputs ?? {};
    const result = captured?.result ?? null;
    const inSpec = captured?.in_spec ?? null;

    const parsedFormula = useMemo(() => {
        try {
            return { ok: true as const, expr: FORMULA_PARSER.parse(formula) };
        } catch (e) {
            return { ok: false as const, error: e instanceof Error ? e.message : String(e) };
        }
    }, [formula]);

    /** Reapply the formula + spec check to a candidate inputs map and push
     *  the result back into the response context. Pure data — no UI side
     *  effects. Used by both operator typing and the linked-measurement
     *  auto-fill effect below. */
    const commitInputs = (newInputs: Record<string, string>) => {
        const numericInputs: Record<string, number> = {};
        let allValid = variables.length > 0;
        for (const v of variables) {
            const raw = newInputs[v.name];
            if (raw == null || raw === "") {
                allValid = false;
                continue;
            }
            const n = Number(raw);
            if (!Number.isFinite(n)) {
                allValid = false;
                continue;
            }
            numericInputs[v.name] = n;
        }
        let nextResult: number | null = null;
        let nextInSpec: boolean | null = null;
        if (parsedFormula.ok && allValid) {
            try {
                const evald = parsedFormula.expr.evaluate(numericInputs);
                if (typeof evald === "number" && Number.isFinite(evald)) {
                    nextResult = evald;
                    if (hasSpec) {
                        const lo = nominal! - (lowerTol ?? Number.POSITIVE_INFINITY);
                        const hi = nominal! + (upperTol ?? Number.POSITIVE_INFINITY);
                        nextInSpec = evald >= lo && evald <= hi;
                    }
                }
            } catch {
                // runtime error — leave nulls
            }
        }
        setValue({
            inputs: newInputs,
            result: nextResult,
            in_spec: nextInSpec,
        } satisfies ComputedResponse);
    };

    const setInput = (name: string, rawValue: string) => {
        if (!isOperator) return;
        const newInputs = { ...inputs };
        if (rawValue === "") delete newInputs[name];
        else newInputs[name] = rawValue;
        commitInputs(newInputs);
    };

    // Auto-fill linked-source variables from their MeasurementDefinition's
    // most recent capture on this StepExecution. Only writes when the
    // upstream value differs from what's currently in inputs, so we don't
    // loop or overwrite operator edits to manual-source variables.
    useEffect(() => {
        if (!isOperator) return;
        if (Object.keys(linkedValuesByDefId).length === 0) return;
        let changed = false;
        const next = { ...inputs };
        for (const v of linkedVars) {
            const sid = String(v.source_id);
            const upstream = linkedValuesByDefId[sid];
            if (upstream != null && next[v.name] !== upstream) {
                next[v.name] = upstream;
                changed = true;
            }
        }
        if (changed) commitInputs(next);
        // We deliberately exclude `inputs` from deps to avoid re-firing on
        // every commitInputs round-trip; the upstream values drive this
        // effect, and reconciliation handles drift naturally.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [linkedValuesByDefId, isOperator]);

    const allFilled =
        variables.length > 0 &&
        variables.every((v) => v.name in inputs && inputs[v.name] !== "");

    const card = (
        <NodeCard
            icon={<Calculator className="h-4 w-4 text-muted-foreground" />}
            label={a.label || "Computed value"}
            badges={
                <>
                    <Badge variant="outline" className="text-[10px]">
                        {variables.length} var{variables.length === 1 ? "" : "s"}
                    </Badge>
                    {required && <Badge variant="secondary" className="text-[10px]">Required</Badge>}
                    {isOperator && inSpec === true && (
                        <Badge className="bg-green-600 text-[10px] text-white">In spec</Badge>
                    )}
                    {isOperator && inSpec === false && (
                        <Badge variant="destructive" className="text-[10px]">Out of spec</Badge>
                    )}
                    {isOperator && allFilled && inSpec === null && result === null && parsedFormula.ok && (
                        <Badge variant="destructive" className="text-[10px]">Calc error</Badge>
                    )}
                </>
            }
            rightSlot={
                hasSpec
                    ? `${nominal}${upperTol != null ? ` +${upperTol}` : ""}${
                          lowerTol != null ? ` −${lowerTol}` : ""
                      }${resultUnit ? " " + resultUnit : ""}`
                    : null
            }
        >
            <div contentEditable={false} className="space-y-2">
                <div className="rounded bg-muted/50 px-2 py-1 font-mono text-xs">
                    {resultLabel} ={" "}
                    <span className="font-semibold">{formula || "(no formula)"}</span>
                    {!parsedFormula.ok && (
                        <span className="ml-2 text-destructive">
                            · syntax error: {parsedFormula.error}
                        </span>
                    )}
                </div>

                <div className="space-y-1.5">
                    {variables.map((v) => {
                        const isLinked =
                            v.source === "measurement_definition" && v.source_id != null;
                        const sid = v.source_id != null ? String(v.source_id) : "";
                        const linkedLabel = isLinked ? defLabelById[sid] : undefined;
                        const linkedHasValue = isLinked && sid in linkedValuesByDefId;
                        return (
                            <div key={v.name} className="flex items-center gap-2 text-sm">
                                <span className="w-40 text-xs text-muted-foreground">
                                    {v.label || v.name}{" "}
                                    <span className="font-mono opacity-70">({v.name})</span>
                                </span>
                                <input
                                    type="text"
                                    inputMode="decimal"
                                    disabled={!isOperator || isLinked}
                                    readOnly={isLinked}
                                    value={inputs[v.name] ?? ""}
                                    onChange={(e) => setInput(v.name, e.target.value)}
                                    placeholder={isLinked ? "—" : "—"}
                                    className={
                                        "w-24 rounded border px-2 py-1 font-mono text-sm " +
                                        (isLinked
                                            ? "bg-muted text-muted-foreground"
                                            : "bg-background")
                                    }
                                />
                                {v.unit && (
                                    <span className="text-xs text-muted-foreground">{v.unit}</span>
                                )}
                                {isLinked && (
                                    <span className="text-[10px] text-muted-foreground italic">
                                        {linkedHasValue
                                            ? `auto from ${linkedLabel ?? "linked measurement"}`
                                            : `waiting on ${linkedLabel ?? "linked measurement"}`}
                                    </span>
                                )}
                            </div>
                        );
                    })}
                </div>

                <div className="flex items-center gap-2 rounded border bg-background/60 px-2 py-1.5">
                    <span className="text-xs font-medium">{resultLabel}:</span>
                    <span className="font-mono text-sm tabular-nums">
                        {result != null ? result.toFixed(displayPrecision) : "—"}
                    </span>
                    {resultUnit && (
                        <span className="text-xs text-muted-foreground">{resultUnit}</span>
                    )}
                    {hasSpec && (
                        <span className="ml-auto text-[10px] text-muted-foreground">
                            {(() => {
                                const lo = nominal! - (lowerTol ?? Number.POSITIVE_INFINITY);
                                const hi = nominal! + (upperTol ?? Number.POSITIVE_INFINITY);
                                const fmt = (x: number) =>
                                    Number.isFinite(x) ? x.toFixed(displayPrecision) : "∞";
                                return `spec: [${fmt(lo)}, ${fmt(hi)}]${
                                    resultUnit ? " " + resultUnit : ""
                                }`;
                            })()}
                        </span>
                    )}
                </div>
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

export const ComputedValue = Node.create({
    name: "computedValue",
    group: "block",
    atom: true,
    selectable: true,
    draggable: true,
    addAttributes() {
        return {
            node_id: { default: "" },
            label: { default: "" },
            variables: { default: [] },
            formula: { default: "" },
            result_label: { default: "Result" },
            result_unit: { default: "" },
            nominal: { default: null },
            upper_tol: { default: null },
            lower_tol: { default: null },
            display_precision: { default: 4 },
            required: { default: false },
        };
    },
    parseHTML() {
        return [{ tag: 'div[data-type="computed-value"]' }];
    },
    renderHTML({ HTMLAttributes }) {
        return [
            "div",
            mergeAttributes(HTMLAttributes, { "data-type": "computed-value" }),
            `[CALC] ${HTMLAttributes.label || ""}: ${HTMLAttributes.formula || ""}`,
        ];
    },
    addNodeView() {
        return ReactNodeViewRenderer(View);
    },
});

export const SAMPLE_COMPUTED_TRUE_POSITION = {
    type: "computedValue",
    attrs: {
        node_id: "seed-tp-1",
        label: "OD true position check",
        variables: [
            { name: "X", label: "X deviation", unit: "in" },
            { name: "Y", label: "Y deviation", unit: "in" },
        ],
        formula: "2 * sqrt(X^2 + Y^2)",
        result_label: "TP",
        result_unit: "in",
        nominal: 0,
        upper_tol: 0.005,
        lower_tol: 0,
        display_precision: 5,
        required: true,
    },
};
