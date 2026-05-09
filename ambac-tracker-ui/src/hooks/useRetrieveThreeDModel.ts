import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/generated.ts"
import type { Schema } from "@/lib/api/types";

type ThreeDModelResponse = Schema<"ThreeDModel">;

export function useRetrieveThreeDModel (id: string) {
    return useQuery<ThreeDModelResponse>({
        queryKey: ["threeDModel", id],
        queryFn: () => api.api_ThreeDModels_retrieve({ params: { id } }) as Promise<ThreeDModelResponse>,
        enabled: !!id,
    });
};
