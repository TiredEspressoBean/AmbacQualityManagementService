/** Part approvals (PPAP / FAI) — a supplier approved to produce a specific part type.
 *  Mirrors the ASL (SupplierQualification) hooks; backend at /api/PartApprovals/. */
import { useMutation, useQuery, useQueryClient, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

const csrf = () => ({ "X-CSRFToken": getCookie("csrftoken") });

const invalidate = (qc: ReturnType<typeof useQueryClient>) => {
    qc.invalidateQueries({ predicate: (q) => q.queryKey[0] === "part-approvals" });
    qc.invalidateQueries({ predicate: (q) => q.queryKey[0] === "part-approval-status" });
};

/** Derived from the generated contract rather than hand-written. The hand-rolled
 *  version typed `status` as a bare string while the endpoint takes an enum, and
 *  the mismatch was cast away at the call -- so an invalid status compiled
 *  cleanly and was rejected at runtime. Deriving it makes that a type error at
 *  the caller, and keeps the two in step when the backend filter set changes. */
export type PartApprovalListParams = NonNullable<
    NonNullable<Parameters<typeof api.api_PartApprovals_list>[0]>["queries"]
>;

export const listPartApprovalsOptions = (params: PartApprovalListParams = {}) =>
    queryOptions({
        queryKey: ["part-approvals", params] as const,
        queryFn: () => api.api_PartApprovals_list({ queries: params }),
    });

export const useListPartApprovals = (params: PartApprovalListParams = {}) =>
    useQuery(listPartApprovalsOptions(params));

export const retrievePartApprovalOptions = (id: string | undefined) =>
    queryOptions({
        queryKey: ["part-approvals", "detail", id] as const,
        queryFn: () =>
            api.api_PartApprovals_retrieve({ params: { id: id as string } }) as Promise<
                Schema<"PartApproval">
            >,
    });

export const useRetrievePartApproval = (id: string | undefined) =>
    useQuery({ ...retrievePartApprovalOptions(id), enabled: !!id });

/** Resolve a (part type, supplier) approval standing — for badges + the receiving banner. */
export const partApprovalStatusOptions = (partTypeId: string | undefined, supplierId: string | undefined) =>
    queryOptions({
        queryKey: ["part-approval-status", partTypeId, supplierId] as const,
        queryFn: () =>
            api.api_PartApprovals_status_retrieve({
                queries: { part_type: partTypeId as string, supplier: supplierId as string },
            }),
        meta: { suppressGlobalError: true },
    });

export const usePartApprovalStatus = (partTypeId: string | undefined, supplierId: string | undefined) =>
    useQuery({
        ...partApprovalStatusOptions(partTypeId, supplierId),
        enabled: !!partTypeId && !!supplierId,
    });

export const useCreatePartApproval = () => {
    const qc = useQueryClient();
    return useMutation({
        // The request shape, not Partial<the response model>: that typed the
        // body from the read schema and made required fields optional, so a
        // body missing them compiled and was rejected by zod at the call.
        mutationFn: (body: Parameters<typeof api.api_PartApprovals_create>[0]) =>
            api.api_PartApprovals_create(body, { headers: csrf() }),
        onSuccess: () => invalidate(qc),
    });
};

export const useUpdatePartApproval = () => {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (vars: { id: string; body: Partial<Schema<"PartApproval">> }) =>
            api.api_PartApprovals_partial_update(vars.body, {
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
                },
                { params: { id: vars.id }, headers: csrf() },
            ),
        onSuccess: () => invalidate(qc),
    });
};

export const useSuspendPartApproval = () => {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (vars: { id: string; reason?: string }) =>
            api.api_PartApprovals_suspend_create({ reason: vars.reason ?? "" }, {
                params: { id: vars.id }, headers: csrf(),
            }),
        onSuccess: () => invalidate(qc),
    });
};

export const useDisqualifyPartApproval = () => {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (vars: { id: string; reason?: string }) =>
            api.api_PartApprovals_disqualify_create({ reason: vars.reason ?? "" }, {
                params: { id: vars.id }, headers: csrf(),
            }),
        onSuccess: () => invalidate(qc),
    });
};
