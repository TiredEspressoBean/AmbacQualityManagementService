import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { Schema } from "@/lib/api/types";

type GroupResponse = Schema<"Group">;

export const useRetrieveGroup = (
  id: string | undefined,
  options: any = {}
) => {
  return useQuery<GroupResponse>({
    queryKey: ["group", id],
    queryFn: () => api.api_Groups_retrieve({ params: { id: id as never } }) as Promise<GroupResponse>,
    enabled: !!id,
    ...options,
  });
};
