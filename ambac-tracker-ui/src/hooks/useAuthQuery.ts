// src/lib/hooks/useAuthQuery.ts
import { useQuery } from "@tanstack/react-query"

const token = localStorage.getItem('authToken')

export function useAuthQuery() {
    return useQuery({
        queryKey: ["auth", "me"],
        queryFn: async () => {
            const res = await fetch("/auth/user", {
                method: "GET",
                credentials: "include",
                headers: {
                    "Accept": "application/json",
                    "Authorization": `Token ${token}`,
                },
            })

            if (!res.ok) {
                throw new Error("Not authenticated")
            }

            return res.json()
        },
        staleTime: 1000 * 60 * 5, // cache for 5 minutes
    })
}
