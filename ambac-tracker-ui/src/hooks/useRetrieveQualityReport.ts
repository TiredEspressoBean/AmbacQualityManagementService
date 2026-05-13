import { api } from "@/lib/api/generated";
import { useQuery, queryOptions } from "@tanstack/react-query";
import type { Schema } from "@/lib/api/types";

type QualityReportsResponse = Schema<"QualityReports">;

export const retrieveQualityReportOptions = (id: string | undefined) => queryOptions({
    queryKey: ["quality-report", id] as const,
    queryFn: () => api.api_ErrorReports_retrieve({ params: { id: id! } }) as Promise<QualityReportsResponse>,
});

export const useRetrieveQualityReport = (id: string | undefined) => {
    return useQuery({
        ...retrieveQualityReportOptions(id),
        enabled: !!id,
    });
};
