// src/lib/hooks/useAuthQuery.ts
import { useQuery, queryOptions } from "@tanstack/react-query"
import { api } from "@/lib/api/generated"
import type { AuthUser } from "./useAuthUser"

export const authQueryOptions = () => queryOptions<AuthUser>({
    queryKey: ["auth", "me"] as const,
    queryFn: () => api.auth_user_retrieve() as Promise<AuthUser>,
});

export function useAuthQuery() {
    return useQuery({
        ...authQueryOptions(),
        staleTime: 1000 * 60 * 5, // cache for 5 minutes
    })
}
