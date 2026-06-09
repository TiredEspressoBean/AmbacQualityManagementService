/**
 * DwiSpikePage — throwaway exploration of the substep authoring UX.
 *
 * Custom nodes were extracted to `src/components/dwi/nodes/*` and the shared
 * extension list lives at `src/lib/dwi/extensions.ts`. This file now just
 * hosts the spike-only page shell and the `SubstepEditor` (engineer +
 * operator preview side by side).
 *
 * The production `SubstepEditorPage` re-uses `SubstepEditor`, `DWI_EXTENSIONS`,
 * and the `OperatorResponseContext` re-exported below so it stays a single
 * import surface as the per-node refactor finishes.
 */
import { useEffect, useMemo, useState } from "react";
import {
    useEditor,
    EditorContent,
    type Editor,
} from "@tiptap/react";
import { Button } from "@/components/ui/button";
import {
    ResizableHandle,
    ResizablePanel,
    ResizablePanelGroup,
} from "@/components/ui/resizable";
import {
    AlertTriangle,
    Bold,
    Braces,
    Calculator,
    Camera,
    CheckSquare,
    Code,
    Eye,
    FlaskConical,
    SlidersHorizontal,
    Gauge,
    Heading1,
    Heading2,
    Image as ImageIcon,
    FileText,
    Italic,
    List,
    ListChecks,
    ListOrdered,
    Minus,
    Paperclip,
    Pencil,
    PenLine,
    Plus,
    Quote,
    Redo,
    Ruler,
    ScanLine,
    Strikethrough,
    Timer as TimerIcon,
    Type,
    Undo,
    ChevronDown,
    ChevronRight,
    GripVertical,
    ShieldCheck,
    Wrench,
    Users,
    Bug,
    ClipboardCheck,
    ScanSearch,
    PackageOpen,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";

import { DWI_EXTENSIONS } from "@/lib/dwi/extensions";
import {
    SAMPLE_ATTESTATION_CONFIRM,
    SAMPLE_ATTESTATION_SIGNATURE,
    SAMPLE_CALLOUT_CAUTION,
    SAMPLE_CALLOUT_NOTE,
    SAMPLE_CHOICE_RADIO,
    SAMPLE_CHOICE_SELECT,
    SAMPLE_COMPUTED_TRUE_POSITION,
    SAMPLE_FILE,
    SAMPLE_MEASUREMENT_INPUT,
    SAMPLE_MEASUREMENT_SPEC,
    SAMPLE_MEDIA,
    SAMPLE_DOCUMENT_LINK,
    SAMPLE_PHOTO,
    SAMPLE_SCAN,
    SAMPLE_TEXT_INPUT_LONG,
    SAMPLE_TEXT_INPUT_SHORT,
    SAMPLE_TIMER_COUNTDOWN,
    SAMPLE_QUALITY_STATUS,
    SAMPLE_EQUIPMENT_ROLES,
    SAMPLE_PERSONNEL_ROLES,
    SAMPLE_INSPECTION_SIGNATURES,
    SAMPLE_ERROR_TYPES,
    SAMPLE_PART_ANNOTATION,
    SAMPLE_HARVESTED_COMPONENT_CAPTURE,
    QUALITY_REPORT_BUNDLE,
} from "@/lib/dwi/samples";
import { withFreshNodeId } from "@/lib/dwi/node-id";
import {
    OperatorResponseContext,
    type OperatorResponses,
    type OperatorResponseContextValue,
} from "@/components/dwi/shared/OperatorResponseContext";
import { NodePropertiesPanel } from "@/components/dwi/NodePropertiesPanel";
import { NodeSelection } from "@tiptap/pm/state";

// Re-export so the production page keeps importing from this module while
// the per-node refactor is in flight.
export { DWI_EXTENSIONS } from "@/lib/dwi/extensions";
export {
    OperatorResponseContext,
    type OperatorResponses,
    type OperatorResponseContextValue,
} from "@/components/dwi/shared/OperatorResponseContext";

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
            <ToolbarButton active={editor.isActive("bold")} onClick={() => editor.chain().focus().toggleBold().run()} icon={<Bold className="h-4 w-4" />} label="Bold" />
            <ToolbarButton active={editor.isActive("italic")} onClick={() => editor.chain().focus().toggleItalic().run()} icon={<Italic className="h-4 w-4" />} label="Italic" />
            <ToolbarButton active={editor.isActive("strike")} onClick={() => editor.chain().focus().toggleStrike().run()} icon={<Strikethrough className="h-4 w-4" />} label="Strikethrough" />
            <ToolbarButton active={editor.isActive("code")} onClick={() => editor.chain().focus().toggleCode().run()} icon={<Code className="h-4 w-4" />} label="Inline code" />
            <ToolbarDivider />
            <ToolbarButton active={editor.isActive("heading", { level: 1 })} onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()} icon={<Heading1 className="h-4 w-4" />} label="Heading 1" />
            <ToolbarButton active={editor.isActive("heading", { level: 2 })} onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()} icon={<Heading2 className="h-4 w-4" />} label="Heading 2" />
            <ToolbarDivider />
            <ToolbarButton active={editor.isActive("bulletList")} onClick={() => editor.chain().focus().toggleBulletList().run()} icon={<List className="h-4 w-4" />} label="Bullet list" />
            <ToolbarButton active={editor.isActive("orderedList")} onClick={() => editor.chain().focus().toggleOrderedList().run()} icon={<ListOrdered className="h-4 w-4" />} label="Ordered list" />
            <ToolbarButton active={editor.isActive("blockquote")} onClick={() => editor.chain().focus().toggleBlockquote().run()} icon={<Quote className="h-4 w-4" />} label="Blockquote" />
            <ToolbarButton onClick={() => editor.chain().focus().setHorizontalRule().run()} icon={<Minus className="h-4 w-4" />} label="Horizontal rule" />
            <ToolbarDivider />
            <ToolbarButton onClick={() => editor.chain().focus().undo().run()} icon={<Undo className="h-4 w-4" />} label="Undo" />
            <ToolbarButton onClick={() => editor.chain().focus().redo().run()} icon={<Redo className="h-4 w-4" />} label="Redo" />
            <ToolbarDivider />
            <ToolbarButton onClick={() => editor.chain().focus().insertContent(SAMPLE_CALLOUT_CAUTION).run()} icon={<AlertTriangle className="h-4 w-4" />} label="Insert callout" />
            <ToolbarButton onClick={() => editor.chain().focus().insertContent(SAMPLE_MEDIA).run()} icon={<ImageIcon className="h-4 w-4" />} label="Insert media" />
            <ToolbarButton onClick={() => editor.chain().focus().insertContent(SAMPLE_DOCUMENT_LINK).run()} icon={<FileText className="h-4 w-4" />} label="Insert document link" />
            <ToolbarButton onClick={() => editor.chain().focus().insertContent(withFreshNodeId(SAMPLE_MEASUREMENT_SPEC)).run()} icon={<Gauge className="h-4 w-4" />} label="Insert measurement spec" />
            <ToolbarButton onClick={() => editor.chain().focus().insertContent(withFreshNodeId(SAMPLE_MEASUREMENT_INPUT)).run()} icon={<Ruler className="h-4 w-4" />} label="Insert measurement input" />
            <ToolbarButton onClick={() => editor.chain().focus().insertContent(withFreshNodeId(SAMPLE_ATTESTATION_CONFIRM)).run()} icon={<CheckSquare className="h-4 w-4" />} label="Insert attestation" />
            <ToolbarButton onClick={() => editor.chain().focus().insertContent(withFreshNodeId(SAMPLE_ATTESTATION_SIGNATURE)).run()} icon={<PenLine className="h-4 w-4" />} label="Insert signature gate" />
            <ToolbarButton onClick={() => editor.chain().focus().insertContent(withFreshNodeId(SAMPLE_TEXT_INPUT_SHORT)).run()} icon={<Type className="h-4 w-4" />} label="Insert text input" />
            <ToolbarButton onClick={() => editor.chain().focus().insertContent(withFreshNodeId(SAMPLE_CHOICE_RADIO)).run()} icon={<ListChecks className="h-4 w-4" />} label="Insert choice input" />
            <ToolbarButton onClick={() => editor.chain().focus().insertContent(withFreshNodeId(SAMPLE_PHOTO)).run()} icon={<Camera className="h-4 w-4" />} label="Insert photo capture" />
            <ToolbarButton onClick={() => editor.chain().focus().insertContent(withFreshNodeId(SAMPLE_SCAN)).run()} icon={<ScanLine className="h-4 w-4" />} label="Insert scan input" />
            <ToolbarButton onClick={() => editor.chain().focus().insertContent(withFreshNodeId(SAMPLE_FILE)).run()} icon={<Paperclip className="h-4 w-4" />} label="Insert file capture" />
            <ToolbarButton onClick={() => editor.chain().focus().insertContent(withFreshNodeId(SAMPLE_TIMER_COUNTDOWN)).run()} icon={<TimerIcon className="h-4 w-4" />} label="Insert timer (countdown)" />
            <ToolbarButton onClick={() => editor.chain().focus().insertContent(withFreshNodeId(SAMPLE_COMPUTED_TRUE_POSITION)).run()} icon={<Calculator className="h-4 w-4" />} label="Insert computed value" />
            <ToolbarDivider />
            <ToolbarButton onClick={() => editor.chain().focus().insertContent(withFreshNodeId(SAMPLE_QUALITY_STATUS)).run()} icon={<ShieldCheck className="h-4 w-4" />} label="Insert quality status" />
            <ToolbarButton onClick={() => editor.chain().focus().insertContent(withFreshNodeId(SAMPLE_EQUIPMENT_ROLES)).run()} icon={<Wrench className="h-4 w-4" />} label="Insert equipment + roles" />
            <ToolbarButton onClick={() => editor.chain().focus().insertContent(withFreshNodeId(SAMPLE_PERSONNEL_ROLES)).run()} icon={<Users className="h-4 w-4" />} label="Insert personnel + roles" />
            <ToolbarButton onClick={() => editor.chain().focus().insertContent(withFreshNodeId(SAMPLE_INSPECTION_SIGNATURES)).run()} icon={<PenLine className="h-4 w-4" />} label="Insert inspection signatures" />
            <ToolbarButton onClick={() => editor.chain().focus().insertContent(withFreshNodeId(SAMPLE_ERROR_TYPES)).run()} icon={<Bug className="h-4 w-4" />} label="Insert defect findings" />
            <ToolbarButton onClick={() => editor.chain().focus().insertContent(withFreshNodeId(SAMPLE_PART_ANNOTATION)).run()} icon={<ScanSearch className="h-4 w-4" />} label="Insert part annotation (3D)" />
            <ToolbarButton onClick={() => editor.chain().focus().insertContent(withFreshNodeId(SAMPLE_HARVESTED_COMPONENT_CAPTURE)).run()} icon={<PackageOpen className="h-4 w-4" />} label="Insert harvested-components capture (teardown)" />
            {/* Bundle — drops the minimum capture set for a complete
                QualityReport in one click. Set the parent substep's
                `is_inspection_point` toggle to actually promote captures. */}
            <ToolbarButton
                onClick={() =>
                    editor
                        .chain()
                        .focus()
                        .insertContent(QUALITY_REPORT_BUNDLE.map((n) => withFreshNodeId(n)))
                        .run()
                }
                icon={<ClipboardCheck className="h-4 w-4" />}
                label="Insert QA inspection bundle"
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

