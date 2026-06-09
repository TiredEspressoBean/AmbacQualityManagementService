import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

/**
 * Read-only list hooks for the three change-control artifact types.
 *
 * Backend is fully built; this surface is a starter list view. Create /
 * lifecycle action UI is the next chunk — for now the page renders rows
 * read from these endpoints so the sidebar entry resolves to something
 * useful (even when the tenant has zero artifacts).
 */

export const processChangeRequestsOptions = () =>
    queryOptions({
        queryKey: ["process-change-requests"] as const,
        queryFn: () =>
            (api as { api_process_change_requests_list: (args?: unknown) => Promise<unknown> })
                .api_process_change_requests_list(),
    });

export const processChangeOrdersOptions = () =>
    queryOptions({
        queryKey: ["process-change-orders"] as const,
        queryFn: () =>
            (api as { api_process_change_orders_list: (args?: unknown) => Promise<unknown> })
                .api_process_change_orders_list(),
    });

export const processChangeNoticesOptions = () =>
    queryOptions({
        queryKey: ["process-change-notices"] as const,
        queryFn: () =>
            (api as { api_process_change_notices_list: (args?: unknown) => Promise<unknown> })
                .api_process_change_notices_list(),
    });

export function useProcessChangeRequests() {
    return useQuery(processChangeRequestsOptions());
}
export function useProcessChangeOrders() {
    return useQuery(processChangeOrdersOptions());
}
export function useProcessChangeNotices() {
    return useQuery(processChangeNoticesOptions());
}
