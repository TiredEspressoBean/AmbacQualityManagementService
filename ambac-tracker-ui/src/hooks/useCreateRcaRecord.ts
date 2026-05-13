import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type CreateRcaRecordInput = Schema<"RcaRecordRequest">;
type CreateRcaRecordResponse = Schema<"RcaRecord">;

export const useCreateRcaRecord = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateRcaRecordResponse, unknown, CreateRcaRecordInput>({
        mutationFn: (data) =>
            api.api_RcaRecords_create(data as never, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<CreateRcaRecordResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["rca-records"] });
            queryClient.invalidateQueries({ queryKey: ["capas"] });
        },
    });
};
