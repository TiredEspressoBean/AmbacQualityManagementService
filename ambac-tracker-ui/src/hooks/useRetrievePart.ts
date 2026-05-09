import { api } from "@/lib/api/generated.ts"
import {useQuery} from "@tanstack/react-query";
import type { Schema } from "@/lib/api/types";

type PartsResponse = Schema<"Parts">;

export function useRetrievePart(
    query: Parameters<typeof api.api_Parts_retrieve>[0],
    options?: { enabled?: boolean }
) {
    return useQuery<PartsResponse>({
        queryKey: ["parts", query],
        queryFn: () => api.api_Parts_retrieve(query) as Promise<PartsResponse>,
        enabled: options?.enabled ?? true,
    });
}