import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export const useRetrieveGroups = (
  params?: Parameters<typeof api.api_Groups_list>[0],
  options: any = {}
) => {
  return useQuery({
    queryKey: ["groups", params],
    queryFn: () => api.api_Groups_list(params),
    ...options,
  });
};