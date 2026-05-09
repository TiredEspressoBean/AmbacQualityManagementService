import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

type UpdateCalibrationRecordInput = Parameters<typeof api.api_CalibrationRecords_partial_update>[0];
type UpdateCalibrationRecordConfig = Parameters<typeof api.api_CalibrationRecords_partial_update>[1];
type UpdateCalibrationRecordParams = UpdateCalibrationRecordConfig["params"];
type UpdateCalibrationRecordResponse = Awaited<ReturnType<typeof api.api_CalibrationRecords_partial_update>>;

type UpdateCalibrationRecordVariables = {
    id: UpdateCalibrationRecordParams["id"];
    data: UpdateCalibrationRecordInput;
};

export const useUpdateCalibrationRecord = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateCalibrationRecordResponse, unknown, UpdateCalibrationRecordVariables>({
        mutationFn: ({ id, data }) =>
            api.api_CalibrationRecords_partial_update(data, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: (_, variables) => {
            queryClient.invalidateQueries({ queryKey: ["calibration-records"] });
            queryClient.invalidateQueries({ queryKey: ["calibration-record", variables.id] });
        },
    });
};
