/**
 * SubstepEditorPage
 *
 * Authoring surface for substeps within a Step. Route:
 *   /editor/processes/$processId/steps/$stepId/substeps
 *
 * Layout: accordion list of substeps. Each row shows title + flags
 * (Required / Optional / Sign-off / Inspection point); expanding opens
 * the dual-pane editor (engineer authoring + operator preview side-by-side).
 *
 * Persistence: editor body_blocks autosave via debounced PATCH on edit.
 * Title / flag changes are immediate on blur. New substep creation is
 * explicit via the "Add substep" button.
 *
 * Note on architecture: the editor itself (`SubstepEditor` + `DWI_EXTENSIONS`)
 * is imported from `DwiSpikePage.tsx` to avoid re-implementing the 12-node
 * library. When the per-node refactor lands (per design doc decision #20),
 * those move to `src/lib/dwi/extensions.ts` and `src/components/dwi/nodes/`,
 * and the spike file can be deleted.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "@tanstack/react-router";
import { useQueryClient } from "@tanstack/react-query";
import {
    SubstepEditor,
    OperatorResponseContext,
    type OperatorResponses,
    type OperatorResponseContextValue,
} from "@/pages/DwiSpikePage";
import {
    useSubsteps,
    useCreateSubstep,
    useUpdateSubstep,
    useDeleteSubstep,
    type Substep,
} from "@/hooks/useSubsteps";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import {
    ChevronDown,
    ChevronRight,
    GripVertical,
    PenLine,
    Plus,
    Trash2,
    Loader2,
    FlaskConical,
} from "lucide-react";

// Pull the start step from the URL so the page can scope by step.
type RouteParams = {
    processId: string;
    stepId: string;
};

export function SubstepEditorPage() {
    const params = useParams({ strict: false }) as Partial<RouteParams>;
    const stepId = params.stepId;

    const { data, isLoading, isError, error } = useSubsteps(
        stepId ? { step: stepId } : undefined,
    );
    const [expandedId, setExpandedId] = useState<string | null>(null);

    // Operator response context for the preview pane. The engineer-side page
    // doesn't actually persist responses (that's the operator runtime's job)
    // — this is just so the preview pane is interactive during authoring.
    const [previewResponses, setPreviewResponses] = useState<OperatorResponses>({});
    const previewContextValue = useMemo<OperatorResponseContextValue>(
        () => ({
            responses: previewResponses,
            setResponse: (id, value) =>
                setPreviewResponses((prev) => ({ ...prev, [id]: value })),
        }),
        [previewResponses],
    );

    const create = useCreateSubstep();

    if (!stepId) {
        return (
            <div className="p-6">
                <h1 className="text-xl font-semibold">Substep Editor</h1>
                <p className="mt-2 text-sm text-muted-foreground">
                    Missing stepId in the route. Navigate via{" "}
                    <code className="font-mono text-xs">
                        /editor/processes/$processId/steps/$stepId/substeps
                    </code>
                    .
                </p>
            </div>
        );
    }

    const substeps: Substep[] = (data?.results as Substep[] | undefined) ?? [];
    // Substeps are ordered by `order` field already by the viewset, but list
    // pagination can re-shuffle in edge cases; resort defensively.
    const sortedSubsteps = [...substeps].sort((a, b) => a.order - b.order);

    const handleAdd = () => {
        const nextOrder = sortedSubsteps.length
            ? Math.max(...sortedSubsteps.map((s) => s.order)) + 1
            : 0;
        create.mutate(
            {
                step: stepId,
                order: nextOrder,
                title: `New substep ${nextOrder + 1}`,
                body_blocks: {
                    type: "doc",
                    content: [{ type: "paragraph" }],
                } as never,
            },
            {
                onSuccess: (created) => setExpandedId(created.id),
            },
        );
    };

    return (
        <OperatorResponseContext.Provider value={previewContextValue}>
            <div className="flex h-[calc(100vh-4rem)] flex-col">
                {/* Header */}
                <div className="shrink-0 border-b bg-background px-6 py-4">
                    <h1 className="text-xl font-semibold tracking-tight">Substep Editor</h1>
                    <p className="text-sm text-muted-foreground">
                        Authoring view for substeps in this step. Edits autosave to the
                        backend. The right pane shows the operator-mode preview live.
                    </p>
                </div>

                {/* Substep list */}
                <div className="flex-1 overflow-auto bg-muted/20 p-4">
                    {isLoading ? (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            Loading substeps…
                        </div>
                    ) : isError ? (
                        <div className="rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
                            Failed to load substeps: {String(error)}
                        </div>
                    ) : (
                        <div className="space-y-2">
                            {sortedSubsteps.map((s) => (
                                <SubstepRow
                                    key={s.id}
                                    substep={s}
                                    expanded={expandedId === s.id}
                                    onToggle={() =>
                                        setExpandedId(expandedId === s.id ? null : s.id)
                                    }
                                />
                            ))}
                            <Button
                                variant="ghost"
                                size="sm"
                                className="w-full justify-start text-muted-foreground"
                                onClick={handleAdd}
                                disabled={create.isPending}
                            >
                                {create.isPending ? (
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                ) : (
                                    <Plus className="mr-2 h-4 w-4" />
                                )}
                                Add substep
                            </Button>
                        </div>
                    )}
                </div>
            </div>
        </OperatorResponseContext.Provider>
    );
}

