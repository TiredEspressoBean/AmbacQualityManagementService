/**
 * BatchExecution hooks — read/create/seal.
 *
 * The seal action is the public state-changing surface. Read endpoints
 * are used by the operator BatchPanel to discover existing batches for
 * a (WorkOrder, Step) so a second operator doesn't accidentally start
 * a parallel batch.
 */

import {
    queryOptions,
    useMutation,
    useQuery,
    useQueryClient,
    type QueryClient,
} from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

const csrfHeaders = () => ({ "X-CSRFToken": getCookie("csrftoken") ?? "" });

// Derived from the client rather than restated. The hand-written copy here
// had `started_by?: string` where the serializer sends a numeric user pk, and
// nothing caught it because every call site was cast.
export type BatchExecutionRow = Awaited<
    ReturnType<typeof api.api_BatchExecutions_create>
>;

export const batchKeys = {
    all: ["batchExecutions"] as const,
    forWoStep: (workOrderId: string, stepId: string) =>
        ["batchExecutions", "wo-step", workOrderId, stepId] as const,
};

export function batchesForWoStepOptions(workOrderId: string, stepId: string) {
    return queryOptions({
        queryKey: batchKeys.forWoStep(workOrderId, stepId),
        queryFn: () =>
            api.api_BatchExecutions_list({
                queries: { work_order: workOrderId, step: stepId },
            }),
        enabled: !!workOrderId && !!stepId,
        staleTime: 15_000,
    });
}

export function useBatchesForWoStep(workOrderId: string, stepId: string) {
    return useQuery(batchesForWoStepOptions(workOrderId, stepId));
}

/** Refresh every batch list — after anything that changes a load's phase (confirming
 *  the substep that seals it, say). */
export const invalidateBatches = (qc: QueryClient) =>
    qc.invalidateQueries({
        predicate: (q) => q.queryKey[0] === batchKeys.all[0],
    });

type CreateBatchInput = {
    work_order: string;
    step: string;
    parts: string[];
    notes?: string;
};

export function useCreateBatchExecution() {
    const qc = useQueryClient();
    return useMutation<BatchExecutionRow, unknown, CreateBatchInput>({
        mutationFn: (data) =>
            api.api_BatchExecutions_create(data, { headers: csrfHeaders() }),
        onSuccess: () => invalidateBatches(qc),
        meta: {
            errorMessage: "Couldn't start batch",
            successMessage: "Batch started",
        },
    });
}

type SealResult = { batch_id: string; sealed_at: string };

export function useSealBatchExecution() {
    const qc = useQueryClient();
    return useMutation<SealResult, unknown, { id: string }>({
        mutationFn: ({ id }) =>
            api.api_BatchExecutions_seal_create(undefined, {
                params: { id },
                headers: csrfHeaders(),
            }) as Promise<SealResult>,
        onSuccess: () => invalidateBatches(qc),
        // The panel says why a seal was refused (the missing loading checks).
        meta: {
            suppressGlobalError: true,
            successMessage: "Load sealed: the machine runs",
        },
    });
}

type CompleteResult = { batch_id: string; completed_at: string };

/** Complete a sealed load: its run is finished and its completion checks done. This
 *  is where the load's parts advance. */
export function useCompleteBatchExecution() {
    const qc = useQueryClient();
    return useMutation<CompleteResult, unknown, { id: string }>({
        mutationFn: ({ id }) =>
            api.api_BatchExecutions_complete_create(undefined, {
                params: { id },
                headers: csrfHeaders(),
            }) as Promise<CompleteResult>,
        onSuccess: () => {
            invalidateBatches(qc);
            // Advancement moved the parts; refresh parts and open work too.
            qc.invalidateQueries({
                predicate: (q) => q.queryKey[0] === "parts" || q.queryKey[0] === "step-executions",
            });
        },
        // The panel says why a completion was refused (the missing checks).
        meta: {
            suppressGlobalError: true,
            successMessage: "Load complete: its parts move on",
        },
    });
}

/** Put forgotten pieces into a load, until the parts' step is completed. No reason. */
export function useAddBatchParts() {
    const qc = useQueryClient();
    return useMutation<unknown, unknown, { id: string; parts: string[] }>({
        mutationFn: ({ id, parts }) =>
            api.api_BatchExecutions_add_parts_create({ parts }, {
                params: { id },
                headers: csrfHeaders(),
            }),
        onSuccess: () => invalidateBatches(qc),
        // The panel says why an add was refused.
        meta: { suppressGlobalError: true, successMessage: "Added to the load" },
    });
}

/** Take a piece out of a load. While its step is still being worked it just comes out. */
export function useRemoveBatchPart() {
    const qc = useQueryClient();
    return useMutation<unknown, unknown, { id: string; part: string }>({
        mutationFn: ({ id, part }) =>
            api.api_BatchExecutions_remove_part_create({ part, reason: "" }, {
                params: { id },
                headers: csrfHeaders(),
            }),
        onSuccess: () => invalidateBatches(qc),
        meta: { suppressGlobalError: true, successMessage: "Taken out of the load" },
    });
}

/** Abandon a load started by mistake, while it's still loading: its parts go back to
 *  the step unloaded. */
export function useDiscardBatch() {
    const qc = useQueryClient();
    return useMutation<unknown, unknown, { id: string }>({
        mutationFn: ({ id }) =>
            api.api_BatchExecutions_discard_create({}, { params: { id }, headers: csrfHeaders() }),
        onSuccess: () => {
            invalidateBatches(qc);
            // Gone from Resume / Continue work at once.
            qc.invalidateQueries({ predicate: (q) => q.queryKey[0] === "step-executions" });
        },
        meta: { suppressGlobalError: true, successMessage: "Load discarded: its parts are back at the step" },
    });
}