// ============================================================================
// SubstepEditor — engineer editor + live operator preview, side by side
// ============================================================================

export function SubstepEditor({
    body,
    onChange,
    editable = true,
}: {
    body: object;
    onChange: (next: object) => void;
    /** When false (e.g. Process is APPROVED), the engineer pane is read-only
     *  alongside the operator preview. */
    editable?: boolean;
}) {
    const [, forceRerender] = useState(0);

    const editor = useEditor({
        extensions: DWI_EXTENSIONS,
        content: body,
        editable,
        onUpdate: ({ editor: e }) => {
            forceRerender((n) => n + 1);
            onChange(e.getJSON());
        },
        onSelectionUpdate: () => forceRerender((n) => n + 1),
    }, [editable]);

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

    // Right pane swaps between Properties (when a custom node is selected)
    // and Operator preview (otherwise) — keeps the 2-column layout while the
    // properties pattern is exercised.
    const hasNodeSelection =
        editor != null && editor.state.selection instanceof NodeSelection;

    return (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            {/* Engineer editor */}
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

            {/* Right pane: Properties when node selected, else Operator preview.
                Sticky so the form stays in view while the engineer scrolls the
                editor; `self-start` lets the pane size to its own content. */}
            <div className="flex flex-col rounded-md border bg-background lg:sticky lg:top-4 lg:self-start lg:max-h-[calc(100vh-6rem)]">
                {hasNodeSelection ? (
                    <>
                        <PaneHeader
                            icon={<SlidersHorizontal className="h-3.5 w-3.5" />}
                            title="Properties"
                            subtitle="selected node — click elsewhere to dismiss"
                        />
                        <div className="flex-1 overflow-auto">
                            <NodePropertiesPanel editor={editor} />
                        </div>
                    </>
                ) : (
                    <>
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
                    </>
                )}
            </div>
        </div>
    );
}

