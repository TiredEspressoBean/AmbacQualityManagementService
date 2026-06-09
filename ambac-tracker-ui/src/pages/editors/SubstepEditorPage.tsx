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
 * Persistence model — explicit "Save Draft" (compliance simplicity over
 * fancy UX):
 * - No autosave. Edits accumulate in page-level state per substep.
 * - "Save Draft" button per expanded row PATCHes the backend.
 * - `beforeunload` warns if there are unsaved changes on the page when the
 *   user tries to close/navigate away.
 * - Collapsing a row preserves its pending edits in memory (the engineer
 *   can revisit it without losing work); only page-close drops them.
 *
 * Why this shape (vs. autosave): substeps belong to versioned Processes;
 * each save is an auditable change. Autosave at 600ms debounce would
 * generate hundreds of audit-log entries per edit session, almost all of
 * them mid-keystroke noise that nobody will ever review. Save Draft makes
 * each PATCH a logically meaningful checkpoint. (See conversation that
 * landed this design.)
 *
 * Note on architecture: the editor itself (`SubstepEditor` + `DWI_EXTENSIONS`)
 * is imported from `DwiSpikePage.tsx` to avoid re-implementing the 12-node
 * library. When the per-node refactor lands (per design doc decision #20),
 * those move to `src/lib/dwi/extensions.ts` and `src/components/dwi/nodes/`,
 * and the spike file can be deleted.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams, Link, useBlocker } from "@tanstack/react-router";
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
    useReorderSubsteps,
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
    Save,
    Undo2,
    ArrowLeft,
    ClipboardCheck,
} from "lucide-react";
import { QUALITY_REPORT_BUNDLE } from "@/lib/dwi/samples";
import { withFreshNodeId } from "@/lib/dwi/node-id";
import { SubstepAuthoringProvider } from "@/components/dwi/shared/SubstepAuthoringContext";

type RouteParams = {
    processId: string;
    stepId: string;
};

// Back-link routing target. We keep this as a typed object so the breadcrumb
// stays in sync if the process-flow route signature changes.
const PROCESS_FLOW_PATH = "/process-flow" as const;

/**
 * The shape of a working draft held in page-level state. Each field is
 * present only when it differs from the backend substep — undefined fields
 * mean "no pending change to this field."
 */
type PendingEdits = {
    body_blocks?: object;
    title?: string;
    is_optional?: boolean;
    requires_signature?: boolean;
    is_inspection_point?: boolean;
    is_critical?: boolean;
    allow_not_applicable?: boolean;
};

/**
 * A new substep the engineer has added but not yet saved. Held purely in
 * page state until Save Draft creates it server-side. This is the fix for
 * the bug where "Add substep" was POSTing immediately and leaving empty
 * substeps behind in the backend when the engineer abandoned the page.
 *
 * `tempId` is only used to key the React list and route per-row edits;
 * it never leaves the client.
 */
type PendingCreate = {
    tempId: string;
    order: number;
    title: string;
    body_blocks: object;
    is_optional: boolean;
    requires_signature: boolean;
    is_inspection_point: boolean;
    is_critical: boolean;
    allow_not_applicable: boolean;
};

let _tempIdCounter = 0;
const nextTempId = () => `__new_${Date.now()}_${++_tempIdCounter}`;

