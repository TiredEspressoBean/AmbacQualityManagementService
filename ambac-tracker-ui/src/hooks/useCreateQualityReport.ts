import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

// 1️⃣ Infer the exact "body" type that your create endpoint wants:
type CreateQualityReportInput = Parameters<typeof api.api_ErrorReports_create>[0];

// 2️⃣ (Optionally) infer the return type, if you need it:
type CreateQualityReportResponse = Awaited<ReturnType<typeof api.api_ErrorReports_create>>;

export const useCreateQualityReport = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateQualityReportResponse, unknown, CreateQualityReportInput>({
        mutationFn: (data) =>
            api.api_ErrorReports_create(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["quality-reports"] });
        },
    });
};