import { useQuery } from "@tanstack/react-query";
import {api} from "@/lib/api/generated.ts";

export function useRetrieveDocument(id?: number) {
    return useQuery({
        queryKey: ["document", id],
        queryFn: () => id ? api.api_Documents_retrieve({params: {id}}) : Promise.resolve(null),
        enabled: !!id,
        staleTime: 5 * 60 * 1000, // optional: 5 minute cache
    });
}