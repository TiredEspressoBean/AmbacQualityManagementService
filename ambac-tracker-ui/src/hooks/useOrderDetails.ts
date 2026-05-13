import { useQuery, queryOptions } from '@tanstack/react-query'
import { api } from '@/lib/api/generated.ts'

export const orderDetailsOptions = (orderNumber: string) => queryOptions({
    queryKey: ['order', orderNumber] as const,
    queryFn: () => api.api_TrackerOrders_retrieve({params: {id: orderNumber}}),
});

export function useOrderDetails(orderNumber: string) {
    return useQuery({
        ...orderDetailsOptions(orderNumber),
        enabled: !!orderNumber,
    })
}