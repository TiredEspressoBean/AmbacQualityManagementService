import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

/**
 * Trigger a wipe + reseed of the demo tenant.
 *
 * Backend: `POST /api/Tenants/{slug}/regenerate-demo-data/` returns 202
 * with a `task_id`. Poll `regenerate-demo-status/{task_id}/` for
 * completion. Refuses on any slug !== 'demo'.
 */

// From the endpoint itself. The hand-written version narrowed status to the
// literal "queued", which the schema does not promise.
export type RegenerateDemoQueued =
    Awaited<ReturnType<typeof api.api_Tenants_regenerate_demo_data_create>>;

type Variables = {
    /** Should always be 'demo'. The endpoint refuses anything else,
     *  but we keep the slug explicit so the call site documents intent. */
    slug: string;
};

export function useRegenerateDemoData() {
    const queryClient = useQueryClient();
    return useMutation<RegenerateDemoQueued, Error, Variables>({
        mutationFn: async ({ slug }) => {
            return api.api_Tenants_regenerate_demo_data_create(undefined, {
                params: { slug },
                headers: { "X-CSRFToken": getCookie("csrftoken") ?? "" },
            });
        },
        onSuccess: () => {
            // After reseed the entire tenant changes — blow the whole
            // cache. The page will re-fetch what it needs.
            queryClient.invalidateQueries();
        },
    });
}

export type RegenerateDemoStatus = {
    task_id: string;
    status: string;
    result?: { ok: boolean; slug: string; notes?: string };
    error?: string;
    progress?: { current: number; total: number; percent: number };
};

export async function fetchRegenerateDemoStatus(
    slug: string,
    taskId: string,
): Promise<RegenerateDemoStatus> {
    // Typed client now that the action declares its payload. It used to
    // respond with only a description and no schema, which generated
    // `unknown` — so this was a raw fetch with the shape hand-written above.
    const body = await api.api_Tenants_regenerate_demo_status_retrieve({
        params: { slug, task_id: taskId },
    });
    return body as RegenerateDemoStatus;
}
