import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api/generated.ts'


export function useRetrieveOrders(p: { limit: number; offset: number; ordering: string | undefined }) {
    return useQuery({
        queryKey: ['orders'],
        queryFn: async () => {
            const response = await api.api_Orders_list({queries:p});
            return response.results; // <--- be sure this is correct
        }
    });
}