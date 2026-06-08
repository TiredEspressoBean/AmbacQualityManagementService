import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type UpdateQualityReportInput = Schema<"PatchedQualityReportsRequest">;
type UpdateQualityReportResponse = Schema<"QualityReports">;

type UpdateQualityReportVariables = {
    id: string;
    data: UpdateQualityReportInput;
};

export const useUpdateQualityReport = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateQualityReportResponse, unknown, UpdateQualityReportVariables>({
        mutationFn: ({ id, data }) =>
            api.api_QualityReports_partial_update(data as never, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<UpdateQualityReportResponse>,
        onSuccess: (_data, variables) => {
            queryClient.invalidateQueries({ queryKey: ["quality-reports"] });
            queryClient.invalidateQueries({ queryKey: ["quality-report", variables.id] });
        },
    });
};
