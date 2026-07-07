import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

const csrf = () => ({ "X-CSRFToken": getCookie("csrftoken") });

const invalidateReceiving = (queryClient: ReturnType<typeof useQueryClient>) =>
    queryClient.invalidateQueries({
        // material-lots backs the Materials views + receiving queue; incomingInspection
        // is the unified QA32-style worklist a lot also appears on.
        predicate: (q) => q.queryKey[0] === "material-lots" || q.queryKey[0] === "incomingInspection",
    });

// ----- Bulk receive lots (paste-grid) -----

export type LotBulkRow = {
    lot_number: string;
    received_date: string;
    material_type?: string | null;
    material_description?: string;
    supplier?: string | null;
    supplier_lot_number?: string;
    quantity: string;
    unit_of_measure?: string;
    manufacture_date?: string | null;
    expiration_date?: string | null;
    storage_location?: string;
};

export const useBulkCreateLots = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (vars: { lots: LotBulkRow[] }) =>
            api.api_MaterialLots_bulk_create_create({ lots: vars.lots } as never, { headers: csrf() }),
        onSuccess: () => invalidateReceiving(queryClient),
    });
};

// ----- Certificate of Conformance capture (multipart PATCH of the lot) -----
// The generated client types certificate_of_conformance as a URL string, so a
// File upload goes through a raw multipart PATCH (mirrors useDocumentUpload).
export const useUploadLotCoC = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async (vars: { id: string; file: File }) => {
            const form = new FormData();
            form.append("certificate_of_conformance", vars.file);
            const res = await fetch(`/api/MaterialLots/${vars.id}/`, {
                method: "PATCH",
                credentials: "include",
                headers: { "X-CSRFToken": getCookie("csrftoken") ?? "" },
                body: form,
            });
            if (!res.ok) {
                let detail = "Upload failed";
                try { const b = await res.json(); detail = b.detail ?? JSON.stringify(b); } catch { /* ignore */ }
                throw new Error(`${res.status}: ${detail}`);
            }
            return res.json();
        },
        onSuccess: (_data, vars) => {
            invalidateReceiving(queryClient);
            queryClient.invalidateQueries({ queryKey: ["material-lot", vars.id] });
            queryClient.invalidateQueries({ queryKey: ["supplier-scorecard"] });
        },
    });
};

// ----- Inspection lifecycle actions (detail, keyed by lot id) -----

export const useOpenInspection = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (vars: { id: string }) =>
            api.api_MaterialLots_open_inspection_create(undefined as never, {
                params: { id: vars.id },
                headers: csrf(),
            }),
        onSuccess: () => invalidateReceiving(queryClient),
    });
};

export const useRecordInspection = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (vars: {
            id: string;
            measurements: { definition: string; value_numeric?: number | null; value_pass_fail?: "PASS" | "FAIL" | null }[];
        }) =>
            api.api_MaterialLots_record_inspection_create({ measurements: vars.measurements } as never, {
                params: { id: vars.id },
                headers: csrf(),
            }),
        onSuccess: () => invalidateReceiving(queryClient),
    });
};

export const useRecordUnits = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (vars: {
            id: string;
            units: { sample_number: number; measurements: { definition: string; value_numeric?: number | null; value_pass_fail?: "PASS" | "FAIL" | null }[] }[];
        }) =>
            api.api_MaterialLots_record_units_create({ units: vars.units } as never, {
                params: { id: vars.id },
                headers: csrf(),
            }),
        onSuccess: () => invalidateReceiving(queryClient),
    });
};

export const useRecordBulk = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (vars: { id: string; defectives_found: number }) =>
            api.api_MaterialLots_record_bulk_create({ defectives_found: vars.defectives_found } as never, {
                params: { id: vars.id },
                headers: csrf(),
            }),
        onSuccess: () => invalidateReceiving(queryClient),
    });
};

export const useAcceptLot = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (vars: { id: string }) =>
            api.api_MaterialLots_accept_create(undefined as never, { params: { id: vars.id }, headers: csrf() }),
        onSuccess: () => invalidateReceiving(queryClient),
    });
};

export const useRejectLot = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (vars: { id: string }) =>
            api.api_MaterialLots_reject_create(undefined as never, { params: { id: vars.id }, headers: csrf() }),
        onSuccess: () => invalidateReceiving(queryClient),
    });
};

export const useRaiseScar = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (vars: { id: string }) =>
            api.api_MaterialLots_raise_scar_create(undefined as never, { params: { id: vars.id }, headers: csrf() }),
        onSuccess: () => {
            invalidateReceiving(queryClient);
            queryClient.invalidateQueries({ queryKey: ["supplier-scorecard"] });
        },
    });
};

// ----- Derived sample plan (GET) -----

export const useSamplePlan = (lotId: string | undefined, plan?: string) =>
    useQuery({
        queryKey: ["sample-plan", lotId, plan] as const,
        enabled: !!lotId,
        queryFn: () =>
            api.api_MaterialLots_sample_plan_retrieve({
                params: { id: lotId as string },
                queries: plan ? { plan } : undefined,
            } as never) as Promise<Schema<"SamplePlanResponse">>,
        meta: { suppressGlobalError: true },
    });
