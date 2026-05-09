import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/generated.ts"
import type { Schema } from "@/lib/api/types";

type CAPAResponse = Schema<"CAPA">;

export function useRetrieveCapa(id: string) {
    return useQuery<CAPAResponse>({
        queryKey: ["capa", id],
        queryFn: () => api.api_CAPAs_retrieve({ params: { id } }) as Promise<CAPAResponse>,
        enabled: !!id,
    });
}