// ============================================================================
// SubstepRow — collapsed/expanded row in the accordion
// ============================================================================

function SubstepRow({
    substep,
    expanded,
    onToggle,
}: {
    substep: Substep;
    expanded: boolean;
    onToggle: () => void;
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
                <span className="flex-1 text-sm font-medium">
                    {substep.title || <span className="text-muted-foreground italic">Untitled</span>}
                </span>
                {!substep.is_optional && (
                    <Badge variant="secondary" className="text-[10px]">
                        Required
                    </Badge>
                )}
                {substep.is_optional && (
                    <Badge variant="outline" className="text-[10px]">
                        Optional
                    </Badge>
                )}
                {substep.requires_signature && (
                    <Badge variant="outline" className="text-[10px]">
                        <PenLine className="mr-1 h-3 w-3" /> Sign-off
                    </Badge>
                )}
                {substep.is_inspection_point && (
                    <Badge variant="default" className="bg-amber-600 text-[10px] text-white">
                        <FlaskConical className="mr-1 h-3 w-3" /> Inspection
                    </Badge>
                )}
                {expanded ? (
                    <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
                ) : (
                    <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
                )}
            </button>
            {expanded && <SubstepExpandedBody substep={substep} />}
        </div>
    );
}

// ============================================================================
// SubstepExpandedBody — the expanded editor with autosave + meta controls
// ============================================================================

