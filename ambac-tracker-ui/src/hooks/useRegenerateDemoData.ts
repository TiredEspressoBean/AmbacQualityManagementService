import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

/**
 * Trigger a wipe + reseed of the demo tenant.
 *
 * Backend: `POST /api/Tenants/{slug}/regenerate-demo-data/` returns 202
 * with a `task_id`. Poll `regenerate-demo-status/{task_id}/` for
 * completion. Refuses on any slug !== 'demo'.
 *
 * Raw fetch (not Zodios) — the endpoint takes no JSON body but Zodios
 * insists on body schema validation against the auto-inferred default
 * serializer. Easier to fetch directly.
 */

export type RegenerateDemoQueued = {
    task_id: string;
    status: "queued";
    message: string;
};

type Variables = {
    /** Should always be 'demo'. The endpoint refuses anything else,
     *  but we keep the slug explicit so the call site documents intent. */
    slug: string;
};

export function useRegenerateDemoData() {
    const queryClient = useQueryClient();
    return useMutation<RegenerateDemoQueued, Error, Variables>({
        mutationFn: async ({ slug }) => {
            const r = await fetch(
                `/api/Tenants/${encodeURIComponent(slug)}/regenerate-demo-data/`,
                {
                    method: "POST",
                    credentials: "include",
                    headers: { "X-CSRFToken": getCookie("csrftoken") ?? "" },
                },
            );
            if (r.status === 202) return (await r.json()) as RegenerateDemoQueued;
            const text = await r.text().catch(() => "");
            throw new Error(text || `HTTP ${r.status}`);
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
    const r = await fetch(
        `/api/Tenants/${encodeURIComponent(slug)}/regenerate-demo-status/${encodeURIComponent(taskId)}/`,
        { credentials: "include" },
    );
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
}