// ============================================================================
// Spike-only seed substeps + page shell
// ============================================================================

type SubstepData = {
    id: string;
    order: number;
    title: string;
    body: object;
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
                        { type: "text", text: "Cycle the program once. After the part is unloaded, walk it to the bench and measure the OD." },
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
                SAMPLE_MEASUREMENT_SPEC,
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
                        { type: "text", text: "Document the setup state and sign off when the lot is ready to release." },
                    ],
                },
                SAMPLE_CHOICE_SELECT,
                SAMPLE_PHOTO,
                SAMPLE_FILE,
                SAMPLE_TEXT_INPUT_LONG,
                SAMPLE_ATTESTATION_SIGNATURE,
            ],
        },
    },
];

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
                <div className="flex shrink-0 items-center gap-2 border-b bg-amber-50/60 px-6 py-1.5 text-xs text-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
                    <FlaskConical className="h-3.5 w-3.5" />
                    <span>
                        <span className="font-mono font-semibold">/dwi-spike</span> — throwaway
                        exploration. Not wired to any backend.
                    </span>
                </div>
                <div className="shrink-0 border-b px-6 py-4">
                    <h1 className="text-xl font-semibold tracking-tight">
                        Step 2 · OD Turn — Spacer P/N 11782-3
                    </h1>
                    <p className="text-sm text-muted-foreground">
                        Authoring view. Click a substep row to expand its editor + operator preview.
                        Operator captures land in the right-hand panel, keyed by node_id.
                    </p>
                </div>
                <div className="flex min-h-0 flex-1 p-4">
                    <ResizablePanelGroup direction="horizontal" className="overflow-hidden rounded-md border">
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
