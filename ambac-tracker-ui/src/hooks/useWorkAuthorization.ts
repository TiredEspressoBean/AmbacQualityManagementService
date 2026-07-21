import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

/**
 * Pre-flight training authorization for a set of parts, for the CURRENT user.
 *
 * Backs the Start-Work gate: instead of only blocking on click (and missing
 * the resume path, where a part already has an execution), the dialog asks up
 * front which parts the operator is qualified to work — so unqualified parts
 * can be MARKED, and Start can route to the block / supervisor-override panel
 * uniformly. `can_override` is the user-level override grant.
 */
export type WorkAuthRow = {
    part: string;
    step: string | null;
    authorized: boolean;
    missing: { training: string; reason: string }[];
};

export function useWorkAuthorization(partIds: string[], enabled: boolean) {
    const parts = partIds.join(",");
    return useQuery({
        queryKey: ["work-authorization", parts] as const,
        queryFn: () =>
            api.api_StepExecutions_work_authorization_retrieve({ queries: { parts } }),
        enabled: enabled && partIds.length > 0,
        staleTime: 30_000,
        retry: false,
    });
}
