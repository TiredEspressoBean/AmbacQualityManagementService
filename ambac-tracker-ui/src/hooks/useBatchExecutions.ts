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

const invalidateBatches = (qc: QueryClient) =>
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
            api.api_BatchExecutions_seal_create(undefined as never, {
                params: { id },
                headers: csrfHeaders(),
            }) as Promise<SealResult>,
        onSuccess: () => {
            invalidateBatches(qc);
            // Advancement may have moved parts; refresh parts/queries too.
            qc.invalidateQueries({
                predicate: (q) => q.queryKey[0] === "parts",
            });
        },
        meta: {
            errorMessage: "Couldn't seal batch",
            successMessage: "Batch sealed",
        },
    });
}
