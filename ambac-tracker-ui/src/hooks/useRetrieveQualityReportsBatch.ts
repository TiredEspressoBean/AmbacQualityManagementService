import { api } from "@/lib/api/generated";
import { useQuery } from "@tanstack/react-query";

type RetrieveQualityReportResponse = Awaited<ReturnType<typeof api.api_ErrorReports_retrieve>>;

export const useRetrieveQualityReportsBatch = (ids: string[]) => {
    return useQuery<RetrieveQualityReportResponse[]>({
        queryKey: ["quality-reports-batch", ids],
        queryFn: async () => {
            if (ids.length === 0) return [];
            return Promise.all(ids.map((id) => api.api_ErrorReports_retrieve({ id })));
        },
        enabled: ids.length > 0,
    });
};
