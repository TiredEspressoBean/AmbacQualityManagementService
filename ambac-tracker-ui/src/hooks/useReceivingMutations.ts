import { useMutation, useQuery, useQueryClient, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

const csrf = () => ({ "X-CSRFToken": getCookie("csrftoken") });

const invalidateReceiving = (queryClient: ReturnType<typeof useQueryClient>) =>
    queryClient.invalidateQueries({
        // material-lots backs the Materials views + receiving queue; incomingInspection
        // is the unified QA32-style worklist a lot also appears on; material-lot
        // (singular) is the lot-detail query — without it, the detail page keeps
        // showing AWAITING_INSPECTION + "Run Inspection" after an Accept/Reject.
        predicate: (q) =>
            q.queryKey[0] === "material-lots" ||
            q.queryKey[0] === "incomingInspection" ||
            q.queryKey[0] === "material-lot",
    });

// ----- Bulk receive lots (paste-grid) -----

export type LotBulkRow = {
    lot_number: string;
    received_date: string;
    /** A lot is stock of a raw material (`material`) or a bought part (`material_type`), not both. */
    material?: string | null;
    material_type?: string | null;
    material_description?: string;
    supplier?: string | null;
    supplier_lot_number?: string;
    quantity: string;
    unit_of_measure?: string;
    manufacture_date?: string | null;
    expiration_date?: string | null;
    storage_location?: string;
    heat_number?: string;
    source_type?: "MANUFACTURER" | "AUTHORIZED_DISTRIBUTOR" | "INDEPENDENT_DISTRIBUTOR";
    /** Counted in the item's buying unit: the server derives `quantity` from it. */
    received_as_quantity?: string;
    received_as_unit?: "BOX" | "LB";
};

export const useBulkCreateLots = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (vars: { lots: LotBulkRow[] }) =>
            api.api_MaterialLots_bulk_create_create({ lots: vars.lots }, { headers: csrf() }),
        onSuccess: () => invalidateReceiving(queryClient),
    });
};

// ----- Expected receipts (ordered, not yet delivered) -----
// Purchasing lives in the ERP; these record the *supply signal* so netting stops
// asking for a second order of something already on a truck.

export const useRecordExpectedReceipt = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (vars: {
            /** One of the two: a raw material, or a bought part (PartType). */
            material?: string;
            material_type?: string;
            quantity: string;
            promised_date: string;
            supplier?: string | null;
            erp_po_number?: string;
            erp_po_line?: string;
        }) =>
            api.api_MaterialLots_expected_receipt_create(
                {
                    ...(vars.material ? { material: vars.material } : {}),
                    ...(vars.material_type ? { material_type: vars.material_type } : {}),
                    quantity: vars.quantity,
                    promised_date: vars.promised_date,
                    ...(vars.supplier ? { supplier: vars.supplier } : {}),
                    erp_po_number: vars.erp_po_number ?? "",
                    erp_po_line: vars.erp_po_line ?? "",
                },
                { headers: csrf() },
            ),
        onSuccess: () => invalidateSupply(queryClient),
    });
};

/** Everything an expected receipt changes: the lot views, the sourcing report and the
 *  RCCP material lane (both count on-order stock as incoming), and late deliveries. */
const invalidateSupply = (queryClient: ReturnType<typeof useQueryClient>) => {
    invalidateReceiving(queryClient);
    queryClient.invalidateQueries({
        predicate: (q) =>
            (q.queryKey[0] === "schedule" && q.queryKey[1] === "requirements") ||
            (q.queryKey[0] === "planning" && q.queryKey[1] === "capacity-load") ||
            q.queryKey[0] === "late-deliveries",
    });
};

export type ExpectedReceiptRow = {
    /** One of the two: a raw material, or a bought part (PartType). */
    material?: string;
    material_type?: string;
    quantity: string;
    promised_date: string;
    supplier?: string | null;
    erp_po_number?: string;
    erp_po_line?: string;
};

/** Several expected receipts at once, all or nothing — raised from shortages. */
export const useBulkExpectedReceipts = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (rows: ExpectedReceiptRow[]) =>
            api.api_MaterialLots_bulk_expected_receipt_create(
                {
                    receipts: rows.map((r) => ({
                        ...(r.material ? { material: r.material } : {}),
                        ...(r.material_type ? { material_type: r.material_type } : {}),
                        quantity: r.quantity,
                        promised_date: r.promised_date,
                        ...(r.supplier ? { supplier: r.supplier } : {}),
                        erp_po_number: r.erp_po_number ?? "",
                        erp_po_line: r.erp_po_line ?? "",
                    })),
                },
                { headers: csrf() },
            ),
        onSuccess: () => invalidateSupply(queryClient),
    });
};

