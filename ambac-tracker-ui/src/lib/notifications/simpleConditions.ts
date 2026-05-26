/**
 * Tree-based representation of a rule's CEL condition for the form builder.
 *
 *   ConditionGroup (root)
 *     conjunction: 'and' | 'or'
 *     children: ConditionNode[]
 *
 * Each ConditionNode is one of:
 *   - ConditionLeaf   — [field][operator][value]
 *   - SmartTokenInstance — pre-shaped chip like "Assigned to me"
 *   - ConditionGroup  — recursive subgroup (parenthesized in CEL)
 *
 * The editor maintains a tree; CEL is generated from the tree on every change.
 * When loading an existing rule, we try to parse the CEL back into the tree
 * shape; anything we can't recover (mixed && / ||, nested function calls,
 * unsupported operators) forces Advanced mode.
 */
import type { CelType, PayloadField } from "./payloadSchemas";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type SimpleOperator =
    | "equals"
    | "not_equals"
    | "gt"
    | "gte"
    | "lt"
    | "lte"
    | "in"
    | "contains";

export type Conjunction = "and" | "or";

export interface ConditionLeaf {
    id: string;
    kind: "condition";
    field: string;
    operator: SimpleOperator;
    value: string | number | string[];
}

export interface SmartTokenInstance {
    id: string;
    kind: "smart-token";
    tokenId: string;
    /** Editable parameters; shape depends on the token definition. */
    params: Record<string, string | number>;
}

export interface ConditionGroup {
    id: string;
    kind: "group";
    conjunction: Conjunction;
    children: ConditionNode[];
}

export type ConditionNode = ConditionLeaf | SmartTokenInstance | ConditionGroup;

// ---------------------------------------------------------------------------
// Operator metadata
// ---------------------------------------------------------------------------

export interface OperatorDef {
    op: SimpleOperator;
    label: string;
    english: string;
    cel: string;
}

const STRING_OPS: OperatorDef[] = [
    { op: "equals", label: "equals", english: "equals", cel: "==" },
    { op: "not_equals", label: "does not equal", english: "does not equal", cel: "!=" },
    { op: "in", label: "is one of", english: "is one of", cel: "in" },
    { op: "contains", label: "contains", english: "contains", cel: "contains" },
];

const NUMBER_OPS: OperatorDef[] = [
    { op: "equals", label: "equals", english: "equals", cel: "==" },
    { op: "not_equals", label: "does not equal", english: "does not equal", cel: "!=" },
    { op: "gt", label: "greater than", english: "is greater than", cel: ">" },
    { op: "gte", label: "at least", english: "is at least", cel: ">=" },
    { op: "lt", label: "less than", english: "is less than", cel: "<" },
    { op: "lte", label: "at most", english: "is at most", cel: "<=" },
];

const BOOL_OPS: OperatorDef[] = [
    { op: "equals", label: "is", english: "is", cel: "==" },
];

const UUID_OPS: OperatorDef[] = [
    { op: "equals", label: "equals", english: "equals", cel: "==" },
    { op: "not_equals", label: "does not equal", english: "does not equal", cel: "!=" },
];

export function operatorsForType(type: CelType): OperatorDef[] {
    switch (type) {
        case "string":
            return STRING_OPS;
        case "number":
            return NUMBER_OPS;
        case "boolean":
            return BOOL_OPS;
        case "uuid":
            return UUID_OPS;
        case "datetime":
            return [];
    }
}

export function operatorDef(type: CelType, op: SimpleOperator): OperatorDef | undefined {
    return operatorsForType(type).find((o) => o.op === op);
}

export function fieldLabel(field: PayloadField): string {
    return field.label ?? humanize(field.name);
}

function humanize(name: string): string {
    return name
        .split("_")
        .map((w) => (w.length ? w[0].toUpperCase() + w.slice(1) : w))
        .join(" ");
}

export function newId(prefix = "c"): string {
    return `${prefix}-${Math.random().toString(36).slice(2, 9)}`;
}

// ---------------------------------------------------------------------------
// Smart tokens — pre-shaped conditions for self-reference and relative time
// ---------------------------------------------------------------------------

