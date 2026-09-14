import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export const processChangeRequestOptions = (id: string | undefined) =>
    queryOptions({
        queryKey: ["process-change-request", id] as const,
        queryFn: () =>
            (api as {
                api_process_change_requests_retrieve: (args: { params: { id: string } }) => Promise<unknown>;
            }).api_process_change_requests_retrieve({ params: { id: id! } }),
    });

export function useProcessChangeRequest(id: string | undefined) {
    return useQuery({ ...processChangeRequestOptions(id), enabled: !!id });
}

export const processChangeOrderOptions = (id: string | undefined) =>
    queryOptions({
        queryKey: ["process-change-order", id] as const,
        queryFn: () =>
            (api as {
                api_process_change_orders_retrieve: (args: { params: { id: string } }) => Promise<unknown>;
            }).api_process_change_orders_retrieve({ params: { id: id! } }),
    });

export function useProcessChangeOrder(id: string | undefined) {
    return useQuery({ ...processChangeOrderOptions(id), enabled: !!id });
}

export const processChangeNoticeOptions = (id: string | undefined) =>
    queryOptions({
        queryKey: ["process-change-notice", id] as const,
        queryFn: () =>
            (api as {
                api_process_change_notices_retrieve: (args: { params: { id: string } }) => Promise<unknown>;
            }).api_process_change_notices_retrieve({ params: { id: id! } }),
    });

export function useProcessChangeNotice(id: string | undefined) {
    return useQuery({ ...processChangeNoticeOptions(id), enabled: !!id });
}
