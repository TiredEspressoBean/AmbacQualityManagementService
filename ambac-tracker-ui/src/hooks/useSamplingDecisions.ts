/**
 * SamplingDecisions — live decisions per (StepExecution, Substep).
 *
 * The advancement gate's contract: each substep gets a persisted
 * SamplingDecision row written when a part enters the step. The
 * operator runtime reads these to know which substeps are SELECTED
 * (operator must complete), DESELECTED (rule excluded this part —
 * "not in sample"), or PENDING (cohort-close needed).
 *
 * Decisions are append-only; superseded rows are hidden by default
 * and surface only via `include_superseded=1`.
 */

import { queryOptions, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export type SamplingOutcome = "selected" | "deselected" | "pending";

export type SamplingDecisionRow = {
    id: string;
    step_execution: string;
    substep: string;
    outcome: SamplingOutcome;
    ruleset_version: number;
    decided_at: string;
    superseded_by: string | null;
};

type ListResponse = { results?: SamplingDecisionRow[] };

export const samplingDecisionKeys = {
    all: ["samplingDecisions"] as const,
    forExecution: (stepExecutionId: string) =>
        ["samplingDecisions", "step_execution", stepExecutionId] as const,
};

export function samplingDecisionsForExecutionOptions(stepExecutionId: string) {
    return queryOptions({
        queryKey: samplingDecisionKeys.forExecution(stepExecutionId),
        queryFn: () =>
            api.api_SamplingDecisions_list({
                queries: { step_execution: stepExecutionId } as never,
            }) as Promise<ListResponse>,
        enabled: !!stepExecutionId,
        staleTime: 30_000,
    });
}

export function useSamplingDecisionsForExecution(stepExecutionId: string) {
    return useQuery(samplingDecisionsForExecutionOptions(stepExecutionId));
}

/** Build a `substep_id → outcome` map for fast lookup in the runtime. */
export function buildOutcomeMap(
    rows: SamplingDecisionRow[] | undefined,
): Record<string, SamplingOutcome> {
    const map: Record<string, SamplingOutcome> = {};
    if (!rows) return map;
    for (const r of rows) {
        if (r.superseded_by) continue;
        map[String(r.substep)] = r.outcome;
    }
    return map;
}
