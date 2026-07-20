import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

/**
 * Operators x training-types competency matrix (HR / quality view).
 * Backed by GET /api/CompetenceMatrix/ — gated on view_trainingrecord,
 * so a 403 here means the caller isn't authorized to see the org matrix.
 */
export const trainingMatrixOptions = () => queryOptions({
    queryKey: ["competence-matrix"] as const,
    queryFn: () => api.api_CompetenceMatrix_retrieve(),
    retry: false, // don't hammer on a 403
});

export function useTrainingMatrix() {
    return useQuery(trainingMatrixOptions());
}
