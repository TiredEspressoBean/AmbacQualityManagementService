import { useInfiniteQuery, infiniteQueryOptions, type InfiniteData } from '@tanstack/react-query'
import { api, type PaginatedPartsList } from '@/lib/api/generated'
import { getCookie } from "@/lib/utils.ts";

export const orderPartsOptions = (orderId: number | string) =>
    infiniteQueryOptions<PaginatedPartsList, Error, InfiniteData<PaginatedPartsList>, ['order-parts', number | string], number>({
        queryKey: ['order-parts', orderId] as const,
        queryFn: ({ pageParam }) =>
            // eslint-disable-next-line local/no-double-cast-via-unknown -- Zod-inferred response narrows part_type_info to a passthrough object that doesn't structurally match PaginatedPartsList — cast at boundary.
            api.api_orders_parts_list({
                params: { order_id: String(orderId) },
                queries: {
                    offset: pageParam as number,
                    limit: 25,
                },
                headers: {
                    "X-CSRFToken": getCookie("csrftoken")
                }
            }) as unknown as Promise<PaginatedPartsList>,
        initialPageParam: 0,
        getNextPageParam: (lastPage, _pages, lastOffset) =>
            lastPage.next ? lastOffset + lastPage.results.length : undefined,
    });

export function useOrderParts(orderId: number | string) {
    return useInfiniteQuery({
        ...orderPartsOptions(orderId),
        enabled: !!orderId,
    });
}
