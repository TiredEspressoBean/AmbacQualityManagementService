import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

type CreateInput = Parameters<typeof api.api_CalibrationRecords_create>[0];
type CreateResponse = Awaited<ReturnType<typeof api.api_CalibrationRecords_create>>;

export const useCreateCalibrationRecord = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateResponse, unknown, CreateInput>({
        mutationFn: (data) =>
            api.api_CalibrationRecords_create(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["calibration-records"] });
        },
    });
};
