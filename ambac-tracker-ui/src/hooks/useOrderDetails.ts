import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api/generated.ts'

export function useOrderDetails(orderNumber: string) {
    return useQuery({
        queryKey: ['order', orderNumber],
        queryFn: () => api.api_TrackerOrders_retrieve({params: {id: orderNumber}}),
        enabled: !!orderNumber,
    })
}