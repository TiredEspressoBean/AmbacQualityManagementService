import { useQuery, queryOptions, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { components, operations } from "@/lib/api/generated-types";
import type { Schema } from "@/lib/api/types";

type SubstepsListQueries = NonNullable<operations["api_Substeps_list"]["parameters"]["query"]>;
type SubstepsListResponse = components["schemas"]["PaginatedSubstepList"];
type Substep = Schema<"Substep">;
type SubstepRequest = Schema<"SubstepRequest">;
type PatchedSubstepRequest = Schema<"PatchedSubstepRequest">;

const QK_BASE = "substeps";

export const substepsOptions = (queries?: SubstepsListQueries) =>
    queryOptions({
        queryKey: [QK_BASE, "list", queries] as const,
        queryFn: () =>
            api.api_Substeps_list(
                (queries ? { queries } : undefined) as never,
            ) as Promise<SubstepsListResponse>,
    });

/** List substeps. Pass `{ step: <step_id> }` to fetch substeps for a step. */
export function useSubsteps(queries?: SubstepsListQueries) {
    return useQuery(substepsOptions(queries));
}

/** Single substep by id. */
export function useSubstep(id: string | null | undefined) {
    return useQuery({
        queryKey: [QK_BASE, "detail", id] as const,
        queryFn: () =>
            api.api_Substeps_retrieve({ params: { id: String(id) } } as never) as Promise<Substep>,
        enabled: Boolean(id),
    });
}

export function useCreateSubstep() {
    const qc = useQueryClient();
    return useMutation<Substep, unknown, SubstepRequest>({
        mutationFn: (data) =>
            api.api_Substeps_create(data as never, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<Substep>,
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: [QK_BASE] });
        },
    });
}

/** Partial update — used by the editor for autosave of body_blocks etc. */
export function useUpdateSubstep() {
    const qc = useQueryClient();
    return useMutation<
        Substep,
        unknown,
        { id: string; data: PatchedSubstepRequest }
    >({
        mutationFn: ({ id, data }) =>
            api.api_Substeps_partial_update(data as never, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<Substep>,
        onSuccess: (substep) => {
            qc.invalidateQueries({ queryKey: [QK_BASE] });
            qc.setQueryData([QK_BASE, "detail", substep.id], substep);
        },
    });
}

/** Atomic reorder. Body: `{ step, order: [substep_id, ...] }`. Backend runs
 *  a two-phase update inside a transaction to dodge the `(step, order)`
 *  unique constraint, so the client just sends the intended final ordering. */
export function useReorderSubsteps() {
    const qc = useQueryClient();
    return useMutation<void, unknown, { step: string; order: string[] }>({
        mutationFn: (body) =>
            api.api_Substeps_reorder_create(body as never, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<void>,
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: [QK_BASE] });
        },
    });
}

/** Operator-runtime submit: posts every capture for a substep + closes
 *  with a SubstepCompletion. Body shape lives in the backend service
 *  module `Tracker/services/dwi/operator_capture.py`. */
export type OperatorCapture = Record<string, unknown> & {
    node_id: string;
    kind: string;
};
export type SubmitSubstepRequest = {
    /** Exactly one of step_execution / batch_execution — per-part vs
     *  once-per-lot batch capture (3a). The backend rejects both/neither. */
    step_execution?: string;
    batch_execution?: string;
    captures: OperatorCapture[];
    notes?: string;
    signature_data?: string;
    signature_meaning?: string;
    verification_method?: string;
    marked_not_applicable?: boolean;
    na_reason_code?: string;
};
export type SubmitSubstepResponse = {
    completion_id: string;
    response_count: number;
    quality_report_id: string | null;
    measurement_count: number;
};

export function useSubmitSubstep() {
    const qc = useQueryClient();
    return useMutation<
        SubmitSubstepResponse,
        unknown,
        { id: string; data: SubmitSubstepRequest }
    >({
        mutationFn: ({ id, data }) =>
            api.api_Substeps_submit_create(data as never, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<SubmitSubstepResponse>,
        onSuccess: () => {
            // Invalidate substep + completion queries so badges and
            // operator-side counters refresh.
            qc.invalidateQueries({ queryKey: [QK_BASE] });
        },
    });
}

export function useDeleteSubstep() {
    const qc = useQueryClient();
    return useMutation<void, unknown, string>({
        mutationFn: (id) =>
            api.api_Substeps_destroy(undefined as never, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<void>,
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: [QK_BASE] });
        },
    });
}

export type { Substep, SubstepRequest, PatchedSubstepRequest };
