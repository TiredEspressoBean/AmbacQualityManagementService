import { useQuery, queryOptions } from "@tanstack/react-query"
import { api } from "@/lib/api/generated.ts"
import type { Schema } from "@/lib/api/types";

type ThreeDModelResponse = Schema<"ThreeDModel">;

export const retrieveThreeDModelOptions = (id: string) => queryOptions({
    queryKey: ["threeDModel", id] as const,
    queryFn: () => api.api_ThreeDModels_retrieve({ params: { id } }) as Promise<ThreeDModelResponse>,
});

export function useRetrieveThreeDModel (id: string) {
    return useQuery({
        ...retrieveThreeDModelOptions(id),
        enabled: !!id,
    });
};
