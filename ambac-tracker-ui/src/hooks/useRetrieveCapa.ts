import { useQuery, queryOptions } from "@tanstack/react-query"
import { api } from "@/lib/api/generated.ts"
import type { Schema } from "@/lib/api/types";

type CAPAResponse = Schema<"CAPA">;

export const retrieveCapaOptions = (id: string) => queryOptions({
    queryKey: ["capa", id] as const,
    queryFn: () => api.api_CAPAs_retrieve({ params: { id } }) as Promise<CAPAResponse>,
});

export function useRetrieveCapa(id: string) {
    return useQuery({
        ...retrieveCapaOptions(id),
        enabled: !!id,
    });
}
