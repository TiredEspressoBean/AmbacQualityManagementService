/**
 * Recursive rule builder.
 *
 * Renders a ConditionGroup as a bordered container with an AND/OR toggle and
 * a stack of child rows. Children are leaves, smart-token chips, or nested
 * groups (which recurse). Nesting depth is capped to keep authoring sane.
 *
 * Smart tokens render as a single horizontal chip with inline parameter
 * editors — no field/operator dropdowns, since a token like "Assigned to me"
 * is conceptually a single noun.
 */
import { Plus, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

import {
    SmartTokenIcon,
    SmartTokenRow,
} from "@/components/notifications/SmartTokenRow";
import {
    appendToGroup,
    defaultConditionFor,
    defaultSmartTokenInstance,
    fieldLabel,
    newGroup,
    operatorsForType,
    removeNode,
    SMART_TOKENS,
    updateNode,
    type ConditionGroup,
    type ConditionLeaf,
    type ConditionNode,
    type Conjunction,
    type SimpleOperator,
    type SmartTokenDef,
} from "@/lib/notifications/simpleConditions";
import type { PayloadField } from "@/lib/notifications/payloadSchemas";

const MAX_DEPTH = 3;

interface Props {
    fields: PayloadField[];
    root: ConditionGroup;
    onChange: (root: ConditionGroup) => void;
}

export function SimpleConditionBuilder({ fields, root, onChange }: Props) {
    const applicableTokens = SMART_TOKENS.filter((t) => t.appliesTo(fields));

    const addLeafTo = (groupId: string) => {
        const first = fields.find((f) => operatorsForType(f.type).length > 0);
        if (!first) return;
        onChange(appendToGroup(root, groupId, defaultConditionFor(first)));
    };

    const addTokenTo = (groupId: string, def: SmartTokenDef) => {
        onChange(appendToGroup(root, groupId, defaultSmartTokenInstance(def)));
    };

    const addGroupTo = (groupId: string) => {
        onChange(appendToGroup(root, groupId, newGroup("or")));
    };

    const remove = (id: string) => onChange(removeNode(root, id));

    const updateLeaf = (id: string, patch: Partial<ConditionLeaf>) => {
        onChange(
            updateNode(root, id, (n) =>
                n.kind === "condition" ? { ...n, ...patch } : n,
            ),
        );
    };

    const updateToken = (id: string, params: Record<string, string | number>) => {
        onChange(
            updateNode(root, id, (n) =>
                n.kind === "smart-token" ? { ...n, params } : n,
            ),
        );
    };

    const updateGroupConjunction = (id: string, conjunction: Conjunction) => {
        onChange(
            updateNode(root, id, (n) =>
                n.kind === "group" ? { ...n, conjunction } : n,
            ),
        );
    };

    return (
        <div className="space-y-3">
            {applicableTokens.length > 0 && (
                <QuickAddRow
                    tokens={applicableTokens}
                    onPick={(def) => addTokenTo(root.id, def)}
                />
            )}
            <GroupView
                group={root}
                fields={fields}
                depth={0}
                isRoot
                onAddLeaf={addLeafTo}
                onAddToken={addTokenTo}
                onAddGroup={addGroupTo}
                onRemove={remove}
                onUpdateLeaf={updateLeaf}
                onUpdateToken={updateToken}
                onUpdateGroupConjunction={updateGroupConjunction}
                applicableTokens={applicableTokens}
            />
        </div>
    );
}

// ---------------------------------------------------------------------------
// Group view (recursive)
// ---------------------------------------------------------------------------

interface GroupViewProps {
    group: ConditionGroup;
    fields: PayloadField[];
    depth: number;
    isRoot?: boolean;
    onAddLeaf: (groupId: string) => void;
    onAddToken: (groupId: string, def: SmartTokenDef) => void;
    onAddGroup: (groupId: string) => void;
    onRemove: (id: string) => void;
    onUpdateLeaf: (id: string, patch: Partial<ConditionLeaf>) => void;
    onUpdateToken: (id: string, params: Record<string, string | number>) => void;
    onUpdateGroupConjunction: (id: string, c: Conjunction) => void;
    applicableTokens: SmartTokenDef[];
}

function GroupView(props: GroupViewProps) {
    const {
        group,
        fields,
        depth,
        isRoot,
        onAddLeaf,
        onAddToken,
        onAddGroup,
        onRemove,
        onUpdateLeaf,
        onUpdateToken,
        onUpdateGroupConjunction,
        applicableTokens,
    } = props;

    const canAddGroup = depth + 1 < MAX_DEPTH;
    const isEmpty = group.children.length === 0;

    return (
        <div
            className={cn(
                "rounded-md border",
                isRoot ? "border-border" : "border-l-2 border-l-primary/40",
                isRoot ? "" : "bg-muted/20",
            )}
        >
            <div className="flex items-center justify-between gap-2 px-3 py-2 border-b bg-muted/40 rounded-t-md">
                <div className="flex items-center gap-2">
                    {group.children.length > 1 ? (
                        <ConjunctionToggle
                            value={group.conjunction}
                            onChange={(v) => onUpdateGroupConjunction(group.id, v)}
                        />
                    ) : (
                        <span className="text-xs text-muted-foreground">
                            Match {group.conjunction === "and" ? "all" : "any"} of
                        </span>
                    )}
                </div>
                {!isRoot && (
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => onRemove(group.id)}
                        aria-label="Remove group"
                    >
                        <X className="h-4 w-4" />
                    </Button>
                )}
            </div>

            <div className="p-3 space-y-2">
                {isEmpty ? (
                    <p className="text-xs text-muted-foreground text-center py-2">
                        Empty — add a condition or smart token below.
                    </p>
                ) : (
                    group.children.map((child) => (
                        <ChildView
                            key={child.id}
                            node={child}
                            fields={fields}
                            depth={depth + 1}
                            onAddLeaf={onAddLeaf}
                            onAddToken={onAddToken}
                            onAddGroup={onAddGroup}
                            onRemove={onRemove}
                            onUpdateLeaf={onUpdateLeaf}
                            onUpdateToken={onUpdateToken}
                            onUpdateGroupConjunction={onUpdateGroupConjunction}
                            applicableTokens={applicableTokens}
                        />
                    ))
                )}

                <div className="flex flex-wrap items-center gap-1.5 pt-1">
                    <Button
                        variant="outline"
                        size="sm"
                        className="h-7 text-xs"
                        onClick={() => onAddLeaf(group.id)}
                    >
                        <Plus className="h-3.5 w-3.5 mr-1" />
                        Condition
                    </Button>
                    {canAddGroup && (
                        <Button
                            variant="outline"
                            size="sm"
                            className="h-7 text-xs"
                            onClick={() => onAddGroup(group.id)}
                        >
                            <Plus className="h-3.5 w-3.5 mr-1" />
                            Group
                        </Button>
                    )}
                </div>
            </div>
        </div>
    );
}

