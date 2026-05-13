import { api } from "@/lib/api/generated";
import { useQuery, queryOptions } from "@tanstack/react-query";

export const retrieveQualityReportsBatchOptions = (ids: string[]) => queryOptions({
    queryKey: ["quality-reports-batch", ids] as const,
    queryFn: async () => {
        if (ids.length === 0) return [];
        return Promise.all(ids.map((id) => api.api_ErrorReports_retrieve({ params: { id } })));
    },
});

export const useRetrieveQualityReportsBatch = (ids: string[]) => {
    return useQuery({
        ...retrieveQualityReportsBatchOptions(ids),
        enabled: ids.length > 0,
    });
};
