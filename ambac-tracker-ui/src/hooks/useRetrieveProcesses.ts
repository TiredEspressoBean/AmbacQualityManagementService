import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

export function useRetrieveProcesses(
  queries?: Parameters<typeof api.api_Processes_list>[0],
  options?: Omit<
    UseQueryOptions<
      Awaited<ReturnType<typeof api.api_Processes_list>>,
      Error
    >,
    "queryKey" | "queryFn"
  >
) {
  return useQuery({
    queryKey: ["process", queries],
    queryFn: () => api.api_Processes_list(queries),
    ...options,
  });
}