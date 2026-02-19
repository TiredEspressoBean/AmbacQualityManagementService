import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export function usePartTraveler(
    partId: string,
    options?: { enabled?: boolean }
) {
    return useQuery({
        queryKey: ["part-traveler", partId],
        queryFn: () => api.api_Parts_traveler_retrieve({ params: { id: partId } }),
        enabled: (options?.enabled ?? true) && !!partId,
    });
}
