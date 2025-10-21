// src/hooks/useAuthUser.ts
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api/generated'

export function useAuthUser() {
    return useQuery({
        queryKey: ['authUser'],
        queryFn: () => api.auth_user_retrieve(),
        staleTime: 5 * 60 * 1000, // optional: treat as fresh for 5 minutes
        retry: false,             // optional: don't retry if unauthenticated
    })
}
