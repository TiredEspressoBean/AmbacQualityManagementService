/** Scheduling setup data — the tables the solver and RCCP size operations from.
 *
 *  - StepTimings: a step's standard times (one row per step).
 *  - StepEquipmentAffinities: which machines can run a step, and how well.
 *  - WorkCenterChangeovers: minutes to switch a machine from one step to another,
 *    one row per (machine, from step, to step).
 *
 *  DELETE soft-archives on the backend; adding the same key again revives the row.
 */
import { useMutation, useQuery, useQueryClient, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import { getCookie } from "@/lib/utils";
import type { components, operations } from "@/lib/api/generated-types";

type S = components["schemas"];

export type StepTiming = S["StepTimingRecord"];
export type StepEquipmentAffinity = S["StepEquipmentAffinity"];
export type WorkCenterChangeover = S["WorkCenterChangeover"];

type StepTimingsQueries = NonNullable<operations["api_StepTimings_list"]["parameters"]["query"]>;
type AffinitiesQueries = NonNullable<operations["api_StepEquipmentAffinities_list"]["parameters"]["query"]>;
type ChangeoversQueries = NonNullable<operations["api_WorkCenterChangeovers_list"]["parameters"]["query"]>;

// Key roots. Each list and its detail share one, so a single predicate invalidates both.
export const STEP_TIMINGS_KEY = "step-timings";
export const STEP_AFFINITIES_KEY = "step-equipment-affinities";
export const CHANGEOVERS_KEY = "work-center-changeovers";

const csrf = () => ({ "X-CSRFToken": getCookie("csrftoken") });

function useInvalidate(root: string) {
    const queryClient = useQueryClient();
    return () => queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === root });
}

// ── Step timings ────────────────────────────────────────────────────────────

export const stepTimingsOptions = (queries?: StepTimingsQueries) =>
    queryOptions({
        queryKey: [STEP_TIMINGS_KEY, queries] as const,
        queryFn: () =>
            api.api_StepTimings_list(queries ? { queries } : undefined) as Promise<S["PaginatedStepTimingRecordList"]>,
    });

export const useStepTimings = (queries?: StepTimingsQueries) => useQuery(stepTimingsOptions(queries));

export const stepTimingOptions = (id: string) =>
    queryOptions({
        queryKey: [STEP_TIMINGS_KEY, "detail", id] as const,
        queryFn: () => api.api_StepTimings_retrieve({ params: { id } }) as Promise<StepTiming>,
    });

export const useStepTiming = (id: string) => useQuery({ ...stepTimingOptions(id), enabled: !!id });

export function useCreateStepTiming() {
    const invalidate = useInvalidate(STEP_TIMINGS_KEY);
    return useMutation<StepTiming, unknown, S["StepTimingRecordRequest"]>({
        mutationFn: (data) => api.api_StepTimings_create(data, { headers: csrf() }) as Promise<StepTiming>,
        onSuccess: invalidate,
    });
}

export function useUpdateStepTiming() {
    const invalidate = useInvalidate(STEP_TIMINGS_KEY);
    return useMutation<StepTiming, unknown, { id: string; data: S["PatchedStepTimingRecordRequest"] }>({
        mutationFn: ({ id, data }) =>
            api.api_StepTimings_partial_update(data, { params: { id }, headers: csrf() }) as Promise<StepTiming>,
        onSuccess: invalidate,
    });
}

export function useDeleteStepTiming() {
    const invalidate = useInvalidate(STEP_TIMINGS_KEY);
    return useMutation<unknown, unknown, string>({
        mutationFn: (id) => api.api_StepTimings_destroy(undefined, { params: { id }, headers: csrf() }),
        onSuccess: invalidate,
    });
}

// ── Step ↔ machine eligibility ──────────────────────────────────────────────

export const stepAffinitiesOptions = (queries?: AffinitiesQueries) =>
    queryOptions({
        queryKey: [STEP_AFFINITIES_KEY, queries] as const,
        queryFn: () =>
            api.api_StepEquipmentAffinities_list(queries ? { queries } : undefined) as Promise<S["PaginatedStepEquipmentAffinityList"]>,
    });

export const useStepAffinities = (queries?: AffinitiesQueries) => useQuery(stepAffinitiesOptions(queries));

export const stepAffinityOptions = (id: string) =>
    queryOptions({
        queryKey: [STEP_AFFINITIES_KEY, "detail", id] as const,
        queryFn: () => api.api_StepEquipmentAffinities_retrieve({ params: { id } }) as Promise<StepEquipmentAffinity>,
    });

export const useStepAffinity = (id: string) => useQuery({ ...stepAffinityOptions(id), enabled: !!id });

export function useCreateStepAffinity() {
    const invalidate = useInvalidate(STEP_AFFINITIES_KEY);
    return useMutation<StepEquipmentAffinity, unknown, S["StepEquipmentAffinityRequest"]>({
        mutationFn: (data) =>
            api.api_StepEquipmentAffinities_create(data, { headers: csrf() }) as Promise<StepEquipmentAffinity>,
        onSuccess: invalidate,
    });
}

export function useUpdateStepAffinity() {
    const invalidate = useInvalidate(STEP_AFFINITIES_KEY);
    return useMutation<StepEquipmentAffinity, unknown, { id: string; data: S["PatchedStepEquipmentAffinityRequest"] }>({
        mutationFn: ({ id, data }) =>
            api.api_StepEquipmentAffinities_partial_update(data, { params: { id }, headers: csrf() }) as Promise<StepEquipmentAffinity>,
        onSuccess: invalidate,
    });
}

export function useDeleteStepAffinity() {
    const invalidate = useInvalidate(STEP_AFFINITIES_KEY);
    return useMutation<unknown, unknown, string>({
        mutationFn: (id) => api.api_StepEquipmentAffinities_destroy(undefined, { params: { id }, headers: csrf() }),
        onSuccess: invalidate,
    });
}

// ── Changeover matrix ───────────────────────────────────────────────────────

export const changeoversOptions = (queries?: ChangeoversQueries) =>
    queryOptions({
        queryKey: [CHANGEOVERS_KEY, queries] as const,
        queryFn: () =>
            api.api_WorkCenterChangeovers_list(queries ? { queries } : undefined) as Promise<S["PaginatedWorkCenterChangeoverList"]>,
    });

export const useChangeovers = (queries?: ChangeoversQueries) => useQuery(changeoversOptions(queries));

export const changeoverOptions = (id: string) =>
    queryOptions({
        queryKey: [CHANGEOVERS_KEY, "detail", id] as const,
        queryFn: () => api.api_WorkCenterChangeovers_retrieve({ params: { id } }) as Promise<WorkCenterChangeover>,
    });

export const useChangeover = (id: string) => useQuery({ ...changeoverOptions(id), enabled: !!id });

export function useCreateChangeover() {
    const invalidate = useInvalidate(CHANGEOVERS_KEY);
    return useMutation<WorkCenterChangeover, unknown, S["WorkCenterChangeoverRequest"]>({
        mutationFn: (data) =>
            api.api_WorkCenterChangeovers_create(data, { headers: csrf() }) as Promise<WorkCenterChangeover>,
        onSuccess: invalidate,
    });
}

export function useUpdateChangeover() {
    const invalidate = useInvalidate(CHANGEOVERS_KEY);
    return useMutation<WorkCenterChangeover, unknown, { id: string; data: S["PatchedWorkCenterChangeoverRequest"] }>({
        mutationFn: ({ id, data }) =>
            api.api_WorkCenterChangeovers_partial_update(data, { params: { id }, headers: csrf() }) as Promise<WorkCenterChangeover>,
        onSuccess: invalidate,
    });
}

export function useDeleteChangeover() {
    const invalidate = useInvalidate(CHANGEOVERS_KEY);
    return useMutation<unknown, unknown, string>({
        mutationFn: (id) => api.api_WorkCenterChangeovers_destroy(undefined, { params: { id }, headers: csrf() }),
        onSuccess: invalidate,
    });
}
