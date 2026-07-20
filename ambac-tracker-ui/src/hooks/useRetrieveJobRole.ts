import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { Schema } from "@/lib/api/types";

export function useRetrieveJobRole(id: string) {
    return useQuery({
        queryKey: ["job-role", id],
        queryFn: () => api.api_JobRoles_retrieve({ params: { id } }) as Promise<Schema<"JobRole">>,
        enabled: !!id,
    });
}