function ChildView(props: Omit<GroupViewProps, "group" | "isRoot"> & { node: ConditionNode }) {
    const { node, fields } = props;
    if (node.kind === "group") {
        return <GroupView {...props} group={node} />;
    }
    if (node.kind === "smart-token") {
        return (
            <SmartTokenRow
                token={node}
                onUpdate={(params) => props.onUpdateToken(node.id, params)}
                onRemove={() => props.onRemove(node.id)}
            />
        );
    }
    return (
        <ConditionRow
            condition={node}
            fields={fields.filter((f) => operatorsForType(f.type).length > 0)}
            onChange={(patch) => props.onUpdateLeaf(node.id, patch)}
            onRemove={() => props.onRemove(node.id)}
        />
    );
}

// ---------------------------------------------------------------------------
// Conjunction toggle
// ---------------------------------------------------------------------------

function ConjunctionToggle({
    value,
    onChange,
}: {
    value: Conjunction;
    onChange: (v: Conjunction) => void;
}) {
    return (
        <div className="inline-flex rounded-md border p-0.5 bg-background">
            <Button
                type="button"
                size="sm"
                variant={value === "and" ? "default" : "ghost"}
                className="h-6 px-2.5 text-[11px]"
                onClick={() => onChange("and")}
            >
                ALL (AND)
            </Button>
            <Button
                type="button"
                size="sm"
                variant={value === "or" ? "default" : "ghost"}
                className="h-6 px-2.5 text-[11px]"
                onClick={() => onChange("or")}
            >
                ANY (OR)
            </Button>
        </div>
    );
}

// ---------------------------------------------------------------------------
// Quick-add row (smart token shortcuts)
// ---------------------------------------------------------------------------

function QuickAddRow({
    tokens,
    onPick,
}: {
    tokens: SmartTokenDef[];
    onPick: (t: SmartTokenDef) => void;
}) {
    return (
        <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs text-muted-foreground mr-1">Quick add:</span>
            {tokens.map((def) => (
                <Button
                    key={def.id}
                    variant="outline"
                    size="sm"
                    className="h-7 text-xs"
                    onClick={() => onPick(def)}
                >
                    <SmartTokenIcon name={def.icon} className="h-3.5 w-3.5 mr-1.5" />
                    {def.label.replace(/\{[^}]+\}/g, "…")}
                </Button>
            ))}
        </div>
    );
}

