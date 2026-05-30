import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { Node, mergeAttributes } from "@tiptap/core";
import {
    useEditor,
    EditorContent,
    ReactNodeViewRenderer,
    NodeViewWrapper,
    NodeViewContent,
    type Editor,
    type NodeViewProps,
} from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { Parser as ExprParser } from "expr-eval";
// generateHTML import removed — the preview pane is now a live operator-mode
// editor instead of a static HTML render. For PDF / email rendering later,
// `generateHTML(json, DWI_EXTENSIONS)` from @tiptap/html is the path.

// Single shared expression parser — expr-eval Parser instances are stateless
// and can be reused across all ComputedValue nodes.
const FORMULA_PARSER = new ExprParser();

import {
    ResizableHandle,
    ResizablePanel,
    ResizablePanelGroup,
} from "@/components/ui/resizable";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
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
import {
    Bold,
    Italic,
    Strikethrough,
    Code,
    Heading1,
    Heading2,
    List,
    ListOrdered,
    Quote,
    Minus,
    Undo,
    Redo,
    Pencil,
    Eye,
    Braces,
    FlaskConical,
    Gauge,
    Ruler,
    AlertTriangle,
    Info,
    Bell,
    Shield,
    Image as ImageIcon,
    CheckSquare,
    PenLine,
    Type,
    ListChecks,
    Camera,
    ScanLine,
    Paperclip,
    ChevronDown,
    ChevronRight,
    GripVertical,
    Plus,
    Timer as TimerIcon,
    Play,
    Square,
    Calculator,
    Settings,
} from "lucide-react";

// ============================================================================
// Custom node helpers
// ============================================================================

type CalloutVariant = "caution" | "note" | "reminder" | "safety";
const CALLOUT_CONFIG: Record<
    CalloutVariant,
    { label: string; icon: React.ComponentType<{ className?: string }>; cls: string }
> = {
    caution: { label: "Caution", icon: AlertTriangle, cls: "border-amber-500/40 bg-amber-50/40 dark:bg-amber-950/20" },
    note: { label: "Note", icon: Info, cls: "border-blue-500/40 bg-blue-50/40 dark:bg-blue-950/20" },
    reminder: { label: "Reminder", icon: Bell, cls: "border-purple-500/40 bg-purple-50/40 dark:bg-purple-950/20" },
    safety: { label: "Safety", icon: Shield, cls: "border-red-500/40 bg-red-50/40 dark:bg-red-950/20" },
};

function NodeCard({
    icon,
    label,
    badges,
    rightSlot,
    children,
    className = "",
}: {
    icon: React.ReactNode;
    label: string;
    badges?: React.ReactNode;
    rightSlot?: React.ReactNode;
    children?: React.ReactNode;
    className?: string;
}) {
    return (
        <div className={`rounded-md border bg-muted/30 p-3 ${className}`}>
            <div className="flex flex-wrap items-center gap-2">
                {icon}
                <span className="font-medium">{label}</span>
                {badges}
                {rightSlot && <span className="ml-auto text-xs text-muted-foreground">{rightSlot}</span>}
            </div>
            {children && <div className="mt-2">{children}</div>}
        </div>
    );
}

// ============================================================================
// Operator response store
// ============================================================================
//
// When the editor renders in `editable: false` mode (the right preview pane),
// capture-node form fields become real interactive inputs. Their values land in
// this context, keyed by each node's stable `node_id`. The editor JSON itself
// is never mutated — the substep document stays the engineer's template.
//
// In production this would route to the backend (`SubstepResponse`,
// `SubstepGateCompletion`, `StepExecutionMeasurement`). For the spike it's just
// local React state so we can demonstrate the data flow end-to-end visually.

type OperatorResponses = Record<string, unknown>;

type OperatorResponseContextValue = {
    responses: OperatorResponses;
    setResponse: (node_id: string, value: unknown) => void;
};

const OperatorResponseContext = createContext<OperatorResponseContextValue | null>(null);

function useOperatorResponse(node_id: string | undefined) {
    const ctx = useContext(OperatorResponseContext);
    if (!ctx || !node_id) {
        return { value: undefined, setValue: () => {} } as const;
    }
    return {
        value: ctx.responses[node_id],
        setValue: (v: unknown) => ctx.setResponse(node_id, v),
    } as const;
}

