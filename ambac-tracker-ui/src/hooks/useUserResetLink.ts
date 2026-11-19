import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

/** An administrator-issued password reset link for a user: valid once, for the days chosen.
 *  The person opens it on the Reset password page (sign-in never depends on email). */
export function useUserResetLink() {
    return useMutation({
        mutationFn: ({ userId, validDays }: { userId: number; validDays: number }) =>
            api.api_User_reset_link_create({ valid_days: validDays }, { params: { id: userId } }),
        mutationKey: ["user", "reset-link"],
        // The page shows the server's reason itself.
        meta: { suppressGlobalError: true },
    });
}
