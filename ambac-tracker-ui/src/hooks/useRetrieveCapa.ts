import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/generated.ts"

export function useRetrieveCapa(id: string) {
    return useQuery({
        queryKey: ["capa", id],
        queryFn: () => api.api_CAPAs_retrieve({ params: { id } }),
        enabled: !!id,
    });
}