/** Upload a sheet of open PO lines. Matches on PO + line; only adds and updates. */
export const useImportExpectedReceipts = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (file: File) =>
            api.api_MaterialLots_import_expected_create({ file }, { headers: csrf() }),
        onSuccess: () => invalidateSupply(queryClient),
    });
};

/** Expected receipts overdue or due soon, with the work each holds up. */
export const useLateDeliveries = () =>
    useQuery(
        queryOptions({
            queryKey: ["late-deliveries"],
            queryFn: () => api.api_MaterialLots_late_deliveries_list(),
        }),
    );

export type LateDelivery = Schema<"LateDelivery">;

export const useReceiveExpectedLot = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (vars: {
            id: string;
            lot_number: string;
            quantity?: string | null;
            received_date?: string | null;
            storage_location?: string;
            /** Required when short: BACKORDERED keeps the rest on order, CLOSED closes it. */
            remainder?: "BACKORDERED" | "CLOSED";
            /** Counted in the item's buying unit — the server converts to the stock quantity. */
            received_as_quantity?: string | null;
            received_as_unit?: "BOX" | "LB";
            heat_number?: string;
            source_type?: "MANUFACTURER" | "AUTHORIZED_DISTRIBUTOR" | "INDEPENDENT_DISTRIBUTOR";
        }) =>
            api.api_MaterialLots_receive_create(
                {
                    lot_number: vars.lot_number,
                    ...(vars.quantity ? { quantity: vars.quantity } : {}),
                    ...(vars.received_date ? { received_date: vars.received_date } : {}),
                    ...(vars.storage_location ? { storage_location: vars.storage_location } : {}),
                    ...(vars.remainder ? { remainder: vars.remainder } : {}),
                    ...(vars.received_as_unit && vars.received_as_quantity
                        ? { received_as_quantity: vars.received_as_quantity, received_as_unit: vars.received_as_unit }
                        : {}),
                    ...(vars.heat_number ? { heat_number: vars.heat_number } : {}),
                    ...(vars.source_type ? { source_type: vars.source_type } : {}),
                },
                { params: { id: vars.id }, headers: csrf() },
            ),
        onSuccess: () => {
            invalidateReceiving(queryClient);
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "late-deliveries" });
            queryClient.invalidateQueries({
                predicate: (q) => q.queryKey[0] === "schedule" && q.queryKey[1] === "requirements",
            });
            queryClient.invalidateQueries({
                predicate: (q) => q.queryKey[0] === "planning" && q.queryKey[1] === "capacity-load",
            });
            // On-time delivery is measured as received_date <= promised_date over lots
            // with a promised date, so booking in an expected receipt is exactly the
            // event that moves a supplier's OTD number.
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "supplier-scorecard" });
        },
    });
};

// ----- Certificate of Conformance capture (multipart PATCH of the lot) -----
// Through the typed client. This was a hand-rolled multipart fetch, justified
// by a comment saying the client types certificate_of_conformance as a URL
// string — true of the RESPONSE, but the request schema already typed it as a
// File. What actually blocked it was requestFormat: the viewset took DRF's
// default parser order, so JSON was advertised first and the client would have
// serialised the File as JSON. MaterialLotViewSet now declares MultiPart first
// (as DocumentViewSet already did) and the endpoint generates as form-data.
export const useUploadLotCoC = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (vars: { id: string; file: File }) =>
            api.api_MaterialLots_partial_update(
                { certificate_of_conformance: vars.file },
                { params: { id: vars.id }, headers: csrf() },
            ),
        onSuccess: (_data, vars) => {
            invalidateReceiving(queryClient);
            queryClient.invalidateQueries({
                predicate: (q) => q.queryKey[0] === "material-lot" && q.queryKey[1] === vars.id,
            });
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "supplier-scorecard" });
        },
    });
};

// ----- Inspection lifecycle actions (detail, keyed by lot id) -----

export const useOpenInspection = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (vars: { id: string }) =>
            api.api_MaterialLots_open_inspection_create(undefined, {
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
            api.api_MaterialLots_record_inspection_create({ measurements: vars.measurements }, {
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
            api.api_MaterialLots_record_units_create({ units: vars.units }, {
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
            api.api_MaterialLots_record_bulk_create({ defectives_found: vars.defectives_found }, {
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
            api.api_MaterialLots_accept_create(undefined, { params: { id: vars.id }, headers: csrf() }),
        onSuccess: () => invalidateReceiving(queryClient),
    });
};

export const useRejectLot = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (vars: { id: string }) =>
            api.api_MaterialLots_reject_create(undefined, { params: { id: vars.id }, headers: csrf() }),
        onSuccess: () => invalidateReceiving(queryClient),
    });
};

export const useExtendShelfLife = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (vars: { id: string; new_expiration_date: string; reason: string }) =>
            api.api_MaterialLots_extend_shelf_life_create(
                { new_expiration_date: vars.new_expiration_date, reason: vars.reason },
                { params: { id: vars.id }, headers: csrf() },
            ),
        onSuccess: () => invalidateReceiving(queryClient),
    });
};