export interface SmartTokenParam {
    key: string;
    label: string;
    /** "number" gets an inline number input; "enum" gets a select. */
    type: "number" | "enum";
    default: string | number;
    /** Enum options when `type === 'enum'`. */
    options?: readonly string[];
}

export interface SmartTokenDef {
    id: string;
    label: string;
    /** Lucide icon name to render inside the chip (kept generic to avoid an icon dep here). */
    icon: "user" | "calendar" | "alert" | "tag";
    params: SmartTokenParam[];
    /** True iff this token can apply to the current event's payload. */
    appliesTo: (fields: PayloadField[]) => boolean;
    /** Generate CEL for an instance of this token on the current event. */
    toCel: (params: Record<string, string | number>, fields: PayloadField[]) => string;
    /** Plain-English chunk to render inside the readback. */
    english: (params: Record<string, string | number>) => string;
}

function firstFieldOfType(fields: PayloadField[], type: CelType): PayloadField | undefined {
    return fields.find((f) => f.type === type);
}

export const SMART_TOKENS: SmartTokenDef[] = [
    {
        id: "assigned-to-me",
        label: "Assigned to me",
        icon: "user",
        params: [],
        appliesTo: (fields) => fields.some((f) => f.name === "assigned_to_id"),
        toCel: () => "payload.assigned_to_id == owner_user.id",
        english: () => "is assigned to me",
    },
    {
        id: "opened-by-me",
        label: "Opened by me",
        icon: "user",
        params: [],
        appliesTo: (fields) => fields.some((f) => f.name === "opened_by_id"),
        toCel: () => "payload.opened_by_id == owner_user.id",
        english: () => "was opened by me",
    },
    {
        id: "critical-severity",
        label: "Severity is {severity}",
        icon: "alert",
        params: [
            {
                key: "severity",
                label: "severity",
                type: "enum",
                default: "critical",
                options: ["minor", "major", "critical"],
            },
        ],
        appliesTo: (fields) =>
            fields.some((f) => f.name === "severity" && f.enum && f.enum.length > 0),
        toCel: (params) => `payload.severity == '${params.severity}'`,
        english: (params) => `severity is ${params.severity}`,
    },
    {
        id: "in-last-n-days",
        label: "In the last {days} days",
        icon: "calendar",
        params: [{ key: "days", label: "days", type: "number", default: 7 }],
        appliesTo: (fields) => Boolean(firstFieldOfType(fields, "datetime")),
        toCel: (params, fields) => {
            const field = firstFieldOfType(fields, "datetime");
            if (!field) return "";
            return `payload.${field.name} > now() - duration("${params.days}d")`;
        },
        english: (params) => `in the last ${params.days} days`,
    },
];

export function getSmartToken(id: string): SmartTokenDef | undefined {
    return SMART_TOKENS.find((t) => t.id === id);
}

export function defaultSmartTokenInstance(def: SmartTokenDef): SmartTokenInstance {
    const params: Record<string, string | number> = {};
    for (const p of def.params) params[p.key] = p.default;
    return { id: newId("tok"), kind: "smart-token", tokenId: def.id, params };
}

// ---------------------------------------------------------------------------
// Defaults / constructors
// ---------------------------------------------------------------------------

export function emptyRootGroup(): ConditionGroup {
    return { id: newId("g"), kind: "group", conjunction: "and", children: [] };
}

export function defaultConditionFor(field: PayloadField): ConditionLeaf {
    const ops = operatorsForType(field.type);
    const op: SimpleOperator = ops[0]?.op ?? "equals";
    const value: ConditionLeaf["value"] =
        field.type === "number"
            ? 0
            : field.enum && field.enum.length > 0
              ? field.enum[0]
              : "";
    return { id: newId(), kind: "condition", field: field.name, operator: op, value };
}

export function newGroup(conjunction: Conjunction = "and"): ConditionGroup {
    return { id: newId("g"), kind: "group", conjunction, children: [] };
}

// ---------------------------------------------------------------------------
// CEL generation (recursive)
// ---------------------------------------------------------------------------

export function nodeToCel(
    node: ConditionNode,
    fields: PayloadField[],
    parentJoiner?: Conjunction,
): string {
    if (node.kind === "condition") return conditionToCel(node, fields);
    if (node.kind === "smart-token") {
        const def = getSmartToken(node.tokenId);
        if (!def) return "";
        return def.toCel(node.params, fields);
    }
    // Group: render children joined by its conjunction, parenthesize when it
    // differs from the parent (or any time we're nested inside another group).
    const parts = node.children
        .map((c) => nodeToCel(c, fields, node.conjunction))
        .filter((s) => s.length > 0);
    if (parts.length === 0) return "";
    if (parts.length === 1) return parts[0];
    const joiner = node.conjunction === "and" ? " && " : " || ";
    const joined = parts.join(joiner);
    if (parentJoiner && parentJoiner !== node.conjunction) {
        return `(${joined})`;
    }
    return joined;
}

export function rootToCel(root: ConditionGroup, fields: PayloadField[]): string {
    return nodeToCel(root, fields);
}

function conditionToCel(condition: ConditionLeaf, fields: PayloadField[]): string {
    const field = fields.find((f) => f.name === condition.field);
    if (!field) return "";
    const opDef = operatorDef(field.type, condition.operator);
    if (!opDef) return "";

    if (condition.operator === "in") {
        const arr = Array.isArray(condition.value)
            ? condition.value
            : [String(condition.value)];
        if (arr.length === 0) return "";
        const literals = arr
            .map((v) => formatLiteral(field.type, v))
            .filter((s) => s.length > 0)
            .join(", ");
        return `payload.${field.name} in [${literals}]`;
    }
    if (condition.operator === "contains") {
        const lit = formatLiteral(field.type, condition.value);
        if (!lit) return "";
        return `payload.${field.name}.contains(${lit})`;
    }
    const lit = formatLiteral(field.type, condition.value);
    if (!lit && lit !== "0") return "";
    return `payload.${field.name} ${opDef.cel} ${lit}`;
}

function formatLiteral(type: CelType, raw: string | number | string[]): string {
    if (Array.isArray(raw)) return "";
    if (type === "number") {
        if (raw === "" || raw === null || raw === undefined) return "";
        const n = typeof raw === "number" ? raw : Number(raw);
        return Number.isFinite(n) ? String(n) : "";
    }
    if (type === "boolean") {
        return raw === true || raw === "true" ? "true" : "false";
    }
    const s = String(raw);
    if (!s) return "";
    return JSON.stringify(s);
}

// ---------------------------------------------------------------------------
// English readback (recursive)
// ---------------------------------------------------------------------------

export interface EnglishPart {
    text: string;
    emphasis?: boolean;
}

export function rootToEnglish(root: ConditionGroup, fields: PayloadField[]): EnglishPart[] {
    if (root.children.length === 0) return [{ text: "always" }];
    return groupToEnglish(root, fields, /* topLevel */ true);
}

function groupToEnglish(
    group: ConditionGroup,
    fields: PayloadField[],
    topLevel: boolean,
): EnglishPart[] {
    // Drop children that don't contribute (empty subgroups) so the readback
    // mirrors the CEL emission: incomplete groups are silently skipped.
    const contributing = group.children.filter(
        (c) => !(c.kind === "group" && c.children.length === 0),
    );
    if (contributing.length === 0) {
        return topLevel ? [{ text: "always" }] : [{ text: "(empty group)" }];
    }
    const parts: EnglishPart[] = [];
    if (!topLevel) parts.push({ text: "(" });
    contributing.forEach((child, i) => {
        if (i > 0) {
            parts.push({ text: group.conjunction === "and" ? " AND " : " OR " });
        }
        parts.push(...nodeToEnglish(child, fields));
    });
    if (!topLevel) parts.push({ text: ")" });
    return parts;
}

function nodeToEnglish(node: ConditionNode, fields: PayloadField[]): EnglishPart[] {
    if (node.kind === "group") return groupToEnglish(node, fields, false);
    if (node.kind === "smart-token") {
        const def = getSmartToken(node.tokenId);
        if (!def) return [{ text: "(unknown token)" }];
        return [{ text: def.english(node.params), emphasis: true }];
    }
    return conditionToEnglish(node, fields);
}

function conditionToEnglish(condition: ConditionLeaf, fields: PayloadField[]): EnglishPart[] {
    const field = fields.find((f) => f.name === condition.field);
    if (!field) return [{ text: `(unknown field: ${condition.field})` }];
    const opDef = operatorDef(field.type, condition.operator);
    if (!opDef) return [{ text: `(unsupported operator on ${fieldLabel(field)})` }];

    if (condition.operator === "in") {
        const arr = Array.isArray(condition.value)
            ? condition.value
            : [String(condition.value)];
        return [
            { text: fieldLabel(field), emphasis: true },
            { text: ` ${opDef.english} ` },
            { text: arr.length ? arr.join(", ") : "(empty)", emphasis: true },
        ];
    }
    return [
        { text: fieldLabel(field), emphasis: true },
        { text: ` ${opDef.english} ` },
        { text: displayValue(condition.value), emphasis: true },
    ];
}

function displayValue(value: ConditionLeaf["value"]): string {
    if (Array.isArray(value)) return value.join(", ");
    if (value === "" || value === null || value === undefined) return "(empty)";
    return String(value);
}

// ---------------------------------------------------------------------------
// Parser — flat-only. Anything with parens forces Advanced.
// ---------------------------------------------------------------------------

/**
 * Best-effort parse of a CEL string into a single flat root group.
 *
 * Nested-group parsing is out of scope for v1 — if the user authored nested
 * groups in the builder, saving and reloading will round-trip via Advanced
 * mode. The parser handles the round-trip case for flat single-level rules,
 * which is the common case.
 */
export function parseCelToRoot(
    source: string,
    fields: PayloadField[],
): ConditionGroup | null {
    const trimmed = source.trim();
    if (!trimmed) return emptyRootGroup();

    if (trimmed.includes("(") && !isOnlyContainsParens(trimmed)) return null;
    if (trimmed.includes("&&") && trimmed.includes("||")) return null;

    const splitOn = trimmed.includes("||") ? "||" : "&&";
    const conjunction: Conjunction = splitOn === "||" ? "or" : "and";

    const segments = trimmed.split(splitOn).map((s) => s.trim()).filter(Boolean);
    const children: ConditionNode[] = [];
    for (const segment of segments) {
        const parsed = parseSegment(segment, fields);
        if (!parsed) return null;
        children.push(parsed);
    }
    return { id: newId("g"), kind: "group", conjunction, children };
}

/**
 * `.contains(...)` calls are the only parens we allow on the simple path.
 * Otherwise any `(` means the user used grouping the parser doesn't handle.
 */
function isOnlyContainsParens(source: string): boolean {
    const stripped = source.replace(/\.contains\([^()]*\)/g, "");
    return !stripped.includes("(");
}

function parseSegment(segment: string, fields: PayloadField[]): ConditionNode | null {
    // Smart tokens encoded as their canonical CEL form — try matching those first
    // so round-trip from the builder preserves the chip representation.
    for (const def of SMART_TOKENS) {
        if (!def.appliesTo(fields)) continue;
        const instance = tryMatchSmartToken(def, segment, fields);
        if (instance) return instance;
    }

    const containsMatch = segment.match(
        /^payload\.([a-zA-Z_][a-zA-Z0-9_]*)\.contains\((.+)\)$/,
    );
    if (containsMatch) {
        const field = fields.find((f) => f.name === containsMatch[1]);
        if (!field || field.type !== "string") return null;
        const literal = unquote(containsMatch[2].trim());
        if (literal === null) return null;
        return {
            id: newId(),
            kind: "condition",
            field: field.name,
            operator: "contains",
            value: literal,
        };
    }

    const inMatch = segment.match(/^payload\.([a-zA-Z_][a-zA-Z0-9_]*)\s+in\s+\[(.+)\]$/);
    if (inMatch) {
        const field = fields.find((f) => f.name === inMatch[1]);
        if (!field) return null;
        const items = splitArrayItems(inMatch[2]);
        if (items === null) return null;
        return {
            id: newId(),
            kind: "condition",
            field: field.name,
            operator: "in",
            value: items,
        };
    }

    const binMatch = segment.match(
        /^payload\.([a-zA-Z_][a-zA-Z0-9_]*)\s*(==|!=|>=|<=|>|<)\s*(.+)$/,
    );
    if (binMatch) {
        const field = fields.find((f) => f.name === binMatch[1]);
        if (!field) return null;
        const opMap: Record<string, SimpleOperator> = {
            "==": "equals",
            "!=": "not_equals",
            ">": "gt",
            ">=": "gte",
            "<": "lt",
            "<=": "lte",
        };
        const op = opMap[binMatch[2]];
        if (!op) return null;
        const raw = binMatch[3].trim();
        const value = parseLiteral(field.type, raw);
        if (value === null) return null;
        return {
            id: newId(),
            kind: "condition",
            field: field.name,
            operator: op,
            value,
        };
    }

    return null;
}

/**
 * Generate the token's expected CEL for the default param permutation and
 * a couple of common variations, then string-compare. Cheap and accurate
 * enough for v1 round-trip; replace with a CEL AST match when the backend
 * lands a proper parser.
 */
function tryMatchSmartToken(
    def: SmartTokenDef,
    segment: string,
    fields: PayloadField[],
): SmartTokenInstance | null {
    if (def.params.length === 0) {
        const expected = def.toCel({}, fields);
        if (expected && segment === expected) {
            return { id: newId("tok"), kind: "smart-token", tokenId: def.id, params: {} };
        }
        return null;
    }
    if (def.id === "critical-severity") {
        for (const opt of def.params[0].options ?? []) {
            const expected = def.toCel({ severity: opt }, fields);
            if (segment === expected) {
                return {
                    id: newId("tok"),
                    kind: "smart-token",
                    tokenId: def.id,
                    params: { severity: opt },
                };
            }
        }
    }
    if (def.id === "in-last-n-days") {
        const field = firstFieldOfType(fields, "datetime");
        if (!field) return null;
        const regex = new RegExp(
            `^payload\\.${field.name} > now\\(\\) - duration\\("(\\d+)d"\\)$`,
        );
        const m = segment.match(regex);
        if (m) {
            return {
                id: newId("tok"),
                kind: "smart-token",
                tokenId: def.id,
                params: { days: Number(m[1]) },
            };
        }
    }
    return null;
}

function parseLiteral(type: CelType, raw: string): string | number | null {
    if (type === "number") {
        const n = Number(raw);
        return Number.isFinite(n) ? n : null;
    }
    return unquote(raw);
}

function unquote(raw: string): string | null {
    const trimmed = raw.trim();
    if (trimmed.length < 2) return null;
    const first = trimmed[0];
    const last = trimmed[trimmed.length - 1];
    if ((first === "'" || first === '"') && first === last) {
        return trimmed.slice(1, -1);
    }
    return null;
}

function splitArrayItems(inner: string): string[] | null {
    const items = inner.split(",").map((s) => s.trim()).filter(Boolean);
    const result: string[] = [];
    for (const item of items) {
        const lit = unquote(item);
        if (lit === null) return null;
        result.push(lit);
    }
    return result;
}

// ---------------------------------------------------------------------------
// Tree mutation helpers — return new trees, don't mutate.
// ---------------------------------------------------------------------------

export function updateNode(
    root: ConditionGroup,
    nodeId: string,
    updater: (node: ConditionNode) => ConditionNode,
): ConditionGroup {
    return updateGroup(root, nodeId, updater);
}

function updateGroup(
    group: ConditionGroup,
    nodeId: string,
    updater: (node: ConditionNode) => ConditionNode,
): ConditionGroup {
    if (group.id === nodeId) {
        const updated = updater(group);
        return updated.kind === "group" ? updated : group;
    }
    return {
        ...group,
        children: group.children.map((c) => {
            if (c.id === nodeId) return updater(c);
            if (c.kind === "group") return updateGroup(c, nodeId, updater);
            return c;
        }),
    };
}

export function removeNode(root: ConditionGroup, nodeId: string): ConditionGroup {
    return {
        ...root,
        children: root.children
            .filter((c) => c.id !== nodeId)
            .map((c) => (c.kind === "group" ? removeNode(c, nodeId) : c)),
    };
}

export function appendToGroup(
    root: ConditionGroup,
    targetGroupId: string,
    child: ConditionNode,
): ConditionGroup {
    if (root.id === targetGroupId) {
        return { ...root, children: [...root.children, child] };
    }
    return {
        ...root,
        children: root.children.map((c) =>
            c.kind === "group" ? appendToGroup(c, targetGroupId, child) : c,
        ),
    };
}
