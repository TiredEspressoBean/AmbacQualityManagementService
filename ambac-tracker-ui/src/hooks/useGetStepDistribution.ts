import { useInfiniteQuery, infiniteQueryOptions, type InfiniteData } from "@tanstack/react-query";
import { api, type PaginatedStepDistributionResponseList } from "@/lib/api/generated.ts";
import { getCookie } from "@/lib/utils.ts";

export const stepDistributionOptions = (orderId: number | string) =>
    infiniteQueryOptions<PaginatedStepDistributionResponseList, Error, InfiniteData<PaginatedStepDistributionResponseList>, ['step-distribution', number | string], number>({
        queryKey: ['step-distribution', orderId] as const,
        queryFn: ({ pageParam }) =>
            api.api_Orders_step_distribution_list({
                params: { id: String(orderId) },
                queries: {
                    offset: pageParam as number,
                },
                headers: {
                    "X-CSRFToken": getCookie("csrftoken")
                }
            }),
        initialPageParam: 0,
        getNextPageParam: (lastPage, _pages, lastOffset) =>
            lastPage.next ? lastOffset + lastPage.results.length : undefined,
    });

export function useGetStepDistribution(orderId: number | string) {
    return useInfiniteQuery({
        ...stepDistributionOptions(orderId),
        enabled: !!orderId,
    });
}
