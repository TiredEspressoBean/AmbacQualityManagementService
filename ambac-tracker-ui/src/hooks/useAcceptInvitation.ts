import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils.ts";

/** Whether an invitation link can still set the account up, asked when the signup page
 *  opens: a replaced, expired or used link says why in place of the form. */
export function useInvitationCheck(token: string | undefined) {
    return useQuery({
        queryKey: ["invitation-check", token],
        queryFn: () =>
            api.api_UserInvitations_validate_token_create({ token: token! }, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        enabled: Boolean(token),
        retry: false,
        staleTime: Infinity,
    });
}

export function useAcceptInvitation() {
    return useMutation({
        mutationFn: (data: { token: string; password: string; opt_in_notifications?: boolean }) =>
            api.api_UserInvitations_accept_create(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        mutationKey: ["user", "accept-invitation"],
        // The page shows the server's reason itself (one message, not two toasts).
        meta: { suppressGlobalError: true },
    });
}