import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/generated.ts"

export function useRetrieveCustomers (queries: Parameters<typeof api.api_Customers_list>[0]) {
    return useQuery({
        queryKey: ["customers", queries],
        queryFn: () => api.api_Customers_list(queries),
    });
};