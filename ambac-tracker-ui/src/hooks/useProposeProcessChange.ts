import { useMutation, useQueryClient } from "@tanstack/react-query";
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
 *
 * Raw fetch (not Zodios) because the Zodios body schema is auto-inferred
 * from the ProcessChangeRequest serializer and rejects the simplified
 * `{target_process_id}` payload.
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

type Response = {
    pcr_id: string;
    draft_process_id: string;
    artifact_number: string;
};

export function useProposeProcessChange() {
    const queryClient = useQueryClient();
    return useMutation<Response, Error, Variables>({
        mutationFn: async (vars) => {
            const r = await fetch("/api/process-change-requests/propose/", {
                method: "POST",
                credentials: "include",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCookie("csrftoken") ?? "",
                },
                body: JSON.stringify({
                    target_process_id: vars.targetProcessId,
                    title: vars.title ?? "",
                    proposed_change: vars.proposedChange ?? "",
                    justification: vars.justification ?? "",
                    risk_analysis: vars.riskAnalysis ?? "",
                    priority: vars.priority ?? "NORMAL",
                    customer_notification_required: vars.customerNotificationRequired ?? false,
                }),
            });
            if (r.status === 201) return (await r.json()) as Response;
            const text = await r.text().catch(() => "");
            throw new Error(text || `HTTP ${r.status}`);
        },
        onSuccess: () => {
            // New PCR + new DRAFT process — invalidate both lists.
            queryClient.invalidateQueries({ queryKey: ["process-change-requests"] });
            queryClient.invalidateQueries({ queryKey: ["processes"] });
            queryClient.invalidateQueries({ queryKey: ["processesWithSteps"] });
        },
    });
}
