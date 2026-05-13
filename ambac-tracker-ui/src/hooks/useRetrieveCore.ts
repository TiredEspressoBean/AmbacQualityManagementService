import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { Schema } from "@/lib/api/types";

type CoreResponse = Schema<"Core">;

export const retrieveCoreOptions = (id: string) => queryOptions({
  queryKey: ["core", id] as const,
  queryFn: () => api.api_Cores_retrieve({ params: { id } }) as Promise<CoreResponse>,
});

export function useRetrieveCore(
  id: string,
  options?: Omit<ReturnType<typeof retrieveCoreOptions>, "queryKey" | "queryFn">
) {
  return useQuery({
    ...retrieveCoreOptions(id),
    enabled: !!id,
    ...options,
  });
}