function SubstepExpandedBody({ substep }: { substep: Substep }) {
    const update = useUpdateSubstep();
    const remove = useDeleteSubstep();
    const qc = useQueryClient();

    // Local copies for cursor-stable controlled inputs.
    const [titleLocal, setTitleLocal] = useState(substep.title);
    const [optionalLocal, setOptionalLocal] = useState(substep.is_optional);
    const [signatureLocal, setSignatureLocal] = useState(substep.requires_signature);
    const [inspectionLocal, setInspectionLocal] = useState(substep.is_inspection_point);

    // Resync when prop changes (e.g. from query refetch).
    useEffect(() => setTitleLocal(substep.title), [substep.title]);
    useEffect(() => setOptionalLocal(substep.is_optional), [substep.is_optional]);
    useEffect(() => setSignatureLocal(substep.requires_signature), [substep.requires_signature]);
    useEffect(() => setInspectionLocal(substep.is_inspection_point), [substep.is_inspection_point]);

    // Debounced autosave for body_blocks. 600ms — heavier than the popover
    // attr debounce (250ms) because body edits typically come in bursts
    // during typing.
    const bodyTimerRef = useRef<number | null>(null);
    const handleBodyChange = useCallback(
        (next: object) => {
            if (bodyTimerRef.current != null) window.clearTimeout(bodyTimerRef.current);
            bodyTimerRef.current = window.setTimeout(() => {
                update.mutate(
                    { id: substep.id, data: { body_blocks: next as never } },
                    {
                        onSuccess: () => {
                            // No-op — list cache invalidates via the hook.
                        },
                    },
                );
                bodyTimerRef.current = null;
            }, 600);
        },
        [substep.id, update],
    );

    useEffect(() => {
        return () => {
            if (bodyTimerRef.current != null) window.clearTimeout(bodyTimerRef.current);
        };
    }, []);

    const handleDelete = () => {
        if (!window.confirm(`Delete substep "${substep.title}"? This cannot be undone.`)) return;
        remove.mutate(substep.id, {
            onSuccess: () => {
                qc.invalidateQueries({ queryKey: ["substeps"] });
            },
        });
    };

    return (
        <div className="space-y-3 border-t bg-muted/10 p-3">
            {/* Meta controls row */}
            <div className="flex flex-wrap items-center gap-3 rounded-md border bg-background p-2 text-sm">
                <div className="flex flex-1 items-center gap-2">
                    <Label htmlFor={`title-${substep.id}`} className="text-xs">
                        Title
                    </Label>
                    <Input
                        id={`title-${substep.id}`}
                        value={titleLocal}
                        onChange={(e) => setTitleLocal(e.target.value)}
                        onBlur={() => {
                            if (titleLocal !== substep.title) {
                                update.mutate({ id: substep.id, data: { title: titleLocal } });
                            }
                        }}
                        className="h-8 text-sm"
                    />
                </div>

                <div className="flex items-center gap-2">
                    <Switch
                        id={`optional-${substep.id}`}
                        checked={optionalLocal}
                        onCheckedChange={(v) => {
                            setOptionalLocal(v);
                            update.mutate({ id: substep.id, data: { is_optional: v } });
                        }}
                    />
                    <Label htmlFor={`optional-${substep.id}`} className="text-xs">
                        Optional
                    </Label>
                </div>

                <div className="flex items-center gap-2">
                    <Switch
                        id={`signature-${substep.id}`}
                        checked={signatureLocal}
                        onCheckedChange={(v) => {
                            setSignatureLocal(v);
                            update.mutate({ id: substep.id, data: { requires_signature: v } });
                        }}
                    />
                    <Label htmlFor={`signature-${substep.id}`} className="text-xs">
                        Sign-off
                    </Label>
                </div>

                <div className="flex items-center gap-2">
                    <Switch
                        id={`inspection-${substep.id}`}
                        checked={inspectionLocal}
                        onCheckedChange={(v) => {
                            setInspectionLocal(v);
                            update.mutate({ id: substep.id, data: { is_inspection_point: v } });
                        }}
                    />
                    <Label
                        htmlFor={`inspection-${substep.id}`}
                        className="text-xs"
                        title="When set, MeasurementInput captures in this substep create binding inspection records (auto-quarantine on out-of-spec, NCR notification). Default off."
                    >
                        Inspection point
                    </Label>
                </div>

                <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleDelete}
                    disabled={remove.isPending}
                    className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                >
                    {remove.isPending ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                        <Trash2 className="h-4 w-4" />
                    )}
                </Button>
            </div>

            {/* The editor (engineer + operator preview side by side) */}
            <SubstepEditor
                body={(substep.body_blocks as unknown as object) ?? { type: "doc", content: [] }}
                onChange={handleBodyChange}
            />

            {/* Save indicator */}
            {update.isPending && (
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    Saving…
                </div>
            )}
        </div>
    );
}

export default SubstepEditorPage;
