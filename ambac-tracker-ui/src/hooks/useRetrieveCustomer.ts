import { useQuery } from "@tanstack/react-query";
import {api} from "@/lib/api/generated.ts";

export function useRetrieveCustomer(id?: string) {
    return useQuery({
        queryKey: ["customer", id],
        queryFn: () => id ? api.api_Customers_retrieve({params: {id}}) : Promise.resolve(null),
        enabled: !!id,
    });
}