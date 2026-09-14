import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { Schema } from "@/lib/api/types";

export const retrieveJobRoleOptions = (id: string) =>
    queryOptions({
        queryKey: ["job-role", id],
        queryFn: () => api.api_JobRoles_retrieve({ params: { id } }) as Promise<Schema<"JobRole">>,
        enabled: !!id,
    });

export function useRetrieveJobRole(id: string) {
    return useQuery(retrieveJobRoleOptions(id));
}
