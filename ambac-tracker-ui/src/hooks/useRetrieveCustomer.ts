import { useQuery } from "@tanstack/react-query";
import {api} from "@/lib/api/generated.ts";

export function useRetrieveCustomer(id?: number) {
    return useQuery({
        queryKey: ["customer", id],
        queryFn: () => id ? api.api_Customers_retrieve({params: {id}}) : Promise.resolve(null),
        enabled: !!id,
        staleTime: 5 * 60 * 1000, // optional: 5 minute cache
    });
}