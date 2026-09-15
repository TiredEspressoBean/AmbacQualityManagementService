/**
 * The substep completions recorded behind one traveler row, with QA's void
 * affordance on each.
 *
 * A traveler row is per-step, not per-visit — rework means several
 * StepExecutions collapse into one row — so this takes the row's
 * `step_execution_ids` and fetches across all of them in a single
 * `step_execution__in` query. Completions are grouped by execution so QA can
 * tell the attempts apart: voiding the wrong visit's completion would retract
 * the wrong person's work.
 *
 * Voided rows stay listed rather than disappearing. The void is an audit
 * record, and a reader needs to see that the work was retracted and why — a
 * list that silently dropped them would read as if the completion never
 * happened.
 */

import { useState } from "react";
import { queryOptions, useQuery } from "@tanstack/react-query";
import { Ban, Loader2 } from "lucide-react";
import { api } from "@/lib/api/generated";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { VoidCompletionDialog } from "@/components/dwi/VoidCompletionDialog";
import { usePermissionSet } from "@/hooks/useMyPermissions";

type CompletionRow = Awaited<
    ReturnType<typeof api.api_SubstepCompletions_list>
>["results"][number];

/** `substepCompletions` root so VoidCompletionDialog's invalidation reaches
 *  these lists — it matches on `queryKey[0]`. */
export const stepCompletionsOptions = (stepExecutionIds: string[]) =>
    queryOptions({
        queryKey: ["substepCompletions", { stepExecutionIds }] as const,
        queryFn: () =>
            api.api_SubstepCompletions_list({
                queries: { step_execution__in: stepExecutionIds },
            }),
    });

export const batchCompletionsOptions = (batchExecutionIds: string[]) =>
    queryOptions({
        queryKey: ["substepCompletions", { batchExecutionIds }] as const,
        queryFn: () =>
            api.api_SubstepCompletions_list({
                queries: { batch_execution__in: batchExecutionIds },
            }),
    });

/** Two queries rather than one: a completion binds to either a step_execution
 *  or a batch_execution, never both, and the filter backend ANDs its params —
 *  so a single call carrying both would match nothing. */
function useStepCompletions(stepExecutionIds: string[], batchExecutionIds: string[]) {
    const perPart = useQuery({
        ...stepCompletionsOptions(stepExecutionIds),
        // Only meaningful once the row has executions behind it; a step the
        // part hasn't reached has none, and `__in: []` would list the tenant.
        enabled: stepExecutionIds.length > 0,
    });
    const perBatch = useQuery({
        ...batchCompletionsOptions(batchExecutionIds),
        enabled: batchExecutionIds.length > 0,
    });
    return {
        rows: [...(perPart.data?.results ?? []), ...(perBatch.data?.results ?? [])],
        isLoading: perPart.isLoading || perBatch.isLoading,
        error: perPart.error ?? perBatch.error,
    };
}

function completionLabel(c: CompletionRow) {
    return c.substep_title ?? "Substep";
}