export const useRaiseScar = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (vars: { id: string }) =>
            api.api_MaterialLots_raise_scar_create(undefined, { params: { id: vars.id }, headers: csrf() }),
        onSuccess: () => {
            invalidateReceiving(queryClient);
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "supplier-scorecard" });
        },
    });
};

// ----- Derived sample plan (GET) -----

// No `plan` argument: the endpoint takes none. The server derives the plan from
// the lot's part type + supplier ruleset, so the parameter this used to accept
// was passed as a query param the contract doesn't declare -- dropped on the way
// out, and never supplied by any caller in the first place.
export const samplePlanOptions = (lotId: string | undefined) =>
    queryOptions({
        queryKey: ["sample-plan", lotId] as const,
        queryFn: () =>
            api.api_MaterialLots_sample_plan_retrieve({
                params: { id: lotId as string },
            }) as Promise<Schema<"SamplePlanResponse">>,
        meta: { suppressGlobalError: true },
    });

export const useSamplePlan = (lotId: string | undefined) =>
    useQuery({ ...samplePlanOptions(lotId), enabled: !!lotId });

/** One lot's detail row. ReceivingInspectionPage and ReceivingAcceptanceStage
 *  both read it and had declared this key and queryFn separately, character for
 *  character — two writers on one cache entry, which is the drift this factory
 *  exists to prevent. `invalidateReceiving` above already targets the key. */
export const materialLotOptions = (lotId: string) =>
    queryOptions({
        queryKey: ["material-lot", lotId],
        queryFn: () =>
            api.api_MaterialLots_retrieve({
                params: { id: lotId },
            }) as Promise<Schema<"MaterialLot">>,
    });

// ----- Holds and corrections -----

/** Lift a receiving hold with a reason on record (QA). The lot routes on as if it had
 *  just arrived, with that one gate waived. */
export const useReleaseHold = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (vars: { id: string; reason: string }) =>
            api.api_MaterialLots_release_hold_create(
                { reason: vars.reason }, { params: { id: vars.id }, headers: csrf() }),
        onSuccess: () => invalidateReceiving(queryClient),
    });
};

/** Correct what's left of a lot to what's physically there, with a reason. */
export const useAdjustLotQuantity = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (vars: { id: string; quantity: string; reason: string }) =>
            api.api_MaterialLots_adjust_quantity_create(
                { quantity: vars.quantity, reason: vars.reason },
                { params: { id: vars.id }, headers: csrf() }),
        onSuccess: () => invalidateSupply(queryClient),
    });
};

/** Save a lot field (heat number) — PATCH, which also re-checks a hold waiting on it. */
export const useUpdateLotHeatNumber = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (vars: { id: string; heat_number: string }) =>
            api.api_MaterialLots_partial_update(
                { heat_number: vars.heat_number }, { params: { id: vars.id }, headers: csrf() }),
        onSuccess: () => invalidateReceiving(queryClient),
    });
};

// ----- Managed storage locations -----

export const storageLocationsOptions = () =>
    queryOptions({
        // Not "storage-locations": LocationCombobox caches the picker's name list there.
        queryKey: ["storage-location-records"],
        queryFn: () => api.api_StorageLocations_list({ queries: { limit: 500, ordering: "name" } }),
    });

export const useStorageLocations = () => useQuery(storageLocationsOptions());

const invalidateLocations = (queryClient: ReturnType<typeof useQueryClient>) =>
    queryClient.invalidateQueries({
        // Both the managed records and the picker's name list (which reads them).
        predicate: (q) => q.queryKey[0] === "storage-location-records" || q.queryKey[0] === "storage-locations",
    });

export const useCreateStorageLocation = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (vars: { name: string; description?: string }) =>
            api.api_StorageLocations_create(
                { name: vars.name, description: vars.description ?? "", is_active: true },
                { headers: csrf() }),
        onSuccess: () => invalidateLocations(queryClient),
    });
};

export const useUpdateStorageLocation = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (vars: { id: string; name?: string; description?: string; is_active?: boolean }) => {
            const { id, ...body } = vars;
            return api.api_StorageLocations_partial_update(body, { params: { id }, headers: csrf() });
        },
        onSuccess: () => invalidateLocations(queryClient),
    });
};
