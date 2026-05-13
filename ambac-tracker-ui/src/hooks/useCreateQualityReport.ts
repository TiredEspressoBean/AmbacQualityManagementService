import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type CreateQualityReportInput = Schema<"QualityReportsRequest">;
type CreateQualityReportResponse = Schema<"QualityReports">;

export const useCreateQualityReport = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateQualityReportResponse, unknown, CreateQualityReportInput>({
        mutationFn: (data) =>
            api.api_ErrorReports_create(data as never, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<CreateQualityReportResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["quality-reports"] });
        },
    });
};
