import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { Schema } from "@/lib/api/types";

type GroupResponse = Schema<"Group">;

export const retrieveGroupOptions = (id: string | undefined) => queryOptions({
  queryKey: ["group", id] as const,
  queryFn: () => api.api_Groups_retrieve({ params: { id: id as never } }) as Promise<GroupResponse>,
});

export const useRetrieveGroup = (
  id: string | undefined,
  options: any = {}
) => {
  return useQuery({
    ...retrieveGroupOptions(id),
    enabled: !!id,
    ...options,
  });
};