export function SubstepEditorPage() {
    const params = useParams({ strict: false }) as Partial<RouteParams>;
    const stepId = params.stepId;
    const processId = params.processId;

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

    // Per-substep pending-edits map. A substep's id appearing here with a
    // non-empty object means it has unsaved changes.
    const [pendingBySubstepId, setPendingBySubstepId] = useState<
        Record<string, PendingEdits>
    >({});

    // Locally-staged new substeps. These don't exist on the server until
    // Save Draft. Editing one mutates the entry in-place; on save we POST
    // them in order.
    const [pendingCreates, setPendingCreates] = useState<PendingCreate[]>([]);

    // Substep ids the engineer has marked for deletion. Backend is not
    // touched until Save Draft. The row stays visible but rendered with a
    // strikethrough so the change is reviewable before committing.
    const [pendingDeletes, setPendingDeletes] = useState<Set<string>>(new Set());

    // Drag-to-reorder. Same Save-Draft compliance model as body/title/flags:
    // dragging accumulates a `pendingOrder` (string[] of substep ids) and
    // persists only when the engineer clicks Save draft in the header.
    const [draggingId, setDraggingId] = useState<string | null>(null);
    const [dragOverId, setDragOverId] = useState<string | null>(null);
    const [pendingOrder, setPendingOrder] = useState<string[] | null>(null);

    const hasPendingOrder = pendingOrder !== null;
    const hasUnsavedChanges = useMemo(
        () =>
            hasPendingOrder ||
            pendingCreates.length > 0 ||
            pendingDeletes.size > 0 ||
            Object.values(pendingBySubstepId).some(
                (p) => p && Object.keys(p).length > 0,
            ),
        [hasPendingOrder, pendingBySubstepId, pendingCreates.length, pendingDeletes],
    );

    // beforeunload warning when there are unsaved changes anywhere on the page.
    // Modern browsers show their generic "Changes you made may not be saved"
    // dialog — the text can't be customized, but the protection is reliable
    // across tab close, refresh, and external navigation.
    useEffect(() => {
        if (!hasUnsavedChanges) return;
        const handler = (e: BeforeUnloadEvent) => {
            e.preventDefault();
            // Required for some older browsers to actually trigger the prompt.
            e.returnValue = "";
        };
        window.addEventListener("beforeunload", handler);
        return () => window.removeEventListener("beforeunload", handler);
    }, [hasUnsavedChanges]);

    // SPA-aware nav guard. beforeunload only fires on full unload; TanStack
    // Router transitions (back link, sidebar nav, programmatic navigate())
    // need their own confirm. Returning true blocks the navigation.
    useBlocker({
        shouldBlockFn: () => {
            if (!hasUnsavedChanges) return false;
            return !window.confirm(
                "You have unsaved changes. Leave this page and discard them?",
            );
        },
    });

    const setPendingFor = useCallback(
        (substepId: string, patch: PendingEdits | null) => {
            setPendingBySubstepId((prev) => {
                if (patch === null || Object.keys(patch).length === 0) {
                    const next = { ...prev };
                    delete next[substepId];
                    return next;
                }
                return { ...prev, [substepId]: patch };
            });
        },
        [],
    );

    const create = useCreateSubstep();
    const update = useUpdateSubstep();
    const reorder = useReorderSubsteps();
    const remove = useDeleteSubstep();

    /** Toggle a substep's "pending delete" state. No backend call. */
    const togglePendingDelete = useCallback((substepId: string) => {
        setPendingDeletes((prev) => {
            const next = new Set(prev);
            if (next.has(substepId)) next.delete(substepId);
            else next.add(substepId);
            return next;
        });
    }, []);

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
    // DRAFT-only authoring guard. The backend stamps each substep with
    // `is_editable` (derived from its parent Step's consuming Processes —
    // all must be DRAFT). Every substep on the same Step agrees, so we
    // sample the first. Empty list → assume editable; backend will reject
    // the create if it's not.
    const isEditable = substeps.length === 0
        ? true
        : Boolean((substeps[0] as Substep & { is_editable?: boolean }).is_editable);

    const sortedSubsteps = useMemo(() => {
        const byOrder = [...substeps].sort((a, b) => a.order - b.order);
        if (!pendingOrder) return byOrder;
        const idx = new Map(pendingOrder.map((id, i) => [id, i]));
        // Fall back to backend order for any substep that wasn't part of the
        // pending snapshot (e.g. created after the user started dragging).
        return byOrder.sort((a, b) => {
            const ai = idx.get(a.id) ?? Number.POSITIVE_INFINITY;
            const bi = idx.get(b.id) ?? Number.POSITIVE_INFINITY;
            return ai - bi;
        });
    }, [substeps, pendingOrder]);

    const handleReorder = (movedId: string, targetId: string) => {
        if (movedId === targetId) return;
        const fromIdx = sortedSubsteps.findIndex((s) => s.id === movedId);
        const toIdx = sortedSubsteps.findIndex((s) => s.id === targetId);
        if (fromIdx === -1 || toIdx === -1) return;
        const reordered = [...sortedSubsteps];
        const [moved] = reordered.splice(fromIdx, 1);
        reordered.splice(toIdx, 0, moved);
        const nextIds = reordered.map((s) => s.id);
        // If we've drifted back to the backend order, drop the pending state.
        const backendIds = [...substeps]
            .sort((a, b) => a.order - b.order)
            .map((s) => s.id);
        if (
            nextIds.length === backendIds.length &&
            nextIds.every((id, i) => id === backendIds[i])
        ) {
            setPendingOrder(null);
        } else {
            setPendingOrder(nextIds);
        }
    };

    /** Save everything: pending creates (POST), per-row pending edits
     *  (parallel PATCHes), and the pending reorder (POST) in a single
     *  user action.
     *
     *  Order matters: we POST the new substeps first so their server-side
     *  ids exist before any reorder that might reference them. Reorder of
     *  *only* pre-existing substeps is unaffected. */
    const [isSaving, setIsSaving] = useState(false);
    const handleSaveAll = async () => {
        if (!hasUnsavedChanges || !stepId) return;
        setIsSaving(true);
        try {
            // 1. DELETE pending deletes first so freed order slots are
            //    available for any subsequent inserts/reorders.
            const deleteIds = Array.from(pendingDeletes);
            await Promise.all(deleteIds.map((id) => remove.mutateAsync(id)));

            // 2. POST pending creates sequentially in order. Server enforces
            //    the (step, order) unique constraint; sending them one at a
            //    time keeps us out of races with the local order numbers.
            for (const draft of pendingCreates) {
                await create.mutateAsync({
                    step: stepId,
                    order: draft.order,
                    title: draft.title,
                    body_blocks: draft.body_blocks as never,
                    is_optional: draft.is_optional,
                    requires_signature: draft.requires_signature,
                    is_inspection_point: draft.is_inspection_point,
                    is_critical: draft.is_critical,
                    allow_not_applicable: draft.allow_not_applicable,
                } as never);
            }

            // 3. PATCH per-row edits on still-alive existing substeps. Skip
            //    any row that's been staged for delete — no point sending an
            //    edit for a row we're about to drop.
            const rowEntries = Object.entries(pendingBySubstepId).filter(
                ([id, p]) =>
                    p && Object.keys(p).length > 0 && !pendingDeletes.has(id),
            );
            await Promise.all(
                rowEntries.map(([id, data]) =>
                    update.mutateAsync({ id, data: data as never }),
                ),
            );

            // 4. Reorder (existing-only — pending creates haven't joined
            //    pendingOrder since dragging temp rows is disabled). Drop
            //    any ids that were just deleted so the server payload is
            //    consistent with the new world.
            if (pendingOrder) {
                const finalOrder = pendingOrder.filter(
                    (id) => !pendingDeletes.has(id),
                );
                if (finalOrder.length) {
                    await reorder.mutateAsync({ step: stepId, order: finalOrder });
                }
            }

            setPendingBySubstepId({});
            setPendingCreates([]);
            setPendingDeletes(new Set());
            setPendingOrder(null);
        } finally {
            setIsSaving(false);
        }
    };

    const handleDiscardAll = () => {
        if (!hasUnsavedChanges) return;
        if (
            !window.confirm(
                "Discard all unsaved changes (new substeps, edits, deletions, and reorder)? This cannot be undone.",
            )
        )
            return;
        setPendingBySubstepId({});
        setPendingCreates([]);
        setPendingDeletes(new Set());
        setPendingOrder(null);
    };

    /** Stage a new substep in local state. Nothing hits the backend until
     *  Save Draft. Editing the staged row before save mutates the entry
     *  in pendingCreates directly. */
    const stageCreate = (
        seed: Partial<PendingCreate> & Pick<PendingCreate, "title" | "body_blocks">,
    ) => {
        const existingOrders = [
            ...sortedSubsteps.map((s) => s.order),
            ...pendingCreates.map((p) => p.order),
        ];
        const nextOrder = existingOrders.length ? Math.max(...existingOrders) + 1 : 0;
        const draft: PendingCreate = {
            tempId: nextTempId(),
            order: nextOrder,
            is_optional: false,
            requires_signature: false,
            is_inspection_point: false,
            is_critical: false,
            allow_not_applicable: false,
            ...seed,
        };
        setPendingCreates((prev) => [...prev, draft]);
        setExpandedId(draft.tempId);
    };

    const handleAdd = () => {
        const order =
            (sortedSubsteps.length || pendingCreates.length
                ? Math.max(
                      ...sortedSubsteps.map((s) => s.order),
                      ...pendingCreates.map((p) => p.order),
                  ) + 1
                : 0);
        stageCreate({
            title: `New substep ${order + 1}`,
            body_blocks: { type: "doc", content: [{ type: "paragraph" }] },
        });
    };

    /** Template: a substep configured as an inspection point with the
     *  minimum capture set seeded. */
    const handleAddInspection = () => {
        const order =
            (sortedSubsteps.length || pendingCreates.length
                ? Math.max(
                      ...sortedSubsteps.map((s) => s.order),
                      ...pendingCreates.map((p) => p.order),
                  ) + 1
                : 0);
        stageCreate({
            title: `Inspection ${order + 1}`,
            is_inspection_point: true,
            body_blocks: {
                type: "doc",
                content: [
                    {
                        type: "paragraph",
                        content: [
                            { type: "text", text: "Capture the inspection result." },
                        ],
                    },
                    ...QUALITY_REPORT_BUNDLE.map((n) => withFreshNodeId(n)),
                ],
            },
        });
    };

    /** Apply a patch to a staged (not-yet-saved) substep. */
    const updatePendingCreate = useCallback(
        (tempId: string, patch: Partial<PendingCreate>) => {
            setPendingCreates((prev) =>
                prev.map((d) => (d.tempId === tempId ? { ...d, ...patch } : d)),
            );
        },
        [],
    );

    /** Remove a staged substep without ever touching the backend. */
    const removePendingCreate = useCallback((tempId: string) => {
        setPendingCreates((prev) => prev.filter((d) => d.tempId !== tempId));
    }, []);

    const unsavedCount =
        Object.keys(pendingBySubstepId).length +
        pendingCreates.length +
        pendingDeletes.size;

    return (
        <SubstepAuthoringProvider value={{ stepId, processId }}>
        <OperatorResponseContext.Provider value={previewContextValue}>
            <div className="flex h-[calc(100vh-4rem)] flex-col">
                {/* Header */}
                <div className="flex shrink-0 items-center justify-between border-b bg-background px-6 py-4">
                    <div className="space-y-1">
                        {processId && (
                            <Link
                                to={PROCESS_FLOW_PATH}
                                search={{ id: processId }}
                                className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                            >
                                <ArrowLeft className="h-3 w-3" />
                                Back to process flow
                            </Link>
                        )}
                        <div className="flex items-center gap-2">
                            <h1 className="text-xl font-semibold tracking-tight">Substep Editor</h1>
                            {!isEditable && (
                                <Badge variant="outline" className="border-muted-foreground/40 text-[10px] text-muted-foreground">
                                    Read-only · Process not in DRAFT
                                </Badge>
                            )}
                        </div>
                        <p className="text-sm text-muted-foreground">
                            {isEditable
                                ? <>Authoring view. Edits stay local until you click <b>Save Draft</b>; the page warns if you close with unsaved changes.</>
                                : "This process is approved or deprecated; substeps are locked. Submit a Process Change Request to edit."}
                        </p>
                    </div>
                    <div className="flex items-center gap-2">
                        {hasUnsavedChanges && (
                            <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                                {unsavedCount > 0 && (
                                    <Badge variant="outline" className="border-amber-500/60 text-[10px] text-amber-600">
                                        {unsavedCount} edit{unsavedCount === 1 ? "" : "s"}
                                    </Badge>
                                )}
                                {hasPendingOrder && (
                                    <Badge variant="outline" className="border-amber-500/60 text-[10px] text-amber-600">
                                        Order changed
                                    </Badge>
                                )}
                            </div>
                        )}
                        {isEditable && (
                            <>
                                <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={handleDiscardAll}
                                    disabled={!hasUnsavedChanges || isSaving}
                                >
                                    <Undo2 className="mr-1.5 h-3.5 w-3.5" />
                                    Discard
                                </Button>
                                <Button
                                    size="sm"
                                    onClick={handleSaveAll}
                                    disabled={!hasUnsavedChanges || isSaving}
                                >
                                    {isSaving ? (
                                        <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                                    ) : (
                                        <Save className="mr-1.5 h-3.5 w-3.5" />
                                    )}
                                    Save draft
                                </Button>
                            </>
                        )}
                    </div>
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
                                    pending={pendingBySubstepId[s.id]}
                                    isPendingDelete={pendingDeletes.has(s.id)}
                                    onTogglePendingDelete={() => togglePendingDelete(s.id)}
                                    isDragging={draggingId === s.id}
                                    isDragOver={dragOverId === s.id && draggingId !== s.id}
                                    editable={isEditable}
                                    onToggle={() =>
                                        setExpandedId(expandedId === s.id ? null : s.id)
                                    }
                                    onPendingChange={(patch) =>
                                        setPendingFor(s.id, patch)
                                    }
                                    onDragStart={() => setDraggingId(s.id)}
                                    onDragEnter={() => setDragOverId(s.id)}
                                    onDragLeaveRow={() => {
                                        // Only clear if this row is the current target — guards
                                        // against the leave from a child element fluttering.
                                        if (dragOverId === s.id) setDragOverId(null);
                                    }}
                                    onDrop={() => {
                                        if (draggingId && draggingId !== s.id) {
                                            handleReorder(draggingId, s.id);
                                        }
                                        setDraggingId(null);
                                        setDragOverId(null);
                                    }}
                                    onDragEnd={() => {
                                        setDraggingId(null);
                                        setDragOverId(null);
                                    }}
                                />
                            ))}
                            {/* Staged (not-yet-saved) substeps. Render at
                                the bottom, in creation order. Dragging is
                                disabled for these rows — engineer can save
                                first, then reorder. */}
                            {pendingCreates.map((draft) => (
                                <PendingCreateRow
                                    key={draft.tempId}
                                    draft={draft}
                                    expanded={expandedId === draft.tempId}
                                    editable={isEditable}
                                    onToggle={() =>
                                        setExpandedId(
                                            expandedId === draft.tempId ? null : draft.tempId,
                                        )
                                    }
                                    onChange={(patch) =>
                                        updatePendingCreate(draft.tempId, patch)
                                    }
                                    onRemove={() => removePendingCreate(draft.tempId)}
                                />
                            ))}
                            {isEditable && (
                                <div className="flex gap-2">
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="flex-1 justify-start text-muted-foreground"
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
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="flex-1 justify-start text-muted-foreground"
                                        onClick={handleAddInspection}
                                        disabled={create.isPending}
                                        title="Adds a substep with is_inspection_point=true and the minimum QualityReport capture set pre-seeded."
                                    >
                                        <ClipboardCheck className="mr-2 h-4 w-4" />
                                        Add inspection substep
                                    </Button>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </OperatorResponseContext.Provider>
        </SubstepAuthoringProvider>
    );
}

