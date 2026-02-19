import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export const useRetrieveGroup = (
  id: string | undefined,
  options: any = {}
) => {
  return useQuery({
    queryKey: ["group", id],
    queryFn: () => api.api_Groups_retrieve({ params: { id } }),
    enabled: !!id,
    ...options,
  });
};
