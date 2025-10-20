import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils.ts";

export function useAcceptInvitation() {
    return useMutation({
        mutationFn: (data: { token: string; password: string; opt_in_notifications?: boolean }) =>
            api.api_UserInvitations_accept_create(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        mutationKey: ["user", "accept-invitation"],
    });
}