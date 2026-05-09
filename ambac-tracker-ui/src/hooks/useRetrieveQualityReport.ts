import { api } from "@/lib/api/generated";
import { useQuery } from "@tanstack/react-query";
import type { Schema } from "@/lib/api/types";

type QualityReportsResponse = Schema<"QualityReports">;

export const useRetrieveQualityReport = (id: string | undefined) => {
    return useQuery<QualityReportsResponse>({
        queryKey: ["quality-report", id],
        queryFn: () => api.api_ErrorReports_retrieve({ params: { id: id! } }) as Promise<QualityReportsResponse>,
        enabled: !!id,
    });
};