// ---------------------------------------------------------------------------
// Standard condition row
// ---------------------------------------------------------------------------

function ConditionRow({
    condition,
    fields,
    onChange,
    onRemove,
}: {
    condition: ConditionLeaf;
    fields: PayloadField[];
    onChange: (patch: Partial<ConditionLeaf>) => void;
    onRemove: () => void;
}) {
    const field = fields.find((f) => f.name === condition.field) ?? fields[0];
    const ops = operatorsForType(field.type);
    const currentOpValid = ops.some((o) => o.op === condition.operator);
    const operator = currentOpValid ? condition.operator : (ops[0]?.op ?? "equals");

    const onFieldChange = (next: string) => {
        const nextField = fields.find((f) => f.name === next);
        if (!nextField) return;
        if (nextField.type === field.type) {
            onChange({ field: next });
            return;
        }
        const reset = defaultConditionFor(nextField);
        onChange({ field: reset.field, operator: reset.operator, value: reset.value });
    };

    return (
        <div className="flex flex-wrap items-start gap-2 rounded-md border p-2 bg-background">
            <div className="flex-1 min-w-[160px]">
                <Select value={field.name} onValueChange={onFieldChange}>
                    <SelectTrigger className="h-9">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        {fields.map((f) => (
                            <SelectItem key={f.name} value={f.name}>
                                {fieldLabel(f)}
                                <span className="text-muted-foreground text-xs ml-2">
                                    {f.type}
                                </span>
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>
            </div>
            <div className="min-w-[140px]">
                <Select
                    value={operator}
                    onValueChange={(v) => onChange({ operator: v as SimpleOperator })}
                >
                    <SelectTrigger className="h-9">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        {ops.map((o) => (
                            <SelectItem key={o.op} value={o.op}>
                                {o.label}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>
            </div>
            <div className="flex-1 min-w-[180px]">
                <ValueInput
                    field={field}
                    operator={operator}
                    value={condition.value}
                    onChange={(v) => onChange({ value: v })}
                />
            </div>
            <Button
                variant="ghost"
                size="icon"
                onClick={onRemove}
                aria-label="Remove condition"
                className="h-9 w-9 shrink-0"
            >
                <X className="h-4 w-4" />
            </Button>
        </div>
    );
}

function ValueInput({
    field,
    operator,
    value,
    onChange,
}: {
    field: PayloadField;
    operator: SimpleOperator;
    value: ConditionLeaf["value"];
    onChange: (v: ConditionLeaf["value"]) => void;
}) {
    if (operator === "in") {
        const arr = Array.isArray(value) ? value : value ? [String(value)] : [];
        if (field.enum && field.enum.length > 0) {
            return (
                <div className="flex flex-wrap gap-1.5">
                    {field.enum.map((opt) => {
                        const selected = arr.includes(opt);
                        return (
                            <button
                                key={opt}
                                type="button"
                                onClick={() =>
                                    onChange(
                                        selected
                                            ? arr.filter((x) => x !== opt)
                                            : [...arr, opt],
                                    )
                                }
                                className={cn(
                                    "text-xs rounded-md border px-2 py-1.5 transition-colors",
                                    selected
                                        ? "bg-primary text-primary-foreground border-primary"
                                        : "bg-background hover:bg-muted",
                                )}
                            >
                                {opt}
                            </button>
                        );
                    })}
                </div>
            );
        }
        return (
            <Input
                className="h-9"
                placeholder="comma, separated, values"
                value={arr.join(", ")}
                onChange={(e) =>
                    onChange(
                        e.target.value
                            .split(",")
                            .map((s) => s.trim())
                            .filter(Boolean),
                    )
                }
            />
        );
    }

    if (field.type === "number") {
        return (
            <Input
                className="h-9"
                type="number"
                value={typeof value === "number" ? value : (value as string) ?? ""}
                onChange={(e) =>
                    onChange(e.target.value === "" ? "" : Number(e.target.value))
                }
            />
        );
    }

    if (field.enum && field.enum.length > 0) {
        const v = typeof value === "string" ? value : "";
        return (
            <Select value={v || field.enum[0]} onValueChange={onChange}>
                <SelectTrigger className="h-9">
                    <SelectValue />
                </SelectTrigger>
                <SelectContent>
                    {field.enum.map((opt) => (
                        <SelectItem key={opt} value={opt}>
                            {opt}
                        </SelectItem>
                    ))}
                </SelectContent>
            </Select>
        );
    }

    return (
        <Input
            className="h-9"
            value={typeof value === "string" ? value : ""}
            onChange={(e) => onChange(e.target.value)}
        />
    );
}
