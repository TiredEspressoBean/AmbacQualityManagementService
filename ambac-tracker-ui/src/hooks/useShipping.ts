import { queryOptions, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { Schema } from "@/lib/api/types";

export type Shipment = Schema<"CustomerShipment">;
export type ReadyOrder = Schema<"ReadyToShipOrder">;
export type ShipRequest = Schema<"ShipRequestRequest">;

export const readyToShipOptions = () =>
    queryOptions({
        queryKey: ["shipping", "ready"],
        queryFn: () => api.api_CustomerShipments_ready_list() as Promise<ReadyOrder[]>,
    });

export const shipmentsOptions = (search = "") =>
    queryOptions({
        queryKey: ["shipping", "list", search],
        queryFn: () => api.api_CustomerShipments_list({ queries: { limit: 100, search: search || undefined } }),
    });

export const shipmentOptions = (id: string) =>
    queryOptions({
        queryKey: ["shipping", "detail", id],
        queryFn: () => api.api_CustomerShipments_retrieve({ params: { id } }) as Promise<Shipment>,
    });

export const orderShippingOptions = (orderId: string) =>
    queryOptions({
        queryKey: ["shipping", "order", orderId],
        queryFn: () => api.api_CustomerShipments_order_shipping_retrieve({ queries: { order: orderId } }),
    });

export const deliveryPerformanceOptions = (days = 90) =>
    queryOptions({
        queryKey: ["shipping", "performance", days],
        queryFn: () => api.api_CustomerShipments_delivery_performance_retrieve({ queries: { days } }),
    });

function useInvalidateShipping() {
    const qc = useQueryClient();
    return () => {
        void qc.invalidateQueries({ queryKey: ["shipping"] });
        void qc.invalidateQueries({ queryKey: ["parts"] });
        void qc.invalidateQueries({ queryKey: ["material-lot"] });
    };
}

export function useShipParts() {
    const invalidate = useInvalidateShipping();
    return useMutation({
        mutationFn: (body: ShipRequest) => api.api_CustomerShipments_ship_create(body) as Promise<Shipment>,
        onSuccess: invalidate,
    });
}

export function useVoidShipment() {
    const invalidate = useInvalidateShipping();
    return useMutation({
        mutationFn: ({ id, reason }: { id: string; reason: string }) =>
            api.api_CustomerShipments_void_create({ reason }, { params: { id } }) as Promise<Shipment>,
        onSuccess: invalidate,
    });
}

export function useUpdateShipment() {
    const invalidate = useInvalidateShipping();
    return useMutation({
        mutationFn: ({ id, ...body }: { id: string } & Partial<Schema<"PatchedCustomerShipmentRequest">>) =>
            api.api_CustomerShipments_partial_update(body, { params: { id } }) as Promise<Shipment>,
        onSuccess: invalidate,
    });
}

export const errorOf = (err: unknown, fallback: string) =>
    (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? fallback;
