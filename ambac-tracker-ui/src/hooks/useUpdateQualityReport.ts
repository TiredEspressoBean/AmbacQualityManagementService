import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

// 1️⃣ Infer the exact input (body) that the partial-update endpoint wants:
type UpdateQualityReportInput = Parameters<typeof api.api_ErrorReports_partial_update>[0];

// 2️⃣ Infer the shape of the `params` object:
type UpdateQualityReportConfig = Parameters<typeof api.api_ErrorReports_partial_update>[1];
type UpdateQualityReportParams = UpdateQualityReportConfig["params"];

// 3️⃣ Infer the response type, if you need it:
type UpdateQualityReportResponse = Awaited<ReturnType<typeof api.api_ErrorReports_partial_update>>;

// 4️⃣ Compose the variables your hook will accept:
type UpdateQualityReportVariables = {
    id: UpdateQualityReportParams["id"];
    data: UpdateQualityReportInput;
};

export const useUpdateQualityReport = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateQualityReportResponse, unknown, UpdateQualityReportVariables>({
        mutationFn: ({ id, data }) =>
            api.api_ErrorReports_partial_update(data, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: (_data, variables) => {
            queryClient.invalidateQueries({ queryKey: ["quality-reports"] });
            queryClient.invalidateQueries({ queryKey: ["quality-report", variables.id] });
        },
    });
};