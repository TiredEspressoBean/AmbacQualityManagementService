import {useInfiniteQuery} from "@tanstack/react-query";
import { api, type PaginatedStepDistributionResponseList } from "@/lib/api/generated.ts";
import { getCookie} from "@/lib/utils.ts";

export function useGetStepDistribution (orderId:number | string) {
    return useInfiniteQuery<PaginatedStepDistributionResponseList, Error>({
        queryKey: ['step-distribution', orderId],
        queryFn: ({pageParam = 0}) =>
            api.api_Orders_step_distribution_list({
                params:{id: orderId},
                queries: {
                    offset: pageParam,
                },
                headers: {
                    "X-CSRFToken": getCookie("csrftoken")
                }
            },
        ),
        initialPageParam: 0,
        getNextPageParam:(lastPage, _pages, lastOffset) =>
            lastPage.next ? lastOffset + lastPage.results.length : undefined,
        enabled: !!orderId,
    })
}
