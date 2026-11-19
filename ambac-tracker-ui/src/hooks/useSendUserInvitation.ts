import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils.ts";

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
        onSuccess: () => {
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "User" });
        },
    });
}