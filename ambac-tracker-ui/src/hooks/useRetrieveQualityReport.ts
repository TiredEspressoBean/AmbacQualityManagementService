import { api } from "@/lib/api/generated";
import { useQuery } from "@tanstack/react-query";

type RetrieveQualityReportResponse = Awaited<ReturnType<typeof api.api_ErrorReports_retrieve>>;

export const useRetrieveQualityReport = (id: string | undefined) => {
    return useQuery<RetrieveQualityReportResponse>({
        queryKey: ["quality-report", id],
        queryFn: () => api.api_ErrorReports_retrieve({ params: { id: id! } }),
        enabled: !!id,
    });
};
