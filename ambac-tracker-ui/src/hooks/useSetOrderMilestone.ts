import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

type SetMilestoneInput = Parameters<typeof api.api_Orders_set_milestone_partial_update>[0];
type SetMilestoneConfig = Parameters<typeof api.api_Orders_set_milestone_partial_update>[1];
type SetMilestoneParams = SetMilestoneConfig["params"];
type SetMilestoneResponse = Awaited<ReturnType<typeof api.api_Orders_set_milestone_partial_update>>;

type SetMilestoneVariables = {
    orderId: SetMilestoneParams["id"];
    data: SetMilestoneInput;
};

export const useSetOrderMilestone = () => {
    const queryClient = useQueryClient();

    return useMutation<SetMilestoneResponse, unknown, SetMilestoneVariables>({
        mutationFn: ({ orderId, data }) =>
            api.api_Orders_set_milestone_partial_update(data, {
                params: { id: orderId },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["Orders"] });
            queryClient.invalidateQueries({ queryKey: ["trackerOrders"] });
        },
    });
};
