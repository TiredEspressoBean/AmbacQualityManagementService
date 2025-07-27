import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api/generated.ts'

export function useUserOrders() {
    return useQuery({
        queryKey: ['userOrders'],
        queryFn: async () => {
            const response = await api.api_TrackerOrders_list();
            return response.results; // <--- be sure this is correct
        }
    });
}