import { QueryClient, QueryCache, MutationCache } from '@tanstack/react-query'
import { toast } from 'sonner'
import { recordCaughtError } from './error-log'
import { describeApiError } from './api/describeApiError'

/**
 * Enrich the error-log buffer (and, in dev, the console) with a source-locating
 * description — most importantly for Zodios schema-validation failures, which
 * are otherwise an opaque "no data" with no clue which endpoint/field broke.
 * Returns the message recorded into the buffer. The user-facing toast stays
 * friendly; the diagnostic detail goes to `__errorLog()` / the dev console.
 */
function reportApiError(kind: "query" | "mutation", source: string, error: unknown): void {
    const desc = describeApiError(error);
    const enriched = desc
        ? `${desc.summary}${desc.detail ? ` — ${desc.detail}` : ""}`
        : undefined;
    recordCaughtError(kind, source, error, enriched);
    if (desc && import.meta.env.DEV) {
        // eslint-disable-next-line no-console
        console.error(`[API] ${desc.summary}`, desc.detail ?? "", error);
    }
}

/**
 * Meta-aware global handlers.
 *
 * Each query/mutation can tag itself with `meta` to control global behavior:
 *
 *   meta: { errorMessage: "Couldn't save part" }
 *   meta: { successMessage: "Part incremented" }
 *   meta: { suppressGlobalError: true }   // handle locally via onError
 *
 * Default behavior (no meta):
 *   - Errors: toast with the error message
 *   - Success: no toast
 *
 * Why this lives on the cache, not defaultOptions:
 *   - Cache callbacks fire ONCE per mutation regardless of how many observers
 *     subscribe. defaultOptions.onError fires per-observer, causing duplicate
 *     toasts if a mutation is observed by multiple components.
 *   - Cache callbacks have access to the full mutation/query object, including
 *     its meta field.
 */

type QueryMeta = { errorMessage?: string; suppressGlobalError?: boolean };
type MutationMeta = {
    errorMessage?: string;
    successMessage?: string;
    suppressGlobalError?: boolean;
    suppressGlobalSuccess?: boolean;
};

export const queryClient = new QueryClient({
    queryCache: new QueryCache({
        onError: (error, query) => {
            reportApiError("query", JSON.stringify(query.queryKey), error);
            const meta = query.meta as QueryMeta | undefined;
            if (meta?.suppressGlobalError) return;
            toast.error(meta?.errorMessage ?? "Failed to load data", {
                description: error instanceof Error ? error.message : undefined,
            });
        },
    }),
    mutationCache: new MutationCache({
        onError: (error, _vars, _ctx, mutation) => {
            reportApiError(
                "mutation",
                JSON.stringify(mutation.options.mutationKey ?? "anonymous"),
                error,
            );
            const meta = mutation.meta as MutationMeta | undefined;
            if (meta?.suppressGlobalError) return;
            toast.error(meta?.errorMessage ?? "Operation failed", {
                description: error instanceof Error ? error.message : undefined,
            });
        },
        onSuccess: (_data, _vars, _ctx, mutation) => {
            const meta = mutation.meta as MutationMeta | undefined;
            if (meta?.suppressGlobalSuccess) return;
            if (meta?.successMessage) toast.success(meta.successMessage);
        },
    }),
    defaultOptions: {
        queries: {
            staleTime: 60 * 1000,
            gcTime: 5 * 60 * 1000,
            refetchOnWindowFocus: false,
            retry: 1,
            networkMode: 'offlineFirst',
            refetchOnReconnect: true,
        },
    },
})
