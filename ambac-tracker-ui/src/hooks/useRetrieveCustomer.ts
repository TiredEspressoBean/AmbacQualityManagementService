import { useQuery, queryOptions } from "@tanstack/react-query";
import {api} from "@/lib/api/generated.ts";
import type { Schema } from "@/lib/api/types";

type CustomerResponse = Schema<"UserDetail">;

export const retrieveCustomerOptions = (id?: string) => queryOptions({
    queryKey: ["customer", id] as const,
    // Customers are keyed by an integer pk while callers hold the route param as
    // a string, so convert at the boundary. The cast used to paper over the
    // mismatch instead.
    queryFn: () => id ? api.api_Customers_retrieve({ params: { id: Number(id) } }) as Promise<CustomerResponse> : Promise.resolve(null),
});

export function useRetrieveCustomer(id?: string) {
    return useQuery({
        ...retrieveCustomerOptions(id),
        enabled: !!id,
    });
}
