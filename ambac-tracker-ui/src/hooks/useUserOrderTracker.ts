import { useInfiniteQuery, infiniteQueryOptions } from '@tanstack/react-query'
import { api } from '@/lib/api/generated.ts'

export const userOrdersOptions = () =>
    infiniteQueryOptions({
        queryKey: ['userOrders'] as const,
        queryFn: async ({ pageParam = 0 }) => {
            const response = await api.api_TrackerOrders_list({
                queries: {
                    limit: 25,
                    offset: pageParam as number,
                }
            });
            return response;
        },
        getNextPageParam: (lastPage, allPages) => {
            // If there's a next page, return the new offset
            if (lastPage.next) {
                // Calculate total items loaded so far
                const totalLoaded = allPages.reduce((acc, page) => acc + page.results.length, 0);
                return totalLoaded;
            }
            return undefined;
        },
        initialPageParam: 0,
    });

export function useUserOrders() {
    return useInfiniteQuery(userOrdersOptions());
}
