/**
 * Outside-processing (subcontract, Flow B) hooks.
 *
 * Send parts out to a vendor for an OSP step → receive them back (which opens a
 * return inspection that reuses the DWI receiving runtime). Mutations carry the
 * CSRF header and invalidate shipments + parts on success.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { components } from "@/lib/api/generated-types";

const csrf = () => ({ "X-CSRFToken": getCookie("csrftoken") ?? "" });

/** OSP lifecycle actions move parts across the shipper board (ospReadyToShip),
 *  the shipment lists (ospShipments), the parts board, and the unified incoming
 *  queue (incomingInspection). Invalidate all four so no surface goes stale. */
function invalidateOsp(qc: ReturnType<typeof useQueryClient>) {
    const keys = ["ospReadyToShip", "ospShipments", "parts", "incomingInspection"];
    qc.invalidateQueries({ predicate: (q) => keys.includes(q.queryKey[0] as string) });
}

export type OutsideProcessShipment = components["schemas"]["OutsideProcessShipment"];
export type ReadyToShipGroup = components["schemas"]["ReadyToShipGroup"];
type PaginatedShipments = components["schemas"]["PaginatedOutsideProcessShipmentList"];

/** Shipper board: parts staged at OSP steps, grouped by step/vendor, ready to dispatch.
 *  The endpoint returns a paginated envelope (it rides a paginated viewset); unwrap it. */
export function useReadyToShip() {
    return useQuery({
        queryKey: ["ospReadyToShip"] as const,
        queryFn: async () => {
            const r = await api.api_OutsideProcessShipments_ready_to_ship_list();
            return ((r as { results?: ReadyToShipGroup[] }).results ?? []) as ReadyToShipGroup[];
        },
        staleTime: 15_000,
    });
}

/** Shipments filtered by arbitrary query (e.g. cross-WO { status: "SENT" }). */
export function useOSPShipments(queries?: Record<string, string>) {
    return useQuery({
        queryKey: ["ospShipments", "list", queries] as const,
        queryFn: () =>
            api.api_OutsideProcessShipments_list({ queries } as never) as Promise<PaginatedShipments>,
        staleTime: 15_000,
    });
}

export function useListOSPShipments(workOrderId: string, opts?: { enabled?: boolean }) {
    return useQuery({
        queryKey: ["ospShipments", "by-wo", workOrderId] as const,
        queryFn: () =>
            api.api_OutsideProcessShipments_list({
                queries: { work_order: workOrderId } as never,
            }) as Promise<PaginatedShipments>,
        enabled: opts?.enabled ?? !!workOrderId,
        staleTime: 15_000,
    });
}

export type SendPartsOutBody = {
    step: string;
    part_ids: string[];
    supplier?: string;
    reference?: string;
};

export function useSendPartsOut() {
    const qc = useQueryClient();
    return useMutation<OutsideProcessShipment, unknown, SendPartsOutBody>({
        mutationFn: (body) =>
            api.api_OutsideProcessShipments_send_out_create(body as never, {
                headers: csrf(),
            }) as Promise<OutsideProcessShipment>,
        onSuccess: () => invalidateOsp(qc),
        meta: { errorMessage: "Couldn't send parts out" },
    });
}

/** Receive a shipment back — opens its return inspection (returns the QualityReport). */
export function useReceiveBack() {
    const qc = useQueryClient();
    return useMutation<components["schemas"]["QualityReports"], unknown, { id: string }>({
        mutationFn: ({ id }) =>
            api.api_OutsideProcessShipments_receive_back_create(undefined as never, {
                params: { id },
                headers: csrf(),
            }) as Promise<components["schemas"]["QualityReports"]>,
        onSuccess: () => invalidateOsp(qc),
        meta: { errorMessage: "Couldn't receive the shipment back" },
    });
}
