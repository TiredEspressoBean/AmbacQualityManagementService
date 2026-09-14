/**
 * Narrowing for values thrown by the Zodios/axios client.
 *
 * A thrown value is `unknown`, and reading `e.response.status` off it needs
 * either several `in` checks or a cast. Several call sites picked the cast and
 * suppressed the lint rule for it; this puts the checks in one place instead so
 * they can be written once and honestly.
 *
 * Note a Zod validation failure has no `.response` at all -- it is thrown
 * client-side after a 200. `describeApiError` reports those as "no response",
 * which is the distinction worth keeping: a server rejection and a
 * contract mismatch need different fixes.
 */

function record(value: unknown): Record<string, unknown> | undefined {
    return typeof value === "object" && value !== null
        ? (value as Record<string, unknown>)
        : undefined;
}

/** HTTP status, or undefined when the failure never reached the server. */
export function apiErrorStatus(e: unknown): number | undefined {
    const status = record(record(e)?.response)?.status;
    return typeof status === "number" ? status : undefined;
}

/** The server's response body, if there was one. */
export function apiErrorBody(e: unknown): unknown {
    return record(record(e)?.response)?.data;
}

/**
 * Best available human-readable reason. Prefers DRF's `detail`, falls back to
 * the whole body, then to the thrown value's own message.
 */
export function describeApiError(e: unknown, maxLength = 200): string {
    const status = apiErrorStatus(e);
    if (status !== undefined) {
        const body = apiErrorBody(e);
        const detail =
            typeof body === "string" ? body : record(body)?.detail ?? JSON.stringify(body ?? {});
        return `HTTP ${status}: ${String(detail).slice(0, maxLength)}`;
    }
    const message = record(e)?.message;
    return typeof message === "string" ? `no response (${message})` : String(e);
}

/**
 * Does this error's body mention `pattern` anywhere obvious? Used to tell one
 * 400 from another when the backend distinguishes them only by message --
 * e.g. members POST returns 400 both for a bad user and for "already a member".
 */
export function apiErrorMentions(e: unknown, pattern: RegExp): boolean {
    const body = apiErrorBody(e);
    if (typeof body === "string") return pattern.test(body);
    const asRecord = record(body);
    if (!asRecord) return false;
    return Object.values(asRecord).some((v) => pattern.test(String(v)));
}
