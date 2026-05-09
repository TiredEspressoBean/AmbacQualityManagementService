import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { Schema } from "@/lib/api/types";

type UserResponse = Schema<"User">;

export function useRetrieveUser(
    queries: Parameters<typeof api.api_User_retrieve>[0],
    options?: { enabled?: boolean }
) {
    return useQuery<UserResponse>({
        queryKey: ["User", queries],
        queryFn: () => api.api_User_retrieve(queries) as Promise<UserResponse>,
        enabled: options?.enabled ?? true,
    });
}