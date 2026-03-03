import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

export function useRetrieveCore(
  id: string,
  options?: Omit<
    UseQueryOptions<
      Awaited<ReturnType<typeof api.api_Cores_retrieve>>,
      Error
    >,
    "queryKey" | "queryFn"
  >
) {
  return useQuery({
    queryKey: ["core", id],
    queryFn: () => api.api_Cores_retrieve({ params: { id } }),
    enabled: !!id,
    ...options,
  });
}
