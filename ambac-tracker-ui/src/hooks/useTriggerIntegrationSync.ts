import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

type TriggerSyncParams = Parameters<typeof api.api_integrations_trigger_sync_create>[1]["params"];

export const useTriggerIntegrationSync = () => {
    const queryClient = useQueryClient();

    return useMutation<any, unknown, { id: TriggerSyncParams["id"] }>({
        mutationFn: ({ id }) =>
            api.api_integrations_trigger_sync_create(undefined, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["integrations-catalog"] });
            queryClient.invalidateQueries({ queryKey: ["integration"] });
        },
    });
};