export function StepCompletionsList({
    stepExecutionIds,
    batchCycles,
    stepName,
}: {
    stepExecutionIds: string[];
    /** Cycles this part shared at this step, with how many parts rode each —
     *  the count is what tells the reader a void here reaches other parts. */
    batchCycles: { batch_id: string; part_count: number }[];
    stepName: string;
}) {
    const batchIds = batchCycles.map((b) => b.batch_id);
    const { rows, isLoading, error } = useStepCompletions(stepExecutionIds, batchIds);
    const partCountByBatch = new Map(batchCycles.map((b) => [b.batch_id, b.part_count]));
    const canVoid = usePermissionSet().has("void_substepcompletion");
    const [target, setTarget] = useState<CompletionRow | null>(null);

    if (isLoading) {
        return (
            <div className="flex items-center gap-2 px-3 py-2 text-xs text-muted-foreground">
                <Loader2 className="h-3 w-3 animate-spin" />
                Loading completions…
            </div>
        );
    }
    if (error) {
        return (
            <div className="px-3 py-2 text-xs text-destructive">
                Completions unavailable: {error.message}
            </div>
        );
    }

    if (rows.length === 0) {
        return (
            <div className="px-3 py-2 text-xs text-muted-foreground">
                No substep completions recorded at this step.
            </div>
        );
    }

    // Oldest execution first, matching the order the ids arrive in, so the
    // visit numbering below reads chronologically.
    const byExecution = stepExecutionIds
        .map((execId, i) => ({
            key: execId,
            // Only worth labelling the visit when there was more than one —
            // on the common single-visit step it's noise.
            label: stepExecutionIds.length > 1 ? `Visit #${i + 1}` : null,
            sharedWith: 0,
            completions: rows.filter((c) => c.step_execution === execId),
        }))
        .filter((g) => g.completions.length > 0);

    // Shared-cycle work is always labelled, even when it's the only group: the
    // reader has to know before voiding that this record belongs to the load
    // rather than to this part.
    const byBatch = batchCycles
        .map((b) => ({
            key: b.batch_id,
            label: "Shared cycle",
            sharedWith: partCountByBatch.get(b.batch_id) ?? 0,
            completions: rows.filter((c) => c.batch_execution === b.batch_id),
        }))
        .filter((g) => g.completions.length > 0);

    const groups = [...byExecution, ...byBatch];

    return (
        <div className="space-y-2 px-3 py-2">
            {groups.map((group) => (
                <div key={group.key} className="space-y-1">
                    {group.label && (
                        <div className="text-[10px] font-medium uppercase text-muted-foreground">
                            {group.label}
                            {group.sharedWith > 1 && (
                                <span className="ml-1 normal-case text-destructive">
                                    · shared by {group.sharedWith} parts — voiding
                                    affects all of them
                                </span>
                            )}
                        </div>
                    )}
                    {group.completions.map((c) => (
                        <div
                            key={c.id}
                            className="flex items-center justify-between gap-3 rounded border bg-background px-2 py-1.5"
                        >
                            <div className="min-w-0 flex-1 space-y-0.5">
                                <div className="flex items-center gap-2">
                                    <span
                                        className={
                                            c.is_voided
                                                ? "truncate text-xs text-muted-foreground line-through"
                                                : "truncate text-xs"
                                        }
                                    >
                                        {completionLabel(c)}
                                    </span>
                                    {c.marked_not_applicable && (
                                        <Badge variant="outline" className="text-[10px]">
                                            N/A
                                        </Badge>
                                    )}
                                    {c.is_voided && (
                                        <Badge variant="destructive" className="text-[10px]">
                                            Voided
                                        </Badge>
                                    )}
                                </div>
                                <div className="text-[10px] text-muted-foreground">
                                    {c.completed_by_name ?? "Unknown"}
                                    {c.completed_at
                                        ? ` · ${new Date(c.completed_at).toLocaleString()}`
                                        : ""}
                                </div>
                                {c.is_voided && (
                                    <div className="text-[10px] text-destructive">
                                        Voided by {c.voided_by_name ?? "unknown"}
                                        {c.voided_at
                                            ? ` on ${new Date(c.voided_at).toLocaleString()}`
                                            : ""}
                                        {c.void_reason ? ` — ${c.void_reason}` : ""}
                                    </div>
                                )}
                            </div>
                            {/* Voiding an already-voided row is a no-op the
                                backend would accept, so hide it rather than
                                offer a second reason that overwrites the
                                first. */}
                            {canVoid && !c.is_voided && (
                                <Button
                                    size="sm"
                                    variant="ghost"
                                    className="h-7 shrink-0 text-xs text-destructive hover:text-destructive"
                                    onClick={() => setTarget(c)}
                                >
                                    <Ban className="mr-1 h-3 w-3" />
                                    Void
                                </Button>
                            )}
                        </div>
                    ))}
                </div>
            ))}

            <VoidCompletionDialog
                completionId={target?.id ?? null}
                // The dialog warns about blocking "any part downstream". For a
                // shared cycle that's the whole load, so say so in the title —
                // the confirmation is the last place to learn the blast radius.
                completionTitle={
                    target
                        ? `${completionLabel(target)} · ${stepName}${
                              target.batch_execution
                                  ? ` · shared cycle, ${
                                        partCountByBatch.get(target.batch_execution) ?? 0
                                    } parts`
                                  : ""
                          }`
                        : undefined
                }
                open={target !== null}
                onClose={() => setTarget(null)}
            />
        </div>
    );
}
