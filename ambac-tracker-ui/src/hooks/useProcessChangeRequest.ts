import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export function useProcessChangeRequest(id: string | undefined) {
    return useQuery({
        queryKey: ["process-change-request", id] as const,
        enabled: !!id,
        queryFn: () =>
            (api as {
                api_process_change_requests_retrieve: (args: { params: { id: string } }) => Promise<unknown>;
            }).api_process_change_requests_retrieve({ params: { id: id! } }),
    });
}

export function useProcessChangeOrder(id: string | undefined) {
    return useQuery({
        queryKey: ["process-change-order", id] as const,
        enabled: !!id,
        queryFn: () =>
            (api as {
                api_process_change_orders_retrieve: (args: { params: { id: string } }) => Promise<unknown>;
            }).api_process_change_orders_retrieve({ params: { id: id! } }),
    });
}

export function useProcessChangeNotice(id: string | undefined) {
    return useQuery({
        queryKey: ["process-change-notice", id] as const,
        enabled: !!id,
        queryFn: () =>
            (api as {
                api_process_change_notices_retrieve: (args: { params: { id: string } }) => Promise<unknown>;
            }).api_process_change_notices_retrieve({ params: { id: id! } }),
    });
}
