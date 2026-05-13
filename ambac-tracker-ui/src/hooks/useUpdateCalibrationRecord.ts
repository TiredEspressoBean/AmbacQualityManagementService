import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type UpdateCalibrationRecordInput = Schema<"PatchedCalibrationRecordRequest">;
type UpdateCalibrationRecordResponse = Schema<"CalibrationRecord">;

type UpdateCalibrationRecordVariables = {
    id: string;
    data: UpdateCalibrationRecordInput;
};

export const useUpdateCalibrationRecord = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateCalibrationRecordResponse, unknown, UpdateCalibrationRecordVariables>({
        mutationFn: ({ id, data }) =>
            api.api_CalibrationRecords_partial_update(data as never, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<UpdateCalibrationRecordResponse>,
        onSuccess: (_, variables) => {
            queryClient.invalidateQueries({ queryKey: ["calibration-records"] });
            queryClient.invalidateQueries({ queryKey: ["calibration-record", variables.id] });
        },
    });
};
