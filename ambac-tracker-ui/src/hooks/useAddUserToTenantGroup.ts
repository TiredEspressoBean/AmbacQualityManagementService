import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

/**
 * Add a user as a member of a TenantGroup.
 *
 * Backend: `POST /api/TenantGroups/{id}/members/` with body `{ user_id }`.
 *
 * Raw fetch (not Zodios) because the OpenAPI inference for this action's
 * request body picked up the default TenantGroupRequest serializer
 * (`{name, description}`) instead of the real `{user_id, facility_id?,
 * company_id?}` payload. Same workaround pattern as
 * `OperatorSubstepRuntimePage::ensure_inspection_qr`.
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
            const r = await fetch(`/api/TenantGroups/${groupId}/members/`, {
                method: "POST",
                credentials: "include",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCookie("csrftoken") ?? "",
                },
                body: JSON.stringify({ user_id: userId }),
            });
            if (r.ok) return r.json();
            // 400 "already a member" — surface as success so bulk fanout
            // doesn't flag it. Caller can branch on the returned shape.
            if (r.status === 400) {
                const body = await r.json().catch(() => null);
                const msg = String(body?.user_id ?? body?.detail ?? "");
                if (/already a member/i.test(msg)) {
                    return { alreadyMember: true };
                }
            }
            const text = await r.text().catch(() => "");
            throw new Error(text || `HTTP ${r.status}`);
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