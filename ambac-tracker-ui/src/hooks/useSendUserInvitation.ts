import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils.ts";

/** The user list reads ["user", …]; the generated hooks use ["User", …]: refresh both. */
const isUserQuery = (q: { queryKey: readonly unknown[] }) => q.queryKey[0] === "User" || q.queryKey[0] === "user";

export function useSendUserInvitation() {
    const queryClient = useQueryClient();

    return useMutation({
        // A user id (the default lifetime), or the id and how many days the link works.
        mutationFn: (arg: number | { userId: number; validDays?: number }) =>
            api.api_User_send_invitation_create({
                user_id: typeof arg === "number" ? arg : arg.userId,
                ...(typeof arg !== "number" && arg.validDays ? { valid_days: arg.validDays } : {}),
            }, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        mutationKey: ["user", "send-invitation"],
        // The page answers every outcome itself (a pending link, "already set up").
        meta: { suppressGlobalError: true },
        onSettled: () => {
            queryClient.invalidateQueries({ predicate: isUserQuery });
        },
    });
}

/** Resend: a new invitation link for the days chosen; the old one stops working. */
export function useResendUserInvitation() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ userId, validDays }: { userId: number; validDays?: number }) =>
            api.api_UserInvitations_resend_create({
                user_id: userId,
                ...(validDays ? { valid_days: validDays } : {}),
            }, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        mutationKey: ["user", "resend-invitation"],
        meta: { suppressGlobalError: true },
        onSettled: () => {
            queryClient.invalidateQueries({ predicate: isUserQuery });
        },
    });
}
