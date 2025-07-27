import { useQuery } from "@tanstack/react-query";
import {api} from "@/lib/api/generated.ts";

export function useRetrieveCompany(id?: number) {
    return useQuery({
        queryKey: ["company", id],
        queryFn: () => id ? api.api_Companies_retrieve({params: {id}}) : Promise.resolve(null),
        enabled: !!id,
        staleTime: 5 * 60 * 1000, // optional: 5 minute cache
    });
}