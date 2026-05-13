import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { Schema } from "@/lib/api/types";

type UserResponse = Schema<"User">;

export const retrieveUserOptions = (queries: Parameters<typeof api.api_User_retrieve>[0]) => queryOptions({
    queryKey: ["User", queries] as const,
    queryFn: () => api.api_User_retrieve(queries) as Promise<UserResponse>,
});

export function useRetrieveUser(queries: Parameters<typeof api.api_User_retrieve>[0], options?: { enabled?: boolean }){
    return useQuery({ ...retrieveUserOptions(queries), enabled: options?.enabled ?? true });
}