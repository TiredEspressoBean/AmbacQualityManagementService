import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

type UpdateQuarantineDispositionInput = Parameters<typeof api.api_QuarantineDispositions_partial_update>[0];

type UpdateQuarantineDispositionConfig = Parameters<typeof api.api_QuarantineDispositions_partial_update>[1];
type UpdateQuarantineDispositionParams = UpdateQuarantineDispositionConfig["params"];

type UpdateQuarantineDispositionResponse = Awaited<ReturnType<typeof api.api_QuarantineDispositions_partial_update>>;

type UpdateQuarantineDispositionVariables = {
    id: UpdateQuarantineDispositionParams["id"];
    data: UpdateQuarantineDispositionInput;
};

export const useUpdateQuarantineDisposition = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateQuarantineDispositionResponse, unknown, UpdateQuarantineDispositionVariables>({
        mutationFn: ({ id, data }) =>
            api.api_QuarantineDispositions_partial_update(data, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ["quarantine-dispositions"],
                predicate: (query) => query.queryKey[0] === "quarantine-dispositions",
            });
        },
    });
};