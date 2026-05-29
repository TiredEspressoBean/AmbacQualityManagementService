import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

type ScrapCoreVars = {
    id: string;
    reason?: string;
};

export const useScrapCore = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (vars: ScrapCoreVars) =>
            api.api_Cores_scrap_create(
                { reason: vars.reason ?? "" } as never,
                {
                    params: { id: vars.id },
                    headers: { "X-CSRFToken": getCookie("csrftoken") },
                },
            ),
        onSuccess: () => {
            queryClient.invalidateQueries({
                predicate: (q) => q.queryKey[0] === "cores" || q.queryKey[0] === "core",
            });
        },
    });
};