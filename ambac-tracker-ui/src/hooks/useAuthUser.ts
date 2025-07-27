// src/hooks/useAuthUser.ts
import { useQuery } from '@tanstack/react-query'
import { getCookie } from '@/lib/utils'

export function useAuthUser() {
    return useQuery({
        queryKey: ['authUser'],
        queryFn: async () => {
            const res = await fetch('/auth/user/', {
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken') ?? '',
                },
            })
            if (!res.ok) throw new Error('Not authenticated')
            return res.json()
        },
        staleTime: 5 * 60 * 1000, // optional: treat as fresh for 5 minutes
        retry: false,             // optional: don’t retry if unauthenticated
    })
}
