import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api/generated.ts'

export function useOrderDetails(orderNumber: string) {
    const id = Number(orderNumber)
    return useQuery({
        queryKey: ['order', orderNumber],
        queryFn: () => api.api_TrackerOrders_retrieve({params: {id}}),
        enabled: !!orderNumber,
    })
}