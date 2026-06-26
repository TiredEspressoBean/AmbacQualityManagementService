import { ZodiosError } from "@zodios/core";
import { ZodError } from "zod";

export type ApiErrorDescription = {
    /** One-line, source-locating summary (method + endpoint). */
    summary: string;
    /** Field-level / message detail. */
    detail?: string;
    /** True for response/body schema-validation failures — the silent class
     *  (HTTP 200 whose body doesn't match the generated Zod schema). */
    isValidation: boolean;
};

/**
 * Turn an API-client error into a readable, source-locating description.
 *
 * The important case is a **Zodios schema-validation failure**: the backend
 * returned an HTTP-200 body that doesn't match the generated Zod schema (e.g.
 * a new required field the running backend doesn't send yet). These surface to
 * React Query as an opaque rejected promise — the UI just shows "no data" with
 * no clue which endpoint or field broke. We pull the endpoint + offending
 * field paths out so the failure is diagnosable.
 *
 * Also handles plain HTTP/network (Axios) errors via duck-typing (no hard
 * axios import). Returns null for anything else — callers fall back to
 * `error.message`.
 */
export function describeApiError(error: unknown): ApiErrorDescription | null {
    if (error instanceof ZodiosError && error.cause instanceof ZodError) {
        const method = (error.config?.method ?? "get").toUpperCase();
        const url = error.config?.url ?? "<unknown>";
        const issues = error.cause.issues
            .map((i) => `${i.path.join(".") || "(root)"}: ${i.message}`)
            .join("; ");
        return {
            summary: `Response schema mismatch — ${method} ${url}`,
            detail: issues,
            isValidation: true,
        };
    }

    // Duck-typed AxiosError (avoids a hard axios import; zodios owns axios).
    const ax = error as {
        isAxiosError?: boolean;
        message?: string;
        response?: { status?: number };
        config?: { method?: string; url?: string };
    };
    if (ax?.isAxiosError) {
        const method = (ax.config?.method ?? "get").toUpperCase();
        const url = ax.config?.url ?? "<unknown>";
        const status = ax.response?.status;
        return {
            summary: status
                ? `HTTP ${status} — ${method} ${url}`
                : `Network error — ${method} ${url}`,
            detail: ax.message,
            isValidation: false,
        };
    }

    return null;
}