// ============================================================================
// SubstepRow — collapsed/expanded row
// ============================================================================

function SubstepRow({
    substep,
    expanded,
    pending,
    isPendingDelete,
    onTogglePendingDelete,
    isDragging,
    isDragOver,
    editable,
    onToggle,
    onPendingChange,
    onDragStart,
    onDragEnter,
    onDragLeaveRow,
    onDrop,
    onDragEnd,
}: {
    substep: Substep;
    expanded: boolean;
    pending: PendingEdits | undefined;
    isPendingDelete: boolean;
    onTogglePendingDelete: () => void;
    isDragging: boolean;
    isDragOver: boolean;
    editable: boolean;
    onToggle: () => void;
    onPendingChange: (patch: PendingEdits | null) => void;
    onDragStart: () => void;
    onDragEnter: () => void;
    onDragLeaveRow: () => void;
    onDrop: () => void;
    onDragEnd: () => void;
}) {
    const hasPending = pending !== undefined && Object.keys(pending).length > 0;

    // Display values: show pending edits when present, fall back to backend.
    const displayTitle = pending?.title ?? substep.title;
    const displayOptional = pending?.is_optional ?? substep.is_optional;
    const displaySignature = pending?.requires_signature ?? substep.requires_signature;
    const displayInspection =
        pending?.is_inspection_point ?? substep.is_inspection_point;

    return (
        <div
            draggable={editable}
            onDragStart={(e) => {
                // Required for the drag to actually start in some browsers; the
                // payload itself goes via React state, not dataTransfer.
                e.dataTransfer.setData("text/plain", substep.id);
                e.dataTransfer.effectAllowed = "move";
                onDragStart();
            }}
            onDragOver={(e) => {
                // Must preventDefault to enable a drop target.
                e.preventDefault();
                e.dataTransfer.dropEffect = "move";
            }}
            onDragEnter={onDragEnter}
            onDragLeave={onDragLeaveRow}
            onDrop={(e) => {
                e.preventDefault();
                onDrop();
            }}
            onDragEnd={onDragEnd}
            className={`rounded-md border bg-card transition ${
                isDragging ? "opacity-40" : ""
            } ${isDragOver ? "ring-2 ring-primary" : ""} ${
                isPendingDelete ? "border-destructive/60 bg-destructive/5" : ""
            }`}
        >
            <button
                type="button"
                onClick={onToggle}
                className="flex w-full items-center gap-3 px-3 py-2.5 text-left hover:bg-muted/50"
            >
                <GripVertical className="h-4 w-4 shrink-0 cursor-grab text-muted-foreground" />
                <span className="w-6 shrink-0 text-sm font-medium text-muted-foreground tabular-nums">
                    {substep.order}.
                </span>
                <span
                    className={
                        "flex-1 text-sm font-medium " +
                        (isPendingDelete ? "text-muted-foreground line-through" : "")
                    }
                >
                    {displayTitle || (
                        <span className="text-muted-foreground italic">Untitled</span>
                    )}
                </span>
                {isPendingDelete && (
                    <Badge variant="outline" className="border-destructive/60 text-[10px] text-destructive">
                        Will delete on save
                    </Badge>
                )}
                {hasPending && !isPendingDelete && (
                    <Badge variant="outline" className="border-amber-500/60 text-[10px] text-amber-600">
                        Unsaved
                    </Badge>
                )}
                {!displayOptional && (
                    <Badge variant="secondary" className="text-[10px]">
                        Required
                    </Badge>
                )}
                {displayOptional && (
                    <Badge variant="outline" className="text-[10px]">
                        Optional
                    </Badge>
                )}
                {displaySignature && (
                    <Badge variant="outline" className="text-[10px]">
                        <PenLine className="mr-1 h-3 w-3" /> Sign-off
                    </Badge>
                )}
                {displayInspection && (
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
            {expanded && (
                <SubstepExpandedBody
                    substep={substep}
                    pending={pending}
                    editable={editable}
                    isPendingDelete={isPendingDelete}
                    onTogglePendingDelete={onTogglePendingDelete}
                    onPendingChange={onPendingChange}
                />
            )}
        </div>
    );
}

// ============================================================================
// SubstepExpandedBody — editor + meta controls + Save Draft / Discard
// ============================================================================

function SubstepExpandedBody({
    substep,
    pending,
    editable,
    isPendingDelete,
    onTogglePendingDelete,
    onPendingChange,
}: {
    substep: Substep;
    pending: PendingEdits | undefined;
    editable: boolean;
    isPendingDelete: boolean;
    onTogglePendingDelete: () => void;
    onPendingChange: (patch: PendingEdits | null) => void;
}) {

    // Working copies (show backend value when no pending edit is present).
    const workingTitle = pending?.title ?? substep.title;
    const workingOptional = pending?.is_optional ?? substep.is_optional;
    const workingSignature = pending?.requires_signature ?? substep.requires_signature;
    const workingInspection =
        pending?.is_inspection_point ?? substep.is_inspection_point;
    const workingCritical =
        pending?.is_critical ?? (substep.is_critical ?? false);
    const workingAllowNa =
        pending?.allow_not_applicable ?? (substep.allow_not_applicable ?? false);
    const workingBody =
        (pending?.body_blocks as object | undefined) ??
        ((substep.body_blocks as unknown as object) ?? { type: "doc", content: [] });

    const hasPending = pending !== undefined && Object.keys(pending).length > 0;

    /** Merge a partial patch into the pending state, normalizing away values
     * that have reverted to match the backend (so the row stops being marked
     * "unsaved" when the user undoes their edits). */
    const mergePending = useCallback(
        (partial: PendingEdits) => {
            const merged: PendingEdits = { ...(pending ?? {}), ...partial };
            // Strip keys whose value equals the backend value — they're no
            // longer pending changes.
            const cleaned: PendingEdits = {};
            (
                Object.keys(merged) as (keyof PendingEdits)[]
            ).forEach((k) => {
                const backendValue =
                    k === "body_blocks"
                        ? (substep.body_blocks as unknown)
                        : (substep[k as keyof Substep] as unknown);
                if (!_deepEqual(merged[k], backendValue)) {
                    (cleaned as Record<string, unknown>)[k] = merged[k];
                }
            });
            if (Object.keys(cleaned).length === 0) {
                onPendingChange(null);
            } else {
                onPendingChange(cleaned);
            }
        },
        [pending, substep, onPendingChange],
    );

    /** Toggle the row's pending-delete flag. No backend call here — the
     *  page commits the delete on Save Draft along with all other edits. */
    const handleToggleDelete = () => {
        if (!isPendingDelete) {
            // Marking for delete — drop any pending edits since they're
            // about to be moot. Reversible (re-clicking restores nothing
            // but the edit state was already lost on this confirmation).
            if (pending && Object.keys(pending).length > 0) {
                onPendingChange(null);
            }
        }
        onTogglePendingDelete();
    };

    return (
        <div className="space-y-3 border-t bg-muted/10 p-3">
            {/* Meta controls + save bar */}
            <div className="flex flex-wrap items-center gap-3 rounded-md border bg-background p-2 text-sm">
                <div className="flex flex-1 items-center gap-2">
                    <Label htmlFor={`title-${substep.id}`} className="text-xs">
                        Title
                    </Label>
                    <Input
                        id={`title-${substep.id}`}
                        value={workingTitle}
                        onChange={(e) => mergePending({ title: e.target.value })}
                        disabled={!editable}
                        className="h-8 text-sm"
                    />
                </div>

                <div className="flex items-center gap-2">
                    <Switch
                        id={`optional-${substep.id}`}
                        checked={workingOptional}
                        disabled={!editable}
                        onCheckedChange={(v) => mergePending({ is_optional: v })}
                    />
                    <Label htmlFor={`optional-${substep.id}`} className="text-xs">
                        Optional
                    </Label>
                </div>

                <div className="flex items-center gap-2">
                    <Switch
                        id={`signature-${substep.id}`}
                        checked={workingSignature}
                        disabled={!editable}
                        onCheckedChange={(v) => mergePending({ requires_signature: v })}
                    />
                    <Label htmlFor={`signature-${substep.id}`} className="text-xs">
                        Sign-off
                    </Label>
                </div>

                <div className="flex items-center gap-2">
                    <Switch
                        id={`inspection-${substep.id}`}
                        checked={workingInspection}
                        disabled={!editable}
                        onCheckedChange={(v) => mergePending({ is_inspection_point: v })}
                    />
                    <Label
                        htmlFor={`inspection-${substep.id}`}
                        className="text-xs"
                        title="When set, MeasurementInput captures in this substep create binding inspection records (auto-quarantine on out-of-spec, NCR notification). Default off."
                    >
                        Inspection point
                    </Label>
                </div>

                <div className="flex items-center gap-2">
                    <Switch
                        id={`critical-${substep.id}`}
                        checked={workingCritical}
                        disabled={!editable}
                        onCheckedChange={(v) => {
                            // is_critical=True overrides allow_not_applicable.
                            // Clear the N/A flag so the operator can't see a
                            // contradictory UI state.
                            const patch: PendingEdits = { is_critical: v };
                            if (v) patch.allow_not_applicable = false;
                            mergePending(patch);
                        }}
                    />
                    <Label
                        htmlFor={`critical-${substep.id}`}
                        className="text-xs"
                        title="Safety-critical: this substep can never be marked N/A. Use for torque on safety-critical fasteners, witnessed sign-offs, final dimensional verification."
                    >
                        Critical
                    </Label>
                </div>

                <div className="flex items-center gap-2">
                    <Switch
                        id={`allow-na-${substep.id}`}
                        checked={workingAllowNa}
                        disabled={!editable || workingCritical}
                        onCheckedChange={(v) => mergePending({ allow_not_applicable: v })}
                    />
                    <Label
                        htmlFor={`allow-na-${substep.id}`}
                        className={
                            "text-xs " +
                            (workingCritical ? "text-muted-foreground line-through" : "")
                        }
                        title={
                            workingCritical
                                ? "Disabled: critical substeps cannot be marked N/A."
                                : "When set, an operator may mark this substep N/A with a reason code instead of completing it."
                        }
                    >
                        Allow N/A
                    </Label>
                </div>

                <Button
                    variant={isPendingDelete ? "outline" : "ghost"}
                    size="sm"
                    onClick={handleToggleDelete}
                    disabled={!editable}
                    className={
                        isPendingDelete
                            ? "border-destructive/60 text-destructive hover:bg-destructive/10"
                            : "text-destructive hover:bg-destructive/10 hover:text-destructive"
                    }
                    title={
                        editable
                            ? isPendingDelete
                                ? "Undo delete (still pending save)"
                                : "Mark for deletion (commits on Save draft)"
                            : "Locked — Process not in DRAFT"
                    }
                >
                    <Trash2 className="h-4 w-4" />
                </Button>
            </div>

            {/* The editor (engineer + operator preview side by side).
                NOTE: SubstepEditor's onChange fires every time the editor
                content changes — we route those into pending state instead
                of straight to the backend. */}
            <SubstepEditor
                key={substep.id /* remount on substep change */}
                body={workingBody}
                editable={editable && !isPendingDelete}
                onChange={(next) => mergePending({ body_blocks: next })}
            />

            {/* This row's saved/unsaved status — actual save lives in the
                page header so one click persists everything as a single
                logical draft commit (matches authoring compliance model). */}
            <div className="flex items-center justify-end rounded-md border bg-background px-2 py-1 text-xs">
                <span
                    className={
                        isPendingDelete
                            ? "text-destructive"
                            : hasPending
                              ? "text-amber-600"
                              : "text-muted-foreground"
                    }
                >
                    {isPendingDelete
                        ? "Marked for deletion — Save draft in header to commit"
                        : hasPending
                          ? "Unsaved changes — Save draft in header"
                          : "Saved"}
                </span>
            </div>
        </div>
    );
}

// ============================================================================
// PendingCreateRow — staged (not-yet-saved) new substep
// ============================================================================

/**
 * Renders a substep that exists only in client state (not on the backend).
 * Visually similar to SubstepRow but every change is applied directly to
 * the PendingCreate entry; nothing is PATCHed. On save the parent posts the
 * draft and this row collapses (replaced by the resulting real Substep).
 */
function PendingCreateRow({
    draft,
    expanded,
    editable,
    onToggle,
    onChange,
    onRemove,
}: {
    draft: PendingCreate;
    expanded: boolean;
    editable: boolean;
    onToggle: () => void;
    onChange: (patch: Partial<PendingCreate>) => void;
    onRemove: () => void;
}) {
    return (
        <div className="rounded-md border border-dashed border-emerald-500/50 bg-emerald-500/5">
            <button
                type="button"
                onClick={onToggle}
                className="flex w-full items-center gap-3 px-3 py-2.5 text-left hover:bg-emerald-500/10"
            >
                <GripVertical className="h-4 w-4 shrink-0 cursor-not-allowed text-muted-foreground/40" />
                <span className="w-6 shrink-0 text-sm font-medium text-muted-foreground tabular-nums">
                    {draft.order}.
                </span>
                <span className="flex-1 text-sm font-medium">
                    {draft.title || (
                        <span className="text-muted-foreground italic">Untitled</span>
                    )}
                </span>
                <Badge variant="outline" className="border-emerald-500/60 text-[10px] text-emerald-700">
                    New — unsaved
                </Badge>
                {!draft.is_optional && (
                    <Badge variant="secondary" className="text-[10px]">
                        Required
                    </Badge>
                )}
                {draft.is_optional && (
                    <Badge variant="outline" className="text-[10px]">
                        Optional
                    </Badge>
                )}
                {draft.requires_signature && (
                    <Badge variant="outline" className="text-[10px]">
                        <PenLine className="mr-1 h-3 w-3" /> Sign-off
                    </Badge>
                )}
                {draft.is_inspection_point && (
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
            {expanded && (
                <div className="space-y-3 border-t bg-muted/10 p-3">
                    <div className="flex flex-wrap items-center gap-3 rounded-md border bg-background p-2 text-sm">
                        <div className="flex flex-1 items-center gap-2">
                            <Label htmlFor={`title-${draft.tempId}`} className="text-xs">
                                Title
                            </Label>
                            <Input
                                id={`title-${draft.tempId}`}
                                value={draft.title}
                                onChange={(e) => onChange({ title: e.target.value })}
                                disabled={!editable}
                                className="h-8 text-sm"
                            />
                        </div>
                        <div className="flex items-center gap-2">
                            <Switch
                                id={`optional-${draft.tempId}`}
                                checked={draft.is_optional}
                                disabled={!editable}
                                onCheckedChange={(v) => onChange({ is_optional: v })}
                            />
                            <Label htmlFor={`optional-${draft.tempId}`} className="text-xs">
                                Optional
                            </Label>
                        </div>
                        <div className="flex items-center gap-2">
                            <Switch
                                id={`signature-${draft.tempId}`}
                                checked={draft.requires_signature}
                                disabled={!editable}
                                onCheckedChange={(v) => onChange({ requires_signature: v })}
                            />
                            <Label htmlFor={`signature-${draft.tempId}`} className="text-xs">
                                Sign-off
                            </Label>
                        </div>
                        <div className="flex items-center gap-2">
                            <Switch
                                id={`inspection-${draft.tempId}`}
                                checked={draft.is_inspection_point}
                                disabled={!editable}
                                onCheckedChange={(v) => onChange({ is_inspection_point: v })}
                            />
                            <Label htmlFor={`inspection-${draft.tempId}`} className="text-xs">
                                Inspection point
                            </Label>
                        </div>
                        <div className="flex items-center gap-2">
                            <Switch
                                id={`critical-${draft.tempId}`}
                                checked={draft.is_critical}
                                disabled={!editable}
                                onCheckedChange={(v) => {
                                    const patch: Partial<PendingCreate> = { is_critical: v };
                                    if (v) patch.allow_not_applicable = false;
                                    onChange(patch);
                                }}
                            />
                            <Label htmlFor={`critical-${draft.tempId}`} className="text-xs">
                                Critical
                            </Label>
                        </div>
                        <div className="flex items-center gap-2">
                            <Switch
                                id={`allow-na-${draft.tempId}`}
                                checked={draft.allow_not_applicable}
                                disabled={!editable || draft.is_critical}
                                onCheckedChange={(v) => onChange({ allow_not_applicable: v })}
                            />
                            <Label
                                htmlFor={`allow-na-${draft.tempId}`}
                                className={
                                    "text-xs " +
                                    (draft.is_critical ? "text-muted-foreground line-through" : "")
                                }
                            >
                                Allow N/A
                            </Label>
                        </div>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={onRemove}
                            disabled={!editable}
                            className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                            title="Discard this unsaved substep"
                        >
                            <Trash2 className="h-4 w-4" />
                        </Button>
                    </div>

                    <SubstepEditor
                        key={draft.tempId}
                        body={draft.body_blocks}
                        editable={editable}
                        onChange={(next) => onChange({ body_blocks: next as object })}
                    />

                    <div className="flex items-center justify-end rounded-md border bg-background px-2 py-1 text-xs">
                        <span className="text-emerald-700">
                            New — will be created on Save draft
                        </span>
                    </div>
                </div>
            )}
        </div>
    );
}

/** Conservative deep-equality good enough for body_blocks JSON + primitives.
 * Uses JSON.stringify which is fine for our shape (no Date / Map / undefined
 * fields that the encoder would drop). */
function _deepEqual(a: unknown, b: unknown): boolean {
    if (a === b) return true;
    if (typeof a !== typeof b) return false;
    try {
        return JSON.stringify(a) === JSON.stringify(b);
    } catch {
        return false;
    }
}

export default SubstepEditorPage;
