import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

/**
 * Propose a process change — fork a DRAFT version + create a linked PCR row.
 *
 * Backend: `POST /api/process-change-requests/propose/` with body
 * `{ target_process_id }` (plus optional PCR fields). Returns
 * `{ pcr_id, draft_process_id, artifact_number }`.
 *
 * Used by the "Propose Change" action on `ProcessFlowPage`. After
 * success, navigate to the DRAFT's editor URL — the engineer edits the
 * DRAFT and submits the PCR with the diff attached.
 */
type Variables = {
    targetProcessId: string;
    title?: string;
    proposedChange?: string;
    justification?: string;
    riskAnalysis?: string;
    priority?: "LOW" | "NORMAL" | "HIGH" | "CRITICAL";
    customerNotificationRequired?: boolean;
};

// Invalidation-only helpers (not real queryOptions — no queryFn needed).
const processChangeRequestsKeyOptions = () => ({ queryKey: ["process-change-requests"] as const });
const processesKeyOptions = () => ({ queryKey: ["processes"] as const });
const processesWithStepsKeyOptions = () => ({ queryKey: ["processesWithSteps"] as const });

export function useProposeProcessChange() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (vars: Variables) =>
            api.api_process_change_requests_propose_create(
                {
                    target_process_id: vars.targetProcessId,
                    title: vars.title ?? "",
                    proposed_change: vars.proposedChange ?? "",
                    justification: vars.justification ?? "",
                    risk_analysis: vars.riskAnalysis ?? "",
                    priority: vars.priority ?? "NORMAL",
                    customer_notification_required: vars.customerNotificationRequired ?? false,
                },
                { headers: { "X-CSRFToken": getCookie("csrftoken") ?? "" } },
            ),
        onSuccess: () => {
            // New PCR + new DRAFT process — invalidate both lists.
            queryClient.invalidateQueries(processChangeRequestsKeyOptions());
            queryClient.invalidateQueries(processesKeyOptions());
            queryClient.invalidateQueries(processesWithStepsKeyOptions());
        },
    });
}
