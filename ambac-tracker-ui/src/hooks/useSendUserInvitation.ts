import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils.ts";

export function useSendUserInvitation() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (userId: number) =>
            api.api_User_send_invitation_create({
                user_id: userId,
            }, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        mutationKey: ["user", "send-invitation"],
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["User"] });
        },
    });
}