import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export function useRetrieveApprovalTemplates(
  queries?: Parameters<typeof api.api_ApprovalTemplates_list>[0],
  options?: Omit<
    UseQueryOptions<
      Awaited<ReturnType<typeof api.api_ApprovalTemplates_list>>,
      Error
    >,
    "queryKey" | "queryFn"
  >
) {
  return useQuery({
    queryKey: ["approval-template", queries],
    queryFn: () => api.api_ApprovalTemplates_list(queries),
    ...options,
  });
}
