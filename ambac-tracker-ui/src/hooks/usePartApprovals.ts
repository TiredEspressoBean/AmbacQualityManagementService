/** Part approvals (PPAP / FAI) — a supplier approved to produce a specific part type.
 *  Mirrors the ASL (SupplierQualification) hooks; backend at /api/PartApprovals/. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

const csrf = () => ({ "X-CSRFToken": getCookie("csrftoken") });

const invalidate = (qc: ReturnType<typeof useQueryClient>) => {
    qc.invalidateQueries({ predicate: (q) => q.queryKey[0] === "part-approvals" });
    qc.invalidateQueries({ predicate: (q) => q.queryKey[0] === "part-approval-status" });
};

export type PartApprovalListParams = {
    supplier?: string;
    part_type?: string;
    approval_type?: string;
    status?: string;
    search?: string;
    limit?: number;
    offset?: number;
};

export const useListPartApprovals = (params: PartApprovalListParams = {}) =>
    useQuery({
        queryKey: ["part-approvals", params] as const,
        queryFn: () => api.api_PartApprovals_list({ queries: params } as never),
    });

export const useRetrievePartApproval = (id: string | undefined) =>
    useQuery({
        queryKey: ["part-approvals", "detail", id] as const,
        enabled: !!id,
        queryFn: () =>
            api.api_PartApprovals_retrieve({ params: { id: id as string } } as never) as Promise<
                Schema<"PartApproval">
            >,
    });

/** Resolve a (part type, supplier) approval standing — for badges + the receiving banner. */
export const usePartApprovalStatus = (partTypeId: string | undefined, supplierId: string | undefined) =>
    useQuery({
        queryKey: ["part-approval-status", partTypeId, supplierId] as const,
        enabled: !!partTypeId && !!supplierId,
        queryFn: () =>
            api.api_PartApprovals_status_retrieve({
                queries: { part_type: partTypeId as string, supplier: supplierId as string },
            } as never),
        meta: { suppressGlobalError: true },
    });

export const useCreatePartApproval = () => {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (body: Partial<Schema<"PartApproval">>) =>
            api.api_PartApprovals_create(body as never, { headers: csrf() }),
        onSuccess: () => invalidate(qc),
    });
};

export const useUpdatePartApproval = () => {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (vars: { id: string; body: Partial<Schema<"PartApproval">> }) =>
            api.api_PartApprovals_partial_update(vars.body as never, {
                params: { id: vars.id }, headers: csrf(),
            }),
        onSuccess: () => invalidate(qc),
    });
};

export const useGrantPartApproval = () => {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (vars: { id: string; conditional?: boolean; effective_date?: string | null; expiry_date?: string | null }) =>
            api.api_PartApprovals_grant_create(
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

export const useSuspendPartApproval = () => {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (vars: { id: string; reason?: string }) =>
            api.api_PartApprovals_suspend_create({ reason: vars.reason ?? "" } as never, {
                params: { id: vars.id }, headers: csrf(),
            }),
        onSuccess: () => invalidate(qc),
    });
};

export const useDisqualifyPartApproval = () => {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (vars: { id: string; reason?: string }) =>
            api.api_PartApprovals_disqualify_create({ reason: vars.reason ?? "" } as never, {
                params: { id: vars.id }, headers: csrf(),
            }),
        onSuccess: () => invalidate(qc),
    });
};
