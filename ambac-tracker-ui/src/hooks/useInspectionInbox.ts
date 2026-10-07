/** The QA inspector's task inbox — one flat list across every inspection
 *  source (FPI / receiving / OSP / in-process). Standard list-of-rows
 *  contract (the useIncomingInspection pattern); derive type-count chips
 *  from the rows. See services.qms.inspection_inbox for tone rules. */
import { useMutation, useQuery, useQueryClient, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { components } from "@/lib/api/generated-types";

export type InspectionInboxRow = components["schemas"]["InspectionInboxRow"];

export const inspectionInboxOptions = () =>
    queryOptions({
        queryKey: ["inspectionInbox"] as const,
        queryFn: () => api.api_InspectionInbox_list() as Promise<InspectionInboxRow[]>,
        staleTime: 15_000,
    });

export function useInspectionInbox() {
    return useQuery(inspectionInboxOptions());
}

export type PendingQaSignoff = components["schemas"]["PendingQaSignoff"];

/** QA-gated steps whose submitted work waits for a sign-off — for one work order,
 *  or all of them. */
export const qaSignoffsOptions = (workOrderId?: string) =>
    queryOptions({
        queryKey: ["inspectionInbox", "qaSignoffs", workOrderId ?? "all"] as const,
        queryFn: () => api.api_InspectionInbox_qa_signoffs_list(
            workOrderId ? { queries: { work_order: workOrderId } } : undefined,
        ) as Promise<PendingQaSignoff[]>,
        staleTime: 15_000,
    });

export function useQaSignoffs(workOrderId?: string) {
    return useQuery({ ...qaSignoffsOptions(workOrderId), enabled: workOrderId !== "" });
}

/** Sign off a QA-gated step for a work order; the units then advance. */
export function useSignOffStep() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (vars: { work_order: string; step: string }) =>
            api.api_InspectionInbox_sign_off_step_create(vars),
        // The dialog shows the server's reason (e.g. segregation of duties) itself.
        meta: { suppressGlobalError: true },
        onSuccess: () => {
            void qc.invalidateQueries({ queryKey: inspectionInboxOptions().queryKey });
            void qc.invalidateQueries({ predicate: (q) => q.queryKey[0] === "workOrder" || q.queryKey[0] === "parts" });
        },
    });
}

