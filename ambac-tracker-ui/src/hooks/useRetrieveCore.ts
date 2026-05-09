import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { Schema } from "@/lib/api/types";

type CoreResponse = Schema<"Core">;

export function useRetrieveCore(
  id: string,
  options?: Omit<UseQueryOptions<CoreResponse, Error>, "queryKey" | "queryFn">
) {
  return useQuery<CoreResponse, Error>({
    queryKey: ["core", id],
    queryFn: () => api.api_Cores_retrieve({ params: { id } }) as Promise<CoreResponse>,
    enabled: !!id,
    ...options,
  });
}
