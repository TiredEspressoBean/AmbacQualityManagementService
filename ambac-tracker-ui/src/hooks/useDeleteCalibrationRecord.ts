import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

export const useDeleteCalibrationRecord = () => {
    const queryClient = useQueryClient();

    return useMutation<void, unknown, { id: string }>({
        mutationFn: ({ id }) =>
            api.api_CalibrationRecords_destroy(
                { params: { id } },
                { headers: { "X-CSRFToken": getCookie("csrftoken") } }
            ),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["calibration-records"] });
        },
    });
};
