import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type CreateInput = Schema<"CalibrationRecordRequest">;
type CreateResponse = Schema<"CalibrationRecord">;

export const useCreateCalibrationRecord = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateResponse, unknown, CreateInput>({
        mutationFn: (data) =>
            api.api_CalibrationRecords_create(data as never, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<CreateResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["calibration-records"] });
        },
    });
};
