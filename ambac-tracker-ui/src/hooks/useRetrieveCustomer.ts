import { useQuery } from "@tanstack/react-query";
import {api} from "@/lib/api/generated.ts";
import type { Schema } from "@/lib/api/types";

type CustomerResponse = Schema<"UserDetail">;

export function useRetrieveCustomer(id?: string) {
    return useQuery<CustomerResponse | null>({
        queryKey: ["customer", id],
        queryFn: () => id ? api.api_Customers_retrieve({params: {id: id as never}}) as Promise<CustomerResponse> : Promise.resolve(null),
        enabled: !!id,
    });
}