// Tiny UUID helper — `crypto.randomUUID()` is available in modern browsers.
function newNodeId() {
    if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
        return crypto.randomUUID();
    }
    return `node-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

// Toolbar inserts use this so each new node gets a fresh `node_id` attr.
function withFreshNodeId<T extends { attrs?: Record<string, unknown> }>(sample: T): T {
    return { ...sample, attrs: { ...(sample.attrs ?? {}), node_id: newNodeId() } };
}

// ============================================================================
// Authoring popover infrastructure
// ============================================================================
//
// Engineer-mode interaction model per decision #7 in the design doc: hover a
// capture node → small gear button appears top-right → click opens a shadcn
// Popover containing the node's attr form. Form fields write via
// `updateAttributes` from NodeViewProps with a 250ms debounce, so typing
// doesn't flood the undo stack one keystroke at a time.

type AttrPartial = Record<string, unknown>;

function useDebouncedAttrs(
    updateAttributes: (attrs: AttrPartial) => void,
    ms = 250,
) {
    const pendingRef = useRef<AttrPartial>({});
    const timerRef = useRef<number | null>(null);

    useEffect(() => {
        return () => {
            if (timerRef.current != null) window.clearTimeout(timerRef.current);
        };
    }, []);

    return useCallback(
        (partial: AttrPartial) => {
            pendingRef.current = { ...pendingRef.current, ...partial };
            if (timerRef.current != null) window.clearTimeout(timerRef.current);
            timerRef.current = window.setTimeout(() => {
                updateAttributes(pendingRef.current);
                pendingRef.current = {};
                timerRef.current = null;
            }, ms);
        },
        [updateAttributes, ms],
    );
}

// Hover gear that opens the popover. Caller wraps the NodeCard in a
// `relative group` container; the gear becomes visible when the group is
// hovered or focused.
function HoverGearTrigger() {
    return (
        <PopoverTrigger asChild>
            <button
                type="button"
                aria-label="Edit attributes"
                contentEditable={false}
                className="absolute right-1.5 top-1.5 z-10 rounded p-1 text-muted-foreground opacity-0 transition-opacity hover:bg-muted hover:text-foreground focus:opacity-100 group-hover:opacity-100"
            >
                <Settings className="h-3.5 w-3.5" />
            </button>
        </PopoverTrigger>
    );
}

// Mock measurement-definition catalog. In production this is replaced by an
// autocomplete that queries `/api/measurement-definitions/` scoped to the
// authoring engineer's tenant — see decision in #4 (authoring popover).
type MockMeasurementDefinition = {
    id: string;
    label: string;
    unit: string;
    nominal: number;
    upper_tol: number;
    lower_tol: number;
    characteristic_number: string;
};
const MOCK_MEASUREMENT_DEFINITIONS: MockMeasurementDefinition[] = [
    { id: "md-1", label: "Outer Diameter", unit: "in", nominal: 1.247, upper_tol: 0.002, lower_tol: 0.002, characteristic_number: "B12" },
    { id: "md-2", label: "Wall Thickness", unit: "in", nominal: 0.08, upper_tol: 0.005, lower_tol: 0.005, characteristic_number: "C03" },
    { id: "md-3", label: "Bore Diameter", unit: "in", nominal: 0.625, upper_tol: 0.001, lower_tol: 0.001, characteristic_number: "B07" },
    { id: "md-4", label: "Flange Thickness", unit: "in", nominal: 0.25, upper_tol: 0.003, lower_tol: 0.003, characteristic_number: "F01" },
];

/**
 * MeasurementSpec custom node — proof-of-concept for DWI-specific blocks.
 *
 * Attributes mirror the `MeasurementDefinition` model at
 * PartsTracker/Tracker/models/mes_lite.py:309 so the JSON shape stored on a
 * future `Substep.body` lines up with how the spec is already defined elsewhere
 * in the system. When this lands in production, this file moves to
 * src/components/dwi/nodes/measurement-spec.{ts,tsx} and the React view
 * gets its own component file.
 */
type MeasurementSpecAttrs = {
    label: string;
    type: "NUMERIC" | "PASS_FAIL";
    unit: string;
    nominal: number | null;
    upper_tol: number | null;
    lower_tol: number | null;
    required: boolean;
    characteristic_number: string;
};

function MeasurementSpecView({ node }: NodeViewProps) {
    const a = node.attrs as MeasurementSpecAttrs;

    const tolerance =
        a.type === "NUMERIC" && a.nominal != null
            ? `${a.nominal}${a.upper_tol != null ? ` +${a.upper_tol}` : ""}${
                  a.lower_tol != null ? ` −${a.lower_tol}` : ""
              }${a.unit ? ` ${a.unit}` : ""}`
            : null;

    return (
        <NodeViewWrapper className="my-3 not-prose">
            <div className="rounded-md border bg-muted/30 p-3">
                <div className="flex flex-wrap items-center gap-2">
                    <Gauge className="h-4 w-4 text-muted-foreground" />
                    <span className="font-medium">{a.label || "Untitled measurement"}</span>
                    {a.characteristic_number && (
                        <Badge variant="outline" className="font-mono text-[10px]">
                            {a.characteristic_number}
                        </Badge>
                    )}
                    {a.required && (
                        <Badge variant="secondary" className="text-[10px]">
                            Required
                        </Badge>
                    )}
                    <span className="ml-auto text-xs text-muted-foreground">
                        {a.type === "NUMERIC" ? "Numeric" : "Pass / Fail"}
                    </span>
                </div>
                {tolerance && (
                    <div className="mt-2 font-mono text-sm tabular-nums">{tolerance}</div>
                )}
            </div>
        </NodeViewWrapper>
    );
}

const MeasurementSpec = Node.create({
    name: "measurementSpec",
    group: "block",
    atom: true,
    selectable: true,
    draggable: true,

    addAttributes() {
        return {
            label: { default: "" },
            type: { default: "NUMERIC" },
            unit: { default: "" },
            nominal: { default: null },
            upper_tol: { default: null },
            lower_tol: { default: null },
            required: { default: true },
            characteristic_number: { default: "" },
        };
    },

    parseHTML() {
        return [{ tag: 'div[data-type="measurement-spec"]' }];
    },

    renderHTML({ HTMLAttributes }) {
        // Plain HTML fallback for generateHTML / server-side rendering. The
        // interactive React view kicks in inside the editor.
        return [
            "div",
            mergeAttributes(HTMLAttributes, {
                "data-type": "measurement-spec",
                class:
                    "my-3 rounded-md border bg-muted/30 p-3 font-mono text-sm",
            }),
            `${HTMLAttributes.label || "Measurement"}: ${
                HTMLAttributes.nominal ?? "?"
            }${HTMLAttributes.upper_tol ? ` +${HTMLAttributes.upper_tol}` : ""}${
                HTMLAttributes.lower_tol ? ` −${HTMLAttributes.lower_tol}` : ""
            }${HTMLAttributes.unit ? ` ${HTMLAttributes.unit}` : ""}`,
        ];
    },

    addNodeView() {
        return ReactNodeViewRenderer(MeasurementSpecView);
    },
});

const SAMPLE_MEASUREMENT_SPEC = {
    type: "measurementSpec",
    attrs: {
        label: "Outer Diameter",
        type: "NUMERIC",
        unit: "in",
        nominal: 1.247,
        upper_tol: 0.002,
        lower_tol: 0.002,
        required: true,
        characteristic_number: "B12",
    },
};

// ============================================================================
// Callout — content node with caution / note / reminder / safety variants
// ============================================================================

function CalloutView({ node, updateAttributes, editor }: NodeViewProps) {
    const variant = (node.attrs.variant ?? "note") as CalloutVariant;
    const cfg = CALLOUT_CONFIG[variant];
    const Icon = cfg.icon;
    const isEditable = editor.isEditable;
    return (
        <NodeViewWrapper className="my-3 not-prose">
            <div className={`rounded-md border-2 p-3 ${cfg.cls}`}>
                <div
                    className="mb-1 flex items-center gap-2"
                    contentEditable={false}
                >
                    <Icon className="h-4 w-4" />
                    {isEditable ? (
                        <select
                            value={variant}
                            onChange={(e) => updateAttributes({ variant: e.target.value })}
                            className="rounded bg-transparent text-sm font-semibold focus:outline-none"
                            aria-label="Callout variant"
                        >
                            {(Object.keys(CALLOUT_CONFIG) as CalloutVariant[]).map((v) => (
                                <option key={v} value={v} className="bg-background text-foreground">
                                    {CALLOUT_CONFIG[v].label}
                                </option>
                            ))}
                        </select>
                    ) : (
                        <span className="text-sm font-semibold">{cfg.label}</span>
                    )}
                </div>
                {/* Inline-editable body — TipTap renders the child paragraphs here.
                    Click and type as if it were a normal paragraph block. */}
                <NodeViewContent className="text-sm [&_p]:my-1" />
            </div>
        </NodeViewWrapper>
    );
}

const Callout = Node.create({
    name: "callout",
    group: "block",
    content: "paragraph+",
    defining: true,
    selectable: true,
    draggable: true,
    addAttributes() {
        return {
            variant: { default: "note" },
        };
    },
    parseHTML() {
        return [{ tag: 'div[data-type="callout"]' }];
    },
    renderHTML({ HTMLAttributes }) {
        // 0 = "render children here". TipTap walks the content tree and inserts
        // child nodes at this position when serializing.
        return [
            "div",
            mergeAttributes(HTMLAttributes, {
                "data-type": "callout",
                "data-variant": HTMLAttributes.variant || "note",
                class: "my-3 rounded-md border-2 p-3",
            }),
            0,
        ];
    },
    addNodeView() {
        return ReactNodeViewRenderer(CalloutView);
    },
});

// ============================================================================
// Media — author-embedded image / video / 3D-model reference
// ============================================================================

function MediaView({ node }: NodeViewProps) {
    const { kind = "image", src = "", caption = "" } = node.attrs as {
        kind: "image" | "video" | "3d_model";
        src: string;
        caption: string;
    };
    return (
        <NodeViewWrapper className="my-3 not-prose">
            <NodeCard
                icon={<ImageIcon className="h-4 w-4 text-muted-foreground" />}
                label={caption || "Media"}
                badges={<Badge variant="outline" className="text-[10px] capitalize">{kind.replace("_", " ")}</Badge>}
                rightSlot={src ? "src set" : "no src"}
            >
                <div className="flex h-32 items-center justify-center rounded bg-muted text-xs text-muted-foreground">
                    {kind === "image" && "🖼 image preview"}
                    {kind === "video" && "▶ video preview"}
                    {kind === "3d_model" && "📦 3D model preview"}
                </div>
            </NodeCard>
        </NodeViewWrapper>
    );
}

const Media = Node.create({
    name: "media",
    group: "block",
    atom: true,
    selectable: true,
    draggable: true,
    addAttributes() {
        return {
            kind: { default: "image" },
            src: { default: "" },
            caption: { default: "" },
            document_id: { default: null },
        };
    },
    parseHTML() {
        return [{ tag: 'div[data-type="media"]' }];
    },
    renderHTML({ HTMLAttributes }) {
        return [
            "div",
            mergeAttributes(HTMLAttributes, { "data-type": "media" }),
            `[${HTMLAttributes.kind?.toUpperCase() || "MEDIA"}] ${HTMLAttributes.caption || HTMLAttributes.src || ""}`,
        ];
    },
    addNodeView() {
        return ReactNodeViewRenderer(MediaView);
    },
});

// ============================================================================
// AttestationCheckpoint — checkbox or inline signature gate
// ============================================================================

function AttestationCheckpointView({ node, editor }: NodeViewProps) {
    const kind = (node.attrs.kind ?? "confirm") as "confirm" | "signature";
    const required = node.attrs.required !== false;
    const Icon = kind === "signature" ? PenLine : CheckSquare;
    const isOperator = !editor.isEditable;
    const { value, setValue } = useOperatorResponse(node.attrs.node_id);
    return (
        <NodeViewWrapper className="my-3 not-prose">
            <NodeCard
                icon={<Icon className="h-4 w-4 text-muted-foreground" />}
                label={node.attrs.label || "Attestation"}
                badges={
                    <>
                        <Badge variant="outline" className="text-[10px] capitalize">{kind}</Badge>
                        {required && <Badge variant="secondary" className="text-[10px]">Required</Badge>}
                        {isOperator && value && (
                            <Badge variant="default" className="text-[10px]">Captured ✓</Badge>
                        )}
                    </>
                }
            >
                {kind === "confirm" ? (
                    <label className="flex items-center gap-2 text-sm" contentEditable={false}>
                        <input
                            type="checkbox"
                            disabled={!isOperator}
                            checked={isOperator ? Boolean(value) : false}
                            onChange={(e) => isOperator && setValue(e.target.checked)}
                            className={isOperator ? "" : "cursor-not-allowed"}
                        />
                        <span className={isOperator ? "" : "text-muted-foreground"}>
                            {node.attrs.prompt || "Operator confirms"}
                        </span>
                    </label>
                ) : (
                    <div contentEditable={false}>
                        {isOperator ? (
                            value ? (
                                <div className="rounded border border-green-500/40 bg-green-50/40 dark:bg-green-950/20 p-2 text-xs">
                                    Signed at {new Date(value as string).toLocaleString()}
                                </div>
                            ) : (
                                <button
                                    type="button"
                                    onClick={() => setValue(new Date().toISOString())}
                                    className="w-full rounded border border-dashed py-3 text-xs text-muted-foreground hover:bg-muted"
                                >
                                    Click to sign (placeholder — real `SignatureCanvas` integration deferred)
                                </button>
                            )
                        ) : (
                            <div className="flex h-16 items-center justify-center rounded border border-dashed text-xs text-muted-foreground">
                                Signature pad placeholder
                            </div>
                        )}
                    </div>
                )}
            </NodeCard>
        </NodeViewWrapper>
    );
}

const AttestationCheckpoint = Node.create({
    name: "attestationCheckpoint",
    group: "block",
    atom: true,
    selectable: true,
    draggable: true,
    addAttributes() {
        return {
            node_id: { default: "" },
            label: { default: "" },
            kind: { default: "confirm" },
            prompt: { default: "" },
            required: { default: true },
        };
    },
    parseHTML() {
        return [{ tag: 'div[data-type="attestation-checkpoint"]' }];
    },
    renderHTML({ HTMLAttributes }) {
        return [
            "div",
            mergeAttributes(HTMLAttributes, { "data-type": "attestation-checkpoint" }),
            `[${HTMLAttributes.kind?.toUpperCase() || "CONFIRM"}] ${HTMLAttributes.label || ""}`,
        ];
    },
    addNodeView() {
        return ReactNodeViewRenderer(AttestationCheckpointView);
    },
});

// ============================================================================
// MeasurementInput — active numeric capture (sibling of MeasurementSpec)
// ============================================================================

// Text-input row: local state preserves cursor + raw typing; useEffect resyncs
// when an external write updates the attr (e.g. linked-spec autofill).
function TextAttrRow({
    attrName,
    label,
    initial,
    update,
    monospace = false,
}: {
    attrName: string;
    label: string;
    initial: string;
    update: (partial: AttrPartial) => void;
    monospace?: boolean;
}) {
    const [raw, setRaw] = useState(initial ?? "");
    useEffect(() => {
        setRaw(initial ?? "");
    }, [initial]);
    return (
        <div className="grid grid-cols-3 items-center gap-2">
            <Label className="text-xs">{label}</Label>
            <Input
                value={raw}
                onChange={(e) => {
                    setRaw(e.target.value);
                    update({ [attrName]: e.target.value });
                }}
                className={`col-span-2 h-8 text-sm${monospace ? " font-mono" : ""}`}
            />
        </div>
    );
}

// Decimal-input row: keeps a raw string in local state (preserves "0." mid-typing)
// while debouncing a parsed number into the node attrs.
function DecimalAttrInput({
    attrName,
    label,
    initial,
    update,
}: {
    attrName: string;
    label: string;
    initial: number | null;
    update: (partial: AttrPartial) => void;
}) {
    const [raw, setRaw] = useState(initial != null ? String(initial) : "");
    // Re-sync local state when the attr is externally updated (e.g. picking a
    // linked MeasurementDefinition fills in nominal/upper_tol/lower_tol).
    useEffect(() => {
        setRaw(initial != null ? String(initial) : "");
    }, [initial]);
    return (
        <div className="grid grid-cols-3 items-center gap-2">
            <Label className="text-xs">{label}</Label>
            <Input
                type="text"
                inputMode="decimal"
                value={raw}
                onChange={(e) => {
                    const v = e.target.value;
                    setRaw(v);
                    const parsed = v === "" ? null : Number(v);
                    update({ [attrName]: parsed != null && Number.isFinite(parsed) ? parsed : null });
                }}
                className="col-span-2 h-8 font-mono text-sm"
            />
        </div>
    );
}

function MeasurementInputEditForm({
    node,
    updateAttributes,
}: {
    node: NodeViewProps["node"];
    updateAttributes: NodeViewProps["updateAttributes"];
}) {
    const a = node.attrs as {
        label: string;
        unit: string;
        nominal: number | null;
        upper_tol: number | null;
        lower_tol: number | null;
        required: boolean;
        characteristic_number: string;
        measurement_definition_id: string | null;
    };
    const update = useDebouncedAttrs(updateAttributes, 250);

    const pickDefinition = (id: string) => {
        const def = MOCK_MEASUREMENT_DEFINITIONS.find((d) => d.id === id);
        if (!def) return;
        // Linked-spec picks are atomic — bypass the debounce, write all fields in one transaction.
        updateAttributes({
            measurement_definition_id: def.id,
            label: def.label,
            unit: def.unit,
            nominal: def.nominal,
            upper_tol: def.upper_tol,
            lower_tol: def.lower_tol,
            characteristic_number: def.characteristic_number,
        });
    };

    return (
        <div className="space-y-3">
            <div className="space-y-1">
                <Label className="text-xs">Linked measurement spec</Label>
                <Select
                    value={a.measurement_definition_id ?? ""}
                    onValueChange={(v) => v && pickDefinition(v)}
                >
                    <SelectTrigger className="h-8 text-sm">
                        <SelectValue placeholder="— pick to autofill —" />
                    </SelectTrigger>
                    <SelectContent>
                        {MOCK_MEASUREMENT_DEFINITIONS.map((d) => (
                            <SelectItem key={d.id} value={d.id} className="text-sm">
                                <span className="font-mono text-xs text-muted-foreground mr-2">
                                    {d.characteristic_number}
                                </span>
                                {d.label}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>
                {a.measurement_definition_id && (
                    <button
                        type="button"
                        onClick={() => updateAttributes({ measurement_definition_id: null })}
                        className="text-[10px] text-muted-foreground hover:underline"
                    >
                        Unlink (keep fields)
                    </button>
                )}
            </div>

            <TextAttrRow attrName="label" label="Label" initial={a.label} update={update} />
            <TextAttrRow attrName="characteristic_number" label="Characteristic" initial={a.characteristic_number} update={update} monospace />
            <TextAttrRow attrName="unit" label="Unit" initial={a.unit} update={update} />

            <DecimalAttrInput attrName="nominal" label="Nominal" initial={a.nominal} update={update} />
            <DecimalAttrInput attrName="upper_tol" label="+ Tol" initial={a.upper_tol} update={update} />
            <DecimalAttrInput attrName="lower_tol" label="− Tol" initial={a.lower_tol} update={update} />

            <div className="flex items-center justify-between border-t pt-2">
                <Label htmlFor="meas-required" className="text-xs">Required</Label>
                <Switch
                    id="meas-required"
                    checked={a.required}
                    onCheckedChange={(checked) => updateAttributes({ required: checked })}
                />
            </div>
        </div>
    );
}

function MeasurementInputView({ node, editor, updateAttributes }: NodeViewProps) {
    const { label, unit, nominal, upper_tol, lower_tol, required, characteristic_number } = node.attrs as {
        label: string;
        unit: string;
        nominal: number | null;
        upper_tol: number | null;
        lower_tol: number | null;
        required: boolean;
        characteristic_number: string;
    };
    const isOperator = !editor.isEditable;
    const { value, setValue } = useOperatorResponse(node.attrs.node_id);
    // Store raw string so "0." / "0.00" survives mid-typing; parse to number only
    // for the spec-comparison logic.
    const rawValue = typeof value === "string" ? value : "";
    const parsedValue = rawValue === "" ? null : Number(rawValue);
    const numericValid = parsedValue != null && Number.isFinite(parsedValue);
    const inSpec =
        isOperator && numericValid && nominal != null
            ? parsedValue! >= nominal - (lower_tol ?? 0) && parsedValue! <= nominal + (upper_tol ?? 0)
            : null;

    const card = (
        <NodeCard
            icon={<Ruler className="h-4 w-4 text-muted-foreground" />}
            label={label || "Measurement Input"}
            badges={
                <>
                    {characteristic_number && (
                        <Badge variant="outline" className="font-mono text-[10px]">{characteristic_number}</Badge>
                    )}
                    {required && <Badge variant="secondary" className="text-[10px]">Required</Badge>}
                    {inSpec === true && (
                        <Badge className="bg-green-600 text-[10px] text-white">In spec</Badge>
                    )}
                    {inSpec === false && (
                        <Badge variant="destructive" className="text-[10px]">Out of spec</Badge>
                    )}
                </>
            }
            rightSlot={
                nominal != null
                    ? `${nominal}${upper_tol != null ? ` +${upper_tol}` : ""}${lower_tol != null ? ` −${lower_tol}` : ""}${unit ? ` ${unit}` : ""}`
                    : "no target"
            }
        >
            <div className="flex items-center gap-2" contentEditable={false}>
                <input
                    type="text"
                    inputMode="decimal"
                    disabled={!isOperator}
                    placeholder="—"
                    value={rawValue}
                    onChange={(e) => isOperator && setValue(e.target.value)}
                    className="w-32 rounded border bg-background px-2 py-1 text-sm font-mono"
                />
                {unit && <span className="text-sm text-muted-foreground">{unit}</span>}
            </div>
        </NodeCard>
    );

    return (
        <NodeViewWrapper className="my-3 not-prose">
            {isOperator ? (
                card
            ) : (
                <Popover>
                    <div className="group relative">
                        <HoverGearTrigger />
                        {card}
                    </div>
                    <PopoverContent
                        align="end"
                        className="w-80"
                        // Prevent clicks inside the popover from being interpreted as
                        // ProseMirror selection events on the underlying editor.
                        onOpenAutoFocus={(e) => e.preventDefault()}
                    >
                        <MeasurementInputEditForm node={node} updateAttributes={updateAttributes} />
                    </PopoverContent>
                </Popover>
            )}
        </NodeViewWrapper>
    );
}

const MeasurementInput = Node.create({
    name: "measurementInput",
    group: "block",
    atom: true,
    selectable: true,
    draggable: true,
    addAttributes() {
        return {
            node_id: { default: "" },
            label: { default: "" },
            unit: { default: "" },
            nominal: { default: null },
            upper_tol: { default: null },
            lower_tol: { default: null },
            required: { default: true },
            characteristic_number: { default: "" },
            measurement_definition_id: { default: null },
        };
    },
    parseHTML() {
        return [{ tag: 'div[data-type="measurement-input"]' }];
    },
    renderHTML({ HTMLAttributes }) {
        return [
            "div",
            mergeAttributes(HTMLAttributes, { "data-type": "measurement-input" }),
            `${HTMLAttributes.label || "Measurement"}: ___ ${HTMLAttributes.unit || ""}`,
        ];
    },
    addNodeView() {
        return ReactNodeViewRenderer(MeasurementInputView);
    },
});

// ============================================================================
// TextInput — short / long text capture
// ============================================================================

function TextInputView({ node, editor }: NodeViewProps) {
    const kind = (node.attrs.kind ?? "short") as "short" | "long";
    const required = node.attrs.required === true;
    const isOperator = !editor.isEditable;
    const { value, setValue } = useOperatorResponse(node.attrs.node_id);
    const v = typeof value === "string" ? value : "";
    return (
        <NodeViewWrapper className="my-3 not-prose">
            <NodeCard
                icon={<Type className="h-4 w-4 text-muted-foreground" />}
                label={node.attrs.label || "Text input"}
                badges={
                    <>
                        <Badge variant="outline" className="text-[10px] capitalize">{kind}</Badge>
                        {required && <Badge variant="secondary" className="text-[10px]">Required</Badge>}
                        {isOperator && v && (
                            <Badge variant="default" className="text-[10px]">Captured ✓</Badge>
                        )}
                    </>
                }
            >
                <div contentEditable={false}>
                    {kind === "short" ? (
                        <input
                            type="text"
                            disabled={!isOperator}
                            placeholder={node.attrs.placeholder || "—"}
                            value={v}
                            onChange={(e) => isOperator && setValue(e.target.value)}
                            className="w-full rounded border bg-background px-2 py-1 text-sm"
                        />
                    ) : (
                        <textarea
                            disabled={!isOperator}
                            rows={3}
                            placeholder={node.attrs.placeholder || "—"}
                            value={v}
                            onChange={(e) => isOperator && setValue(e.target.value)}
                            className="w-full rounded border bg-background px-2 py-1 text-sm"
                        />
                    )}
                </div>
            </NodeCard>
        </NodeViewWrapper>
    );
}

const TextInput = Node.create({
    name: "textInput",
    group: "block",
    atom: true,
    selectable: true,
    draggable: true,
    addAttributes() {
        return {
            node_id: { default: "" },
            label: { default: "" },
            kind: { default: "short" },
            placeholder: { default: "" },
            required: { default: false },
        };
    },
    parseHTML() {
        return [{ tag: 'div[data-type="text-input"]' }];
    },
    renderHTML({ HTMLAttributes }) {
        return [
            "div",
            mergeAttributes(HTMLAttributes, { "data-type": "text-input" }),
            `${HTMLAttributes.label || "Text"}: ___`,
        ];
    },
    addNodeView() {
        return ReactNodeViewRenderer(TextInputView);
    },
});

// ============================================================================
// ChoiceInput — radio / select
// ============================================================================

function ChoiceInputView({ node, editor }: NodeViewProps) {
    const kind = (node.attrs.kind ?? "radio") as "radio" | "select";
    const options: string[] = Array.isArray(node.attrs.options) ? node.attrs.options : [];
    const required = node.attrs.required === true;
    const isOperator = !editor.isEditable;
    const { value, setValue } = useOperatorResponse(node.attrs.node_id);
    const v = typeof value === "string" ? value : "";
    // unique radio group name per node so multiple ChoiceInputs on the page
    // don't collide
    const groupName = useMemo(
        () => `choice-${node.attrs.node_id || Math.random().toString(36).slice(2)}`,
        [node.attrs.node_id],
    );
    return (
        <NodeViewWrapper className="my-3 not-prose">
            <NodeCard
                icon={<ListChecks className="h-4 w-4 text-muted-foreground" />}
                label={node.attrs.label || "Choice"}
                badges={
                    <>
                        <Badge variant="outline" className="text-[10px] capitalize">{kind}</Badge>
                        {required && <Badge variant="secondary" className="text-[10px]">Required</Badge>}
                        {isOperator && v && (
                            <Badge variant="default" className="text-[10px]">Captured ✓</Badge>
                        )}
                    </>
                }
            >
                <div contentEditable={false}>
                    {kind === "radio" ? (
                        <div className="space-y-1">
                            {options.map((opt) => (
                                <label
                                    key={opt}
                                    className={`flex items-center gap-2 text-sm ${isOperator ? "" : "text-muted-foreground"}`}
                                >
                                    <input
                                        type="radio"
                                        name={groupName}
                                        disabled={!isOperator}
                                        checked={isOperator ? v === opt : false}
                                        onChange={() => isOperator && setValue(opt)}
                                    />
                                    {opt}
                                </label>
                            ))}
                        </div>
                    ) : (
                        <select
                            disabled={!isOperator}
                            value={v}
                            onChange={(e) => isOperator && setValue(e.target.value)}
                            className="rounded border bg-background px-2 py-1 text-sm"
                        >
                            <option value="">— select —</option>
                            {options.map((opt) => (
                                <option key={opt} value={opt}>
                                    {opt}
                                </option>
                            ))}
                        </select>
                    )}
                </div>
            </NodeCard>
        </NodeViewWrapper>
    );
}

const ChoiceInput = Node.create({
    name: "choiceInput",
    group: "block",
    atom: true,
    selectable: true,
    draggable: true,
    addAttributes() {
        return {
            node_id: { default: "" },
            label: { default: "" },
            kind: { default: "radio" },
            options: { default: [] },
            required: { default: false },
        };
    },
    parseHTML() {
        return [{ tag: 'div[data-type="choice-input"]' }];
    },
    renderHTML({ HTMLAttributes }) {
        const options = Array.isArray(HTMLAttributes.options) ? HTMLAttributes.options.join(" / ") : "";
        return [
            "div",
            mergeAttributes(HTMLAttributes, { "data-type": "choice-input" }),
            `${HTMLAttributes.label || "Choice"}: ${options}`,
        ];
    },
    addNodeView() {
        return ReactNodeViewRenderer(ChoiceInputView);
    },
});

// ============================================================================
// PhotoCapture / ScanInput / FileCapture
// ============================================================================

function FileLikeCaptureView({
    node,
    editor,
    icon,
    typeLabel,
    accept,
    mockPlaceholder,
}: NodeViewProps & {
    icon: React.ReactNode;
    typeLabel: string;
    accept: string;
    mockPlaceholder: string;
}) {
    const isOperator = !editor.isEditable;
    const { value, setValue } = useOperatorResponse(node.attrs.node_id);
    const fileName = typeof value === "string" ? value : "";
    return (
        <NodeViewWrapper className="my-3 not-prose">
            <NodeCard
                icon={icon}
                label={node.attrs.label || `${typeLabel} capture`}
                badges={
                    <>
                        <Badge variant="outline" className="text-[10px]">{typeLabel}</Badge>
                        {node.attrs.required && <Badge variant="secondary" className="text-[10px]">Required</Badge>}
                        {isOperator && fileName && (
                            <Badge variant="default" className="text-[10px]">Captured ✓</Badge>
                        )}
                    </>
                }
            >
                <div contentEditable={false}>
                    {isOperator ? (
                        fileName ? (
                            <div className="flex items-center gap-2 rounded border border-green-500/40 bg-green-50/40 dark:bg-green-950/20 p-2 text-xs">
                                <span className="font-mono">{fileName}</span>
                                <button
                                    type="button"
                                    onClick={() => setValue("")}
                                    className="ml-auto text-muted-foreground hover:underline"
                                >
                                    Clear
                                </button>
                            </div>
                        ) : (
                            <label className="block cursor-pointer rounded border border-dashed py-3 text-center text-xs text-muted-foreground hover:bg-muted">
                                <input
                                    type="file"
                                    accept={accept}
                                    className="hidden"
                                    onChange={(e) => {
                                        const f = e.target.files?.[0];
                                        if (f) setValue(f.name);
                                    }}
                                />
                                Tap to {typeLabel.toLowerCase() === "image" ? "capture or upload" : "upload"}
                            </label>
                        )
                    ) : (
                        <div className="flex h-16 items-center justify-center rounded border border-dashed text-xs text-muted-foreground">
                            {mockPlaceholder}
                        </div>
                    )}
                </div>
            </NodeCard>
        </NodeViewWrapper>
    );
}

function PhotoCaptureView(props: NodeViewProps) {
    return (
        <FileLikeCaptureView
            {...props}
            icon={<Camera className="h-4 w-4 text-muted-foreground" />}
            typeLabel="Image"
            accept="image/*"
            mockPlaceholder="Operator taps to capture or upload"
        />
    );
}

const PhotoCapture = Node.create({
    name: "photoCapture",
    group: "block",
    atom: true,
    selectable: true,
    draggable: true,
    addAttributes() {
        return { node_id: { default: "" }, label: { default: "" }, required: { default: false } };
    },
    parseHTML() {
        return [{ tag: 'div[data-type="photo-capture"]' }];
    },
    renderHTML({ HTMLAttributes }) {
        return [
            "div",
            mergeAttributes(HTMLAttributes, { "data-type": "photo-capture" }),
            `[PHOTO] ${HTMLAttributes.label || ""}`,
        ];
    },
    addNodeView() {
        return ReactNodeViewRenderer(PhotoCaptureView);
    },
});

function ScanInputView({ node, editor }: NodeViewProps) {
    const isOperator = !editor.isEditable;
    const { value, setValue } = useOperatorResponse(node.attrs.node_id);
    const v = typeof value === "string" ? value : "";
    return (
        <NodeViewWrapper className="my-3 not-prose">
            <NodeCard
                icon={<ScanLine className="h-4 w-4 text-muted-foreground" />}
                label={node.attrs.label || "Scan"}
                badges={
                    <>
                        <Badge variant="outline" className="text-[10px]">Barcode / QR</Badge>
                        {node.attrs.required && <Badge variant="secondary" className="text-[10px]">Required</Badge>}
                        {isOperator && v && (
                            <Badge variant="default" className="text-[10px]">Captured ✓</Badge>
                        )}
                    </>
                }
            >
                <div contentEditable={false}>
                    <input
                        type="text"
                        disabled={!isOperator}
                        placeholder="Scan into field…"
                        value={v}
                        onChange={(e) => isOperator && setValue(e.target.value)}
                        className="w-full rounded border bg-background px-2 py-1 font-mono text-sm"
                    />
                </div>
            </NodeCard>
        </NodeViewWrapper>
    );
}

const ScanInput = Node.create({
    name: "scanInput",
    group: "block",
    atom: true,
    selectable: true,
    draggable: true,
    addAttributes() {
        return { node_id: { default: "" }, label: { default: "" }, required: { default: false } };
    },
    parseHTML() {
        return [{ tag: 'div[data-type="scan-input"]' }];
    },
    renderHTML({ HTMLAttributes }) {
        return [
            "div",
            mergeAttributes(HTMLAttributes, { "data-type": "scan-input" }),
            `[SCAN] ${HTMLAttributes.label || ""}`,
        ];
    },
    addNodeView() {
        return ReactNodeViewRenderer(ScanInputView);
    },
});

function FileCaptureView(props: NodeViewProps) {
    return (
        <FileLikeCaptureView
            {...props}
            icon={<Paperclip className="h-4 w-4 text-muted-foreground" />}
            typeLabel="Any file"
            accept="*"
            mockPlaceholder="Operator uploads CAD / PDF / spreadsheet"
        />
    );
}

const FileCapture = Node.create({
    name: "fileCapture",
    group: "block",
    atom: true,
    selectable: true,
    draggable: true,
    addAttributes() {
        return { node_id: { default: "" }, label: { default: "" }, required: { default: false } };
    },
    parseHTML() {
        return [{ tag: 'div[data-type="file-capture"]' }];
    },
    renderHTML({ HTMLAttributes }) {
        return [
            "div",
            mergeAttributes(HTMLAttributes, { "data-type": "file-capture" }),
            `[FILE] ${HTMLAttributes.label || ""}`,
        ];
    },
    addNodeView() {
        return ReactNodeViewRenderer(FileCaptureView);
    },
});

// ============================================================================
// Timer — hybrid display/capture node for "wait N seconds" / "time how long"
// ============================================================================

type TimerResponse = {
    started_at: string;
    completed_at: string;
    elapsed_seconds: number;
    direction: "countdown" | "stopwatch";
};

function formatMMSS(totalSeconds: number) {
    const s = Math.max(0, Math.floor(totalSeconds));
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}

function TimerView({ node, editor }: NodeViewProps) {
    const duration = Number(node.attrs.duration_seconds) || 0;
    const direction = (node.attrs.direction ?? "countdown") as "countdown" | "stopwatch";
    const required = node.attrs.required === true;
    const isOperator = !editor.isEditable;
    const { value, setValue } = useOperatorResponse(node.attrs.node_id);

    // Local running state — tracks the active timer for THIS render
    const [startMs, setStartMs] = useState<number | null>(null);
    const [tick, setTick] = useState(0);

    useEffect(() => {
        if (startMs == null) return;
        const id = window.setInterval(() => setTick((t) => t + 1), 200);
        return () => window.clearInterval(id);
    }, [startMs]);

    const captured = value as TimerResponse | undefined;
    const elapsed = startMs != null ? (Date.now() - startMs) / 1000 : 0;
    const remaining = Math.max(0, duration - elapsed);
    // Auto-complete the countdown when it hits zero
    useEffect(() => {
        if (
            startMs != null &&
            direction === "countdown" &&
            duration > 0 &&
            elapsed >= duration
        ) {
            const completedAt = new Date().toISOString();
            const startedAt = new Date(startMs).toISOString();
            setValue({
                started_at: startedAt,
                completed_at: completedAt,
                elapsed_seconds: Math.round(elapsed * 10) / 10,
                direction,
            } satisfies TimerResponse);
            setStartMs(null);
        }
        // tick is included so we re-evaluate as the timer advances
    }, [tick, startMs, direction, duration, elapsed, setValue]);

    const handleStart = () => setStartMs(Date.now());
    const handleStop = () => {
        if (startMs == null) return;
        const completedAt = new Date().toISOString();
        const startedAt = new Date(startMs).toISOString();
        setValue({
            started_at: startedAt,
            completed_at: completedAt,
            elapsed_seconds: Math.round(elapsed * 10) / 10,
            direction,
        } satisfies TimerResponse);
        setStartMs(null);
    };
    const handleReset = () => {
        setValue(undefined);
        setStartMs(null);
    };

    const running = startMs != null;
    const display = running
        ? formatMMSS(direction === "countdown" ? remaining : elapsed)
        : captured
            ? formatMMSS(captured.elapsed_seconds)
            : formatMMSS(duration);

    return (
        <NodeViewWrapper className="my-3 not-prose">
            <NodeCard
                icon={<TimerIcon className="h-4 w-4 text-muted-foreground" />}
                label={node.attrs.label || (direction === "countdown" ? "Wait timer" : "Stopwatch")}
                badges={
                    <>
                        <Badge variant="outline" className="text-[10px] capitalize">{direction}</Badge>
                        {direction === "countdown" && duration > 0 && (
                            <Badge variant="outline" className="font-mono text-[10px]">
                                {formatMMSS(duration)}
                            </Badge>
                        )}
                        {required && <Badge variant="secondary" className="text-[10px]">Required</Badge>}
                        {isOperator && captured && (
                            <Badge variant="default" className="text-[10px]">Captured ✓</Badge>
                        )}
                    </>
                }
            >
                <div className="flex items-center gap-3" contentEditable={false}>
                    <span className="font-mono text-2xl tabular-nums">{display}</span>
                    {isOperator ? (
                        captured ? (
                            <button
                                type="button"
                                onClick={handleReset}
                                className="rounded border px-3 py-1 text-xs text-muted-foreground hover:bg-muted"
                            >
                                Reset
                            </button>
                        ) : running ? (
                            direction === "stopwatch" ? (
                                <button
                                    type="button"
                                    onClick={handleStop}
                                    className="flex items-center gap-1 rounded bg-destructive px-3 py-1 text-xs text-destructive-foreground"
                                >
                                    <Square className="h-3 w-3" /> Stop
                                </button>
                            ) : (
                                <span className="text-xs text-muted-foreground">
                                    Counting down — completes automatically
                                </span>
                            )
                        ) : (
                            <button
                                type="button"
                                onClick={handleStart}
                                className="flex items-center gap-1 rounded bg-primary px-3 py-1 text-xs text-primary-foreground"
                            >
                                <Play className="h-3 w-3" /> Start
                            </button>
                        )
                    ) : (
                        <span className="text-xs text-muted-foreground">
                            (Start button shown to operator)
                        </span>
                    )}
                </div>
            </NodeCard>
        </NodeViewWrapper>
    );
}

const Timer = Node.create({
    name: "timer",
    group: "block",
    atom: true,
    selectable: true,
    draggable: true,
    addAttributes() {
        return {
            node_id: { default: "" },
            label: { default: "" },
            duration_seconds: { default: 30 },
            direction: { default: "countdown" }, // 'countdown' | 'stopwatch'
            required: { default: false },
        };
    },
    parseHTML() {
        return [{ tag: 'div[data-type="timer"]' }];
    },
    renderHTML({ HTMLAttributes }) {
        return [
            "div",
            mergeAttributes(HTMLAttributes, { "data-type": "timer" }),
            `[${HTMLAttributes.direction?.toUpperCase() || "TIMER"}] ${HTMLAttributes.label || ""} (${HTMLAttributes.duration_seconds || 0}s)`,
        ];
    },
    addNodeView() {
        return ReactNodeViewRenderer(TimerView);
    },
});

// ============================================================================
// ComputedValue — declared variables + formula, evaluated live for the operator
// ============================================================================
//
// Engineer authoring (attrs):
//   - variables: [{ name, label, unit }] — N declared input variables
//   - formula: string — expression referencing the variables by name
//                       (`2 * sqrt(X^2 + Y^2)` for true position, etc.)
//   - result_label, result_unit
//   - nominal, upper_tol, lower_tol — same spec language as MeasurementInput
//     (in-spec iff: nominal - (lower_tol ?? 0) <= result <= nominal + (upper_tol ?? 0))
//     For "True Position style" (positive-only, max bound): nominal=0, upper_tol=N, lower_tol=0
//     For "symmetric bilateral" (1.247 ± 0.002): nominal=1.247, upper_tol=0.002, lower_tol=0.002
//     For "unilateral upper" (≤ X): nominal=0, upper_tol=X, lower_tol=null
//   - display_precision: number — decimals to show for the result (default 4)
//
// Operator interaction:
//   - Sees one numeric input per declared variable
//   - As they fill values, the formula evaluates live
//   - In-spec / out-of-spec badge per the unified spec model
//   - Captured response: { inputs: {X, Y, ...}, result, in_spec }

type ComputedVariable = { name: string; label: string; unit: string };
// Inputs are stored as raw strings (what the operator typed) so trailing
// zeros / decimal points survive across re-renders. Numeric conversion
// happens only at evaluation time.
type ComputedResponse = {
    inputs: Record<string, string>;
    result: number | null;
    in_spec: boolean | null;
};

function ComputedValueView({ node, editor }: NodeViewProps) {
    const isOperator = !editor.isEditable;
    const { value, setValue } = useOperatorResponse(node.attrs.node_id);

    const variables = (Array.isArray(node.attrs.variables) ? node.attrs.variables : []) as ComputedVariable[];
    const formula = (node.attrs.formula ?? "") as string;
    const nominal = node.attrs.nominal as number | null;
    const upperTol = node.attrs.upper_tol as number | null;
    const lowerTol = node.attrs.lower_tol as number | null;
    const resultLabel = (node.attrs.result_label || "Result") as string;
    const resultUnit = (node.attrs.result_unit || "") as string;
    const required = node.attrs.required === true;
    const displayPrecision = Number.isFinite(node.attrs.display_precision)
        ? Math.max(0, Math.min(10, Number(node.attrs.display_precision)))
        : 4;
    const hasSpec = nominal != null && (upperTol != null || lowerTol != null);

    const captured = (value as ComputedResponse | undefined) ?? null;
    const inputs = captured?.inputs ?? {};
    const result = captured?.result ?? null;
    const inSpec = captured?.in_spec ?? null;

    // Parse the formula once per render (cheap, expr-eval handles it fast)
    const parsedFormula = useMemo(() => {
        try {
            return { ok: true as const, expr: FORMULA_PARSER.parse(formula) };
        } catch (e) {
            return { ok: false as const, error: e instanceof Error ? e.message : String(e) };
        }
    }, [formula]);

    const setInput = (name: string, rawValue: string) => {
        if (!isOperator) return;
        const newInputs = { ...inputs };
        if (rawValue === "") {
            delete newInputs[name];
        } else {
            newInputs[name] = rawValue; // keep the raw string so "0." / "0.0" survives
        }

        // Build numeric inputs for evaluation. Missing or unparseable values
        // disqualify the calc (result/in_spec stay null).
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
                // runtime error (div by zero, sqrt of negative, etc.) — leave nulls
            }
        }

        setValue({ inputs: newInputs, result: nextResult, in_spec: nextInSpec } satisfies ComputedResponse);
    };

    const allFilled =
        variables.length > 0 &&
        variables.every((v) => v.name in inputs && inputs[v.name] !== "");

    return (
        <NodeViewWrapper className="my-3 not-prose">
            <NodeCard
                icon={<Calculator className="h-4 w-4 text-muted-foreground" />}
                label={node.attrs.label || "Computed value"}
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
                        ? `${nominal}${upperTol != null ? ` +${upperTol}` : ""}${lowerTol != null ? ` −${lowerTol}` : ""}${resultUnit ? " " + resultUnit : ""}`
                        : null
                }
            >
                <div contentEditable={false} className="space-y-2">
                    {/* Formula display — read-only in both modes for spike. Authoring popover would edit this. */}
                    <div className="rounded bg-muted/50 px-2 py-1 font-mono text-xs">
                        {resultLabel} = <span className="font-semibold">{formula || "(no formula)"}</span>
                        {!parsedFormula.ok && (
                            <span className="ml-2 text-destructive">
                                · syntax error: {parsedFormula.error}
                            </span>
                        )}
                    </div>

                    {/* Variable inputs */}
                    <div className="space-y-1.5">
                        {variables.map((v) => (
                            <div key={v.name} className="flex items-center gap-2 text-sm">
                                <span className="w-40 text-xs text-muted-foreground">
                                    {v.label || v.name}{" "}
                                    <span className="font-mono opacity-70">({v.name})</span>
                                </span>
                                <input
                                    type="text"
                                    inputMode="decimal"
                                    disabled={!isOperator}
                                    value={inputs[v.name] ?? ""}
                                    onChange={(e) => setInput(v.name, e.target.value)}
                                    placeholder="—"
                                    className="w-24 rounded border bg-background px-2 py-1 font-mono text-sm"
                                />
                                {v.unit && (
                                    <span className="text-xs text-muted-foreground">{v.unit}</span>
                                )}
                            </div>
                        ))}
                    </div>

                    {/* Result */}
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
                                    return `spec: [${fmt(lo)}, ${fmt(hi)}]${resultUnit ? " " + resultUnit : ""}`;
                                })()}
                            </span>
                        )}
                    </div>
                </div>
            </NodeCard>
        </NodeViewWrapper>
    );
}

const ComputedValue = Node.create({
    name: "computedValue",
    group: "block",
    atom: true,
    selectable: true,
    draggable: true,
    addAttributes() {
        return {
            node_id: { default: "" },
            label: { default: "" },
            variables: { default: [] }, // ComputedVariable[]
            formula: { default: "" },
            result_label: { default: "Result" },
            result_unit: { default: "" },
            // Unified spec language (matches MeasurementInput):
            // in-spec iff: nominal - (lower_tol ?? Infinity) <= result <= nominal + (upper_tol ?? Infinity)
            // Null upper/lower means "no bound on that side"; null nominal disables spec check entirely.
            nominal: { default: null },
            upper_tol: { default: null },
            lower_tol: { default: null },
            // Result display precision (decimals). Engineer sets per node.
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
        return ReactNodeViewRenderer(ComputedValueView);
    },
});

// Sample-data snippets used by both the document and the toolbar inserts.
const SAMPLE_CALLOUT_CAUTION = {
    type: "callout",
    attrs: { variant: "caution" },
    content: [
        {
            type: "paragraph",
            content: [
                {
                    type: "text",
                    text: "Bar stock must be clamped firmly. Loose stock can throw at high spindle speed.",
                },
            ],
        },
    ],
};
const SAMPLE_CALLOUT_NOTE = {
    type: "callout",
    attrs: { variant: "note" },
    content: [
        {
            type: "paragraph",
            content: [{ type: "text", text: "The setup sheet lives in the binder above the machine." }],
        },
    ],
};
const SAMPLE_MEDIA = {
    type: "media",
    attrs: { kind: "image", src: "", caption: "Setup sheet — P/N 11782-3" },
};
// Hardcoded node_ids for the seed document so the operator response store keys
// are stable across renders. Toolbar inserts use `withFreshNodeId()` to mint a
// new id each time.
const SAMPLE_ATTESTATION_CONFIRM = {
    type: "attestationCheckpoint",
    attrs: { node_id: "seed-att-confirm-1", label: "Verify material cert", kind: "confirm", prompt: "I have checked the cert against the lot stamp.", required: true },
};
const SAMPLE_ATTESTATION_SIGNATURE = {
    type: "attestationCheckpoint",
    attrs: { node_id: "seed-att-sig-1", label: "Operator sign-off", kind: "signature", required: true },
};
const SAMPLE_MEASUREMENT_INPUT = {
    type: "measurementInput",
    attrs: {
        node_id: "seed-meas-input-1",
        label: "OD measurement (record actual)",
        unit: "in",
        nominal: 1.247,
        upper_tol: 0.002,
        lower_tol: 0.002,
        required: true,
        characteristic_number: "B12",
    },
};
const SAMPLE_TEXT_INPUT_SHORT = {
    type: "textInput",
    attrs: { node_id: "seed-text-short-1", label: "Material lot #", kind: "short", placeholder: "e.g. LOT-2026-04421", required: true },
};
const SAMPLE_TEXT_INPUT_LONG = {
    type: "textInput",
    attrs: { node_id: "seed-text-long-1", label: "Setup notes", kind: "long", placeholder: "Anything unusual?", required: false },
};
const SAMPLE_CHOICE_RADIO = {
    type: "choiceInput",
    attrs: {
        node_id: "seed-choice-radio-1",
        label: "Bar stock condition",
        kind: "radio",
        options: ["Clean", "Light surface scale", "Heavy scale — requires extra pass"],
        required: true,
    },
};
const SAMPLE_CHOICE_SELECT = {
    type: "choiceInput",
    attrs: {
        node_id: "seed-choice-select-1",
        label: "Cutting tool",
        kind: "select",
        options: ["CCMT-32.51 (general)", "VBMT-110304 (finish)", "DCMT-070204 (light)"],
        required: false,
    },
};
const SAMPLE_PHOTO = {
    type: "photoCapture",
    attrs: { node_id: "seed-photo-1", label: "Photograph the setup sheet position", required: false },
};
const SAMPLE_SCAN = {
    type: "scanInput",
    attrs: { node_id: "seed-scan-1", label: "Scan tool barcode", required: true },
};
const SAMPLE_FILE = {
    type: "fileCapture",
    attrs: { node_id: "seed-file-1", label: "Attach G-code file", required: false },
};
const SAMPLE_TIMER_COUNTDOWN = {
    type: "timer",
    attrs: {
        node_id: "seed-timer-countdown-1",
        label: "Wait for coolant to stabilize",
        duration_seconds: 30,
        direction: "countdown",
        required: true,
    },
};
const SAMPLE_TIMER_STOPWATCH = {
    type: "timer",
    attrs: {
        node_id: "seed-timer-stopwatch-1",
        label: "Time the dry-run cycle",
        duration_seconds: 0,
        direction: "stopwatch",
        required: false,
    },
};
const SAMPLE_COMPUTED_TRUE_POSITION = {
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
        // True Position spec: result is always ≥ 0, max allowed is 0.005
        // nominal=0, upper_tol=0.005, lower_tol=0 → in-spec iff 0 ≤ result ≤ 0.005
        nominal: 0,
        upper_tol: 0.005,
        lower_tol: 0,
        display_precision: 5,
        required: true,
    },
};

// Editor + preview share typography via @tailwindcss/typography's `prose` class.
const PROSE_CLASSES = "prose prose-sm max-w-none dark:prose-invert";

function ToolbarButton({
    active,
    onClick,
    icon,
    label,
}: {
    active?: boolean;
    onClick: () => void;
    icon: React.ReactNode;
    label: string;
}) {
    return (
        <Button
            size="sm"
            variant={active ? "secondary" : "ghost"}
            onClick={onClick}
            aria-label={label}
            title={label}
            className="h-8 w-8 p-0"
        >
            {icon}
        </Button>
    );
}

function ToolbarDivider() {
    return <div className="mx-1 h-5 w-px bg-border" />;
}

function Toolbar({ editor }: { editor: Editor | null }) {
    if (!editor) return null;

    return (
        <div className="flex flex-wrap items-center gap-0.5 border-b bg-background px-2 py-1.5">
            <ToolbarButton
                active={editor.isActive("bold")}
                onClick={() => editor.chain().focus().toggleBold().run()}
                icon={<Bold className="h-4 w-4" />}
                label="Bold"
            />
            <ToolbarButton
                active={editor.isActive("italic")}
                onClick={() => editor.chain().focus().toggleItalic().run()}
                icon={<Italic className="h-4 w-4" />}
                label="Italic"
            />
            <ToolbarButton
                active={editor.isActive("strike")}
                onClick={() => editor.chain().focus().toggleStrike().run()}
                icon={<Strikethrough className="h-4 w-4" />}
                label="Strikethrough"
            />
            <ToolbarButton
                active={editor.isActive("code")}
                onClick={() => editor.chain().focus().toggleCode().run()}
                icon={<Code className="h-4 w-4" />}
                label="Inline code"
            />
            <ToolbarDivider />
            <ToolbarButton
                active={editor.isActive("heading", { level: 1 })}
                onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
                icon={<Heading1 className="h-4 w-4" />}
                label="Heading 1"
            />
            <ToolbarButton
                active={editor.isActive("heading", { level: 2 })}
                onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
                icon={<Heading2 className="h-4 w-4" />}
                label="Heading 2"
            />
            <ToolbarDivider />
            <ToolbarButton
                active={editor.isActive("bulletList")}
                onClick={() => editor.chain().focus().toggleBulletList().run()}
                icon={<List className="h-4 w-4" />}
                label="Bullet list"
            />
            <ToolbarButton
                active={editor.isActive("orderedList")}
                onClick={() => editor.chain().focus().toggleOrderedList().run()}
                icon={<ListOrdered className="h-4 w-4" />}
                label="Ordered list"
            />
            <ToolbarButton
                active={editor.isActive("blockquote")}
                onClick={() => editor.chain().focus().toggleBlockquote().run()}
                icon={<Quote className="h-4 w-4" />}
                label="Blockquote"
            />
            <ToolbarButton
                onClick={() => editor.chain().focus().setHorizontalRule().run()}
                icon={<Minus className="h-4 w-4" />}
                label="Horizontal rule"
            />
            <ToolbarDivider />
            <ToolbarButton
                onClick={() => editor.chain().focus().undo().run()}
                icon={<Undo className="h-4 w-4" />}
                label="Undo"
            />
            <ToolbarButton
                onClick={() => editor.chain().focus().redo().run()}
                icon={<Redo className="h-4 w-4" />}
                label="Redo"
            />
            <ToolbarDivider />
            {/* DWI custom node inserts — each uses the sample data as the default attrs */}
            <ToolbarButton
                onClick={() => editor.chain().focus().insertContent(SAMPLE_CALLOUT_CAUTION).run()}
                icon={<AlertTriangle className="h-4 w-4" />}
                label="Insert callout"
            />
            <ToolbarButton
                onClick={() => editor.chain().focus().insertContent(SAMPLE_MEDIA).run()}
                icon={<ImageIcon className="h-4 w-4" />}
                label="Insert media"
            />
            <ToolbarButton
                onClick={() => editor.chain().focus().insertContent(withFreshNodeId(SAMPLE_MEASUREMENT_SPEC)).run()}
                icon={<Gauge className="h-4 w-4" />}
                label="Insert measurement spec"
            />
            <ToolbarButton
                onClick={() => editor.chain().focus().insertContent(withFreshNodeId(SAMPLE_MEASUREMENT_INPUT)).run()}
                icon={<Ruler className="h-4 w-4" />}
                label="Insert measurement input"
            />
            <ToolbarButton
                onClick={() => editor.chain().focus().insertContent(withFreshNodeId(SAMPLE_ATTESTATION_CONFIRM)).run()}
                icon={<CheckSquare className="h-4 w-4" />}
                label="Insert attestation"
            />
            <ToolbarButton
                onClick={() => editor.chain().focus().insertContent(withFreshNodeId(SAMPLE_ATTESTATION_SIGNATURE)).run()}
                icon={<PenLine className="h-4 w-4" />}
                label="Insert signature gate"
            />
            <ToolbarButton
                onClick={() => editor.chain().focus().insertContent(withFreshNodeId(SAMPLE_TEXT_INPUT_SHORT)).run()}
                icon={<Type className="h-4 w-4" />}
                label="Insert text input"
            />
            <ToolbarButton
                onClick={() => editor.chain().focus().insertContent(withFreshNodeId(SAMPLE_CHOICE_RADIO)).run()}
                icon={<ListChecks className="h-4 w-4" />}
                label="Insert choice input"
            />
            <ToolbarButton
                onClick={() => editor.chain().focus().insertContent(withFreshNodeId(SAMPLE_PHOTO)).run()}
                icon={<Camera className="h-4 w-4" />}
                label="Insert photo capture"
            />
            <ToolbarButton
                onClick={() => editor.chain().focus().insertContent(withFreshNodeId(SAMPLE_SCAN)).run()}
                icon={<ScanLine className="h-4 w-4" />}
                label="Insert scan input"
            />
            <ToolbarButton
                onClick={() => editor.chain().focus().insertContent(withFreshNodeId(SAMPLE_FILE)).run()}
                icon={<Paperclip className="h-4 w-4" />}
                label="Insert file capture"
            />
            <ToolbarButton
                onClick={() => editor.chain().focus().insertContent(withFreshNodeId(SAMPLE_TIMER_COUNTDOWN)).run()}
                icon={<TimerIcon className="h-4 w-4" />}
                label="Insert timer (countdown)"
            />
            <ToolbarButton
                onClick={() => editor.chain().focus().insertContent(withFreshNodeId(SAMPLE_COMPUTED_TRUE_POSITION)).run()}
                icon={<Calculator className="h-4 w-4" />}
                label="Insert computed value"
            />
        </div>
    );
}

function PaneHeader({
    icon,
    title,
    subtitle,
}: {
    icon: React.ReactNode;
    title: string;
    subtitle: string;
}) {
    return (
        <div className="flex items-baseline gap-2 border-b bg-muted/40 px-4 py-2">
            <span className="flex items-center gap-1.5 text-sm font-medium">
                {icon}
                {title}
            </span>
            <span className="text-xs text-muted-foreground">{subtitle}</span>
        </div>
    );
}

// Shared extension list — used by both the engineer (editable) and operator
// (editable: false) editors so both render the same custom nodes.
const DWI_EXTENSIONS = [
    StarterKit,
    MeasurementSpec,
    Callout,
    Media,
    AttestationCheckpoint,
    MeasurementInput,
    TextInput,
    ChoiceInput,
    PhotoCapture,
    ScanInput,
    FileCapture,
    Timer,
    ComputedValue,
];

// ============================================================================
// Substep page model — multiple substeps in an accordion list
// ============================================================================

type SubstepData = {
    id: string;
    order: number;
    title: string;
    body: object; // TipTap doc JSON
    required: boolean;
    requires_signature: boolean;
    is_optional: boolean;
};

const SEED_SUBSTEPS: SubstepData[] = [
    {
        id: "ss-1",
        order: 1,
        title: "Setup OD offsets",
        required: true,
        requires_signature: false,
        is_optional: false,
        body: {
            type: "doc",
            content: [
                {
                    type: "paragraph",
                    content: [
                        { type: "text", text: "Adjust the X and Z offsets per the " },
                        { type: "text", text: "setup sheet", marks: [{ type: "bold" }] },
                        { type: "text", text: " before running the first piece." },
                    ],
                },
                SAMPLE_CALLOUT_CAUTION,
                {
                    type: "heading",
                    attrs: { level: 3 },
                    content: [{ type: "text", text: "Tools required" }],
                },
                {
                    type: "bulletList",
                    content: [
                        {
                            type: "listItem",
                            content: [
                                {
                                    type: "paragraph",
                                    content: [{ type: "text", text: "Digital micrometer (0–1 in)" }],
                                },
                            ],
                        },
                        {
                            type: "listItem",
                            content: [
                                {
                                    type: "paragraph",
                                    content: [{ type: "text", text: "Setup sheet for P/N 11782-3" }],
                                },
                            ],
                        },
                        {
                            type: "listItem",
                            content: [
                                {
                                    type: "paragraph",
                                    content: [{ type: "text", text: "Hex key (3 mm)" }],
                                },
                            ],
                        },
                    ],
                },
                {
                    type: "heading",
                    attrs: { level: 3 },
                    content: [{ type: "text", text: "Material verification" }],
                },
                SAMPLE_TEXT_INPUT_SHORT,
                SAMPLE_SCAN,
                SAMPLE_ATTESTATION_CONFIRM,
            ],
        },
    },
    {
        id: "ss-2",
        order: 2,
        title: "Run first piece + measure",
        required: true,
        requires_signature: false,
        is_optional: false,
        body: {
            type: "doc",
            content: [
                {
                    type: "paragraph",
                    content: [
                        {
                            type: "text",
                            text: "Cycle the program once. After the part is unloaded, walk it to the bench and measure the OD.",
                        },
                    ],
                },
                SAMPLE_MEDIA,
                SAMPLE_CALLOUT_NOTE,
                SAMPLE_TIMER_COUNTDOWN,
                {
                    type: "heading",
                    attrs: { level: 3 },
                    content: [{ type: "text", text: "Critical dimension" }],
                },
                {
                    type: "paragraph",
                    content: [{ type: "text", text: "Target spec (reference only):" }],
                },
                SAMPLE_MEASUREMENT_SPEC,
                {
                    type: "paragraph",
                    content: [{ type: "text", text: "Record the actual reading after the first cut:" }],
                },
                SAMPLE_MEASUREMENT_INPUT,
                SAMPLE_COMPUTED_TRUE_POSITION,
                SAMPLE_CHOICE_RADIO,
            ],
        },
    },
    {
        id: "ss-3",
        order: 3,
        title: "Final inspection + sign-off",
        required: true,
        requires_signature: true,
        is_optional: false,
        body: {
            type: "doc",
            content: [
                {
                    type: "paragraph",
                    content: [
                        {
                            type: "text",
                            text: "Document the setup state and sign off when the lot is ready to release.",
                        },
                    ],
                },
                SAMPLE_CHOICE_SELECT,
                SAMPLE_PHOTO,
                SAMPLE_FILE,
                SAMPLE_TEXT_INPUT_LONG,
                {
                    type: "heading",
                    attrs: { level: 3 },
                    content: [{ type: "text", text: "Operator sign-off" }],
                },
                SAMPLE_ATTESTATION_SIGNATURE,
            ],
        },
    },
];

// ============================================================================
// SubstepEditor — engineer editor + live operator preview, side by side
// ============================================================================

function SubstepEditor({
    body,
    onChange,
}: {
    body: object;
    onChange: (next: object) => void;
}) {
    const [, forceRerender] = useState(0);

    const editor = useEditor({
        extensions: DWI_EXTENSIONS,
        content: body,
        onUpdate: ({ editor: e }) => {
            forceRerender((n) => n + 1);
            onChange(e.getJSON());
        },
        onSelectionUpdate: () => forceRerender((n) => n + 1),
    });

    const operatorEditor = useEditor({
        extensions: DWI_EXTENSIONS,
        content: body,
        editable: false,
    });

    useEffect(() => {
        if (!editor || !operatorEditor) return;
        const sync = () => {
            operatorEditor.commands.setContent(editor.getJSON(), { emitUpdate: false });
        };
        editor.on("update", sync);
        return () => {
            editor.off("update", sync);
        };
    }, [editor, operatorEditor]);

    return (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            {/* Engineer side */}
            <div className="flex flex-col rounded-md border bg-background">
                <PaneHeader
                    icon={<Pencil className="h-3.5 w-3.5" />}
                    title="Editor"
                    subtitle="engineer authoring"
                />
                <Toolbar editor={editor} />
                <div className="flex-1 overflow-auto">
                    <EditorContent
                        editor={editor}
                        className={
                            "px-4 py-3 focus:outline-none [&_.ProseMirror]:min-h-[200px] [&_.ProseMirror]:outline-none " +
                            PROSE_CLASSES
                        }
                    />
                </div>
            </div>

            {/* Operator preview side */}
            <div className="flex flex-col rounded-md border bg-background">
                <PaneHeader
                    icon={<Eye className="h-3.5 w-3.5" />}
                    title="Operator view"
                    subtitle="editable: false — inputs are live"
                />
                <div className="flex-1 overflow-auto">
                    {operatorEditor ? (
                        <EditorContent
                            editor={operatorEditor}
                            className={
                                "px-4 py-3 focus:outline-none [&_.ProseMirror]:min-h-[200px] [&_.ProseMirror]:outline-none " +
                                PROSE_CLASSES
                            }
                        />
                    ) : (
                        <div className="p-4 text-sm text-muted-foreground">Loading…</div>
                    )}
                </div>
            </div>
        </div>
    );
}

// ============================================================================
// SubstepRow — expandable accordion row for one substep
// ============================================================================

function SubstepRow({
    substep,
    expanded,
    onToggle,
    onBodyChange,
}: {
    substep: SubstepData;
    expanded: boolean;
    onToggle: () => void;
    onBodyChange: (next: object) => void;
}) {
    return (
        <div className="rounded-md border bg-card">
            <button
                type="button"
                onClick={onToggle}
                className="flex w-full items-center gap-3 px-3 py-2.5 text-left hover:bg-muted/50"
            >
                <GripVertical className="h-4 w-4 shrink-0 cursor-grab text-muted-foreground" />
                <span className="w-6 shrink-0 text-sm font-medium text-muted-foreground tabular-nums">
                    {substep.order}.
                </span>
                <span className="flex-1 text-sm font-medium">{substep.title}</span>
                {substep.required && (
                    <Badge variant="secondary" className="text-[10px]">Required</Badge>
                )}
                {substep.requires_signature && (
                    <Badge variant="outline" className="text-[10px]">
                        <PenLine className="mr-1 h-3 w-3" /> Sign-off
                    </Badge>
                )}
                {substep.is_optional && (
                    <Badge variant="outline" className="text-[10px]">Optional</Badge>
                )}
                {expanded ? (
                    <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
                ) : (
                    <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
                )}
            </button>
            {expanded && (
                <div className="border-t bg-muted/20 p-3">
                    <SubstepEditor body={substep.body} onChange={onBodyChange} />
                </div>
            )}
        </div>
    );
}

// ============================================================================
// DwiSpikePage — accordion-style list of substeps
// ============================================================================

export function DwiSpikePage() {
    const [substeps, setSubsteps] = useState<SubstepData[]>(SEED_SUBSTEPS);
    const [expandedId, setExpandedId] = useState<string | null>(SEED_SUBSTEPS[0].id);
    const [operatorResponses, setOperatorResponses] = useState<OperatorResponses>({});

    const responseContextValue = useMemo<OperatorResponseContextValue>(
        () => ({
            responses: operatorResponses,
            setResponse: (id, value) =>
                setOperatorResponses((prev) => ({ ...prev, [id]: value })),
        }),
        [operatorResponses],
    );

    const updateSubstepBody = (id: string, body: object) => {
        setSubsteps((prev) => prev.map((s) => (s.id === id ? { ...s, body } : s)));
    };

    return (
        <OperatorResponseContext.Provider value={responseContextValue}>
            <div className="flex h-[calc(100vh-1px)] flex-col bg-background">
                {/* Spike banner */}
                <div className="flex shrink-0 items-center gap-2 border-b bg-amber-50/60 px-6 py-1.5 text-xs text-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
                    <FlaskConical className="h-3.5 w-3.5" />
                    <span>
                        <span className="font-mono font-semibold">/dwi-spike</span> — throwaway
                        exploration. Not wired to any backend.
                    </span>
                </div>

                {/* Page header */}
                <div className="shrink-0 border-b px-6 py-4">
                    <h1 className="text-xl font-semibold tracking-tight">
                        Step 2 · OD Turn — Spacer P/N 11782-3
                    </h1>
                    <p className="text-sm text-muted-foreground">
                        Authoring view. Click a substep row to expand its editor + operator preview.
                        Operator captures land in the right-hand panel, keyed by node_id.
                    </p>
                </div>

                {/* Main area: substep list on the left, response panel on the right */}
                <div className="flex min-h-0 flex-1 p-4">
                    <ResizablePanelGroup direction="horizontal" className="overflow-hidden rounded-md border">
                        {/* Substep list */}
                        <ResizablePanel defaultSize={70} minSize={40}>
                            <div className="flex h-full flex-col bg-background">
                                <PaneHeader
                                    icon={<Pencil className="h-3.5 w-3.5" />}
                                    title="Substeps"
                                    subtitle={`${substeps.length} substeps in this step`}
                                />
                                <div className="flex-1 overflow-auto p-3">
                                    <div className="space-y-2">
                                        {substeps.map((s) => (
                                            <SubstepRow
                                                key={s.id}
                                                substep={s}
                                                expanded={expandedId === s.id}
                                                onToggle={() =>
                                                    setExpandedId(expandedId === s.id ? null : s.id)
                                                }
                                                onBodyChange={(body) => updateSubstepBody(s.id, body)}
                                            />
                                        ))}
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            className="w-full justify-start text-muted-foreground"
                                            onClick={() => {
                                                const newSubstep: SubstepData = {
                                                    id: `ss-${Date.now()}`,
                                                    order: substeps.length + 1,
                                                    title: `New substep ${substeps.length + 1}`,
                                                    body: { type: "doc", content: [{ type: "paragraph" }] },
                                                    required: true,
                                                    requires_signature: false,
                                                    is_optional: false,
                                                };
                                                setSubsteps((prev) => [...prev, newSubstep]);
                                                setExpandedId(newSubstep.id);
                                            }}
                                        >
                                            <Plus className="mr-2 h-4 w-4" />
                                            Add substep
                                        </Button>
                                    </div>
                                </div>
                            </div>
                        </ResizablePanel>

                        <ResizableHandle withHandle />

                        {/* Operator responses panel */}
                        <ResizablePanel defaultSize={30} minSize={20}>
                            <div className="flex h-full flex-col bg-background">
                                <PaneHeader
                                    icon={<Braces className="h-3.5 w-3.5" />}
                                    title="Operator responses"
                                    subtitle="captured per node_id across all substeps"
                                />
                                <pre className="flex-1 overflow-auto bg-muted/30 px-4 py-3 font-mono text-xs leading-relaxed">
                                    {Object.keys(operatorResponses).length === 0
                                        ? "// No responses captured yet.\n// Expand a substep on the left and interact with the operator preview."
                                        : JSON.stringify(operatorResponses, null, 2)}
                                </pre>
                            </div>
                        </ResizablePanel>
                    </ResizablePanelGroup>
                </div>
            </div>
        </OperatorResponseContext.Provider>
    );
}

export default DwiSpikePage;