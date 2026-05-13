import { useQuery, queryOptions } from "@tanstack/react-query";
import {api} from "@/lib/api/generated.ts";
import type { Schema } from "@/lib/api/types";

type CustomerResponse = Schema<"UserDetail">;

export const retrieveCustomerOptions = (id?: string) => queryOptions({
    queryKey: ["customer", id] as const,
    queryFn: () => id ? api.api_Customers_retrieve({params: {id: id as never}}) as Promise<CustomerResponse> : Promise.resolve(null),
});

export function useRetrieveCustomer(id?: string) {
    return useQuery({
        ...retrieveCustomerOptions(id),
        enabled: !!id,
    });
}
