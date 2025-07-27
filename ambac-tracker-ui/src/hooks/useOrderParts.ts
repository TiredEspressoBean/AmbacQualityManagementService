import { useInfiniteQuery } from '@tanstack/react-query'
import { api } from '@/lib/api/generated'
import {getCookie} from "@/lib/utils.ts";

export function useOrderParts(orderId: number | string) {
    return useInfiniteQuery({
        queryKey: ['order-parts', orderId],
        queryFn: ({ pageParam = 0 }) =>
            api.api_orders_parts_list({
                params: { order_id: Number(orderId) },
                queries: {
                    offset: pageParam,
                    limit: 25,
                },
                headers: {
                    "X-CSRFToken": getCookie("csrftoken")
                }
            }),
        initialPageParam: 0,
        getNextPageParam: (lastPage, _pages, lastOffset) =>
            lastPage.next ? lastOffset + lastPage.results.length : undefined,
        enabled: !!orderId,
    })
}