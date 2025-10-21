// src/lib/hooks/useAuthQuery.ts
import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/generated"

export function useAuthQuery() {
    return useQuery({
        queryKey: ["auth", "me"],
        queryFn: () => api.auth_user_retrieve(),
        staleTime: 1000 * 60 * 5, // cache for 5 minutes
    })
}
