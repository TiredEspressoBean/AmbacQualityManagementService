import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

type CreateRcaRecordInput = Parameters<typeof api.api_RcaRecords_create>[0];
type CreateRcaRecordResponse = Awaited<ReturnType<typeof api.api_RcaRecords_create>>;

export const useCreateRcaRecord = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateRcaRecordResponse, unknown, CreateRcaRecordInput>({
        mutationFn: (data) =>
            api.api_RcaRecords_create(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["rca-records"] });
            queryClient.invalidateQueries({ queryKey: ["capas"] });
        },
    });
};
