import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

/**
 * Look up the PCR that owns a given DRAFT process (if any).
 *
 * Used by `ProcessFlowPage` to show a provenance banner when the user
 * lands on a DRAFT that was forked via "Propose Change". A draft can
 * own at most one open PCR (the one that created it).
 */
export function usePcrForDraftProcess(processId: string | undefined) {
    return useQuery({
        queryKey: ["pcr-for-draft", processId] as const,
        enabled: !!processId,
        queryFn: async () => {
            const resp = (await (api as {
                api_process_change_requests_list: (args: {
                    queries: { draft_process_version: string };
                }) => Promise<{ results?: unknown[] } | unknown[]>;
            }).api_process_change_requests_list({
                queries: { draft_process_version: processId! },
            })) as { results?: Array<Record<string, unknown>> } | Array<Record<string, unknown>>;
            const items = Array.isArray(resp) ? resp : resp.results ?? [];
            return items[0] ?? null;
        },
    });
}
