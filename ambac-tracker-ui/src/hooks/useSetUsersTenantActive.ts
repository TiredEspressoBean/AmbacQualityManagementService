import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

/**
 * Activate / deactivate users **within the current tenant** via
 * POST /api/User/bulk-activate/. This suspends or reactivates the user's
 * per-tenant membership — it does NOT touch the global `User.is_active`
 * account flag (that is reserved for platform admins via Django admin).
 *
 * Works for a single user (pass one id) or a bulk selection. The backend
 * skips the requesting user, so `updated_count` may be less than the number
 * of ids submitted.
 */
type SetActiveResponse = {
    detail?: string;
    updated_count?: number;
    is_active?: boolean;
};

type SetActiveVariables = {
    userIds: number[];
    isActive: boolean;
};

export const useSetUsersTenantActive = () => {
    const queryClient = useQueryClient();

    return useMutation<SetActiveResponse, unknown, SetActiveVariables>({
        mutationFn: ({ userIds, isActive }) =>
            api.api_User_bulk_activate_create(
                { user_ids: userIds, is_active: isActive },
                { headers: { "X-CSRFToken": getCookie("csrftoken") } },
            ) as Promise<SetActiveResponse>,
        onSuccess: () => {
            // The list hook keys on lowercase ["user"]; other user queries use
            // ["User"]. Invalidate both spellings.
            queryClient.invalidateQueries({
                predicate: (query) =>
                    query.queryKey[0] === "User" || query.queryKey[0] === "user",
            });
        },
    });
};
