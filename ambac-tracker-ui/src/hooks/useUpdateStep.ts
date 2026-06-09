import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type UpdateStepInput = Schema<"PatchedStepsRequest">;
type UpdateStepResponse = Schema<"Steps">;

type UpdateStepVariables = {
    id: string;
    data: UpdateStepInput;
    /**
     * Process version this edit is scoped to. When supplied, the backend
     * versions the Step row AND repoints that process's ProcessStep
     * junction at the new version — leaving every other process version
     * referencing the old Step row. Required to make edits visible on
     * the editing DRAFT without affecting the approved baseline.
     */
    processId?: string;
};

export const useUpdateStep = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateStepResponse, unknown, UpdateStepVariables>({
        mutationFn: ({ id, data, processId }) =>
            api.api_Steps_partial_update(data as never, {
                params: { id },
                queries: processId ? { process: processId } : undefined,
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<UpdateStepResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ["step"],
                predicate: (query) => query.queryKey[0] === "step",
            });
        },
    });
};
