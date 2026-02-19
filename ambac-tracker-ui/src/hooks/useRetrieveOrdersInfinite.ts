import { useInfiniteQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export function useRetrieveOrdersInfinite(search: string) {
    return useInfiniteQuery({
        queryKey: ["order", search],
        queryFn: ({ pageParam = 0 }) =>
            api.api_Orders_list({ search, offset: pageParam }),
        initialPageParam: 0,
        getNextPageParam: (lastPage, allPages) =>
            (lastPage.next ?? null) ? allPages.length * 20 : undefined,
    });
}
