import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { apiErrorMentions, apiErrorStatus } from "@/lib/api-error";
import { getCookie } from "@/lib/utils";

/**
 * Add a user as a member of a TenantGroup.
 *
 * Backend: `POST /api/TenantGroups/{id}/members/` with body `{ user_id }`.
 *
 * Treats "already a member" (400 with that error message) as a success so
 * bulk fanouts don't fail when some users are already in the group.
 */
type Variables = {
    /** TenantGroup UUID */
    groupId: string;
    /** User pk (integer) */
    userId: number;
};

export function useAddUserToTenantGroup() {
    const queryClient = useQueryClient();

    return useMutation<unknown, Error, Variables>({
        mutationFn: async ({ groupId, userId }) => {
            try {
                return await api.api_TenantGroups_members_create(
                    { user_id: userId },
                    {
                        params: { id: groupId },
                        headers: { "X-CSRFToken": getCookie("csrftoken") ?? "" },
                    },
                );
            } catch (e) {
                // The action returns 400 both for a bad user and for a user who
                // is already in the group; only the message separates them.
                // Report the second as success so a bulk fanout doesn't flag it.
                if (apiErrorStatus(e) === 400 && apiErrorMentions(e, /already a member/i)) {
                    return { alreadyMember: true };
                }
                throw e;
            }
        },
        onSuccess: () => {
            // Invalidate user lists so any UI showing group chips refreshes.
            queryClient.invalidateQueries({
                predicate: (q) => {
                    const k = q.queryKey?.[0];
                    return k === "user" || k === "User";
                },
            });
            queryClient.invalidateQueries({ queryKey: ["tenantGroups"] });
        },
    });
}
