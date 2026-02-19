import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api, type PaginatedUserList } from "@/lib/api/generated.ts";

export function useRetrieveUsers(
  queries?: Parameters<typeof api.api_User_list>[0],
  options?: Omit<
    UseQueryOptions<PaginatedUserList, Error>,
    "queryKey" | "queryFn"
  >
) {
  return useQuery<PaginatedUserList, Error>({
    queryKey: ["user", queries],
    queryFn: () => api.api_User_list(queries),
    ...options,
  });
}
