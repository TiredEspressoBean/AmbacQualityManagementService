import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

const csrf = () => ({ "X-CSRFToken": getCookie("csrftoken") });

const invalidate = (qc: ReturnType<typeof useQueryClient>) => {
    qc.invalidateQueries({ predicate: (q) => q.queryKey[0] === "supplier-qualifications" });
    qc.invalidateQueries({ predicate: (q) => q.queryKey[0] === "qualification-status" });
};

export type QualificationListParams = {
    supplier?: string;
    part_type?: string;
    status?: string;
    scope_type?: string;
    search?: string;
    limit?: number;
    offset?: number;
};

export const useListSupplierQualifications = (params: QualificationListParams = {}) =>
    useQuery({
        queryKey: ["supplier-qualifications", params] as const,
        queryFn: () => api.api_SupplierQualifications_list({ queries: params } as never),
    });

export const useRetrieveSupplierQualification = (id: string | undefined) =>
    useQuery({
        queryKey: ["supplier-qualifications", "detail", id] as const,
        enabled: !!id,
        queryFn: () =>
            api.api_SupplierQualifications_retrieve({ params: { id: id as string } } as never) as Promise<
                Schema<"SupplierQualification">
            >,
    });

/** Resolve a supplier's standing for a scope — for badges + the receiving banner. */
export const useSupplierQualificationStatus = (
    supplierId: string | undefined,
    partTypeId?: string,
) =>
    useQuery({
        queryKey: ["qualification-status", supplierId, partTypeId] as const,
        enabled: !!supplierId,
        queryFn: () =>
            api.api_SupplierQualifications_status_retrieve({
                queries: { supplier: supplierId as string, part_type: partTypeId },
            } as never) as Promise<Schema<"QualificationStatus">>,
        meta: { suppressGlobalError: true },
    });

export const useCreateSupplierQualification = () => {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (body: Partial<Schema<"SupplierQualification">>) =>
            api.api_SupplierQualifications_create(body as never, { headers: csrf() }),
        onSuccess: () => invalidate(qc),
    });
};

export const useUpdateSupplierQualification = () => {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (vars: { id: string; body: Partial<Schema<"SupplierQualification">> }) =>
            api.api_SupplierQualifications_partial_update(vars.body as never, {
                params: { id: vars.id },
                headers: csrf(),
            }),
        onSuccess: () => invalidate(qc),
    });
};

export const useGrantQualification = () => {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (vars: { id: string; conditional?: boolean; effective_date?: string | null; expiry_date?: string | null }) =>
            api.api_SupplierQualifications_grant_create(
                {
                    conditional: vars.conditional ?? false,
                    effective_date: vars.effective_date ?? null,
                    expiry_date: vars.expiry_date ?? null,
                } as never,
                { params: { id: vars.id }, headers: csrf() },
            ),
        onSuccess: () => invalidate(qc),
    });
};

export const useSuspendQualification = () => {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (vars: { id: string; reason?: string }) =>
            api.api_SupplierQualifications_suspend_create({ reason: vars.reason ?? "" } as never, {
                params: { id: vars.id },
                headers: csrf(),
            }),
        onSuccess: () => invalidate(qc),
    });
};

export const useDisqualifyQualification = () => {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (vars: { id: string; reason?: string }) =>
            api.api_SupplierQualifications_disqualify_create({ reason: vars.reason ?? "" } as never, {
                params: { id: vars.id },
                headers: csrf(),
            }),
        onSuccess: () => invalidate(qc),
    });
};
