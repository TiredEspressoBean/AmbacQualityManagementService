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
/** A value the client refused to SEND: zodios checks a request's body, query and path
 *  against the generated schema before it goes out ("Zodios: Invalid Body parameter
 *  'body'"), so nothing reaches the server and there is no DRF message to read. The
 *  response-side failure ("Invalid response from endpoint …") is a different thing — a
 *  contract bug, not a user's input — and is left to `describeApiError`. */
function isRequestValidationError(error: unknown): error is ZodiosError & { cause: ZodError } {
    return error instanceof ZodiosError && error.cause instanceof ZodError
        && /^Zodios: Invalid (Body|Query|Path|Header) parameter/.test(error.message);
}

/** "demand_time_fence_days" → "Demand time fence days". */
const fieldLabel = (path: (string | number)[]) => {
    const name = path.filter((p) => typeof p === "string").join(" ").replace(/_/g, " ").trim();
    return name ? name.charAt(0).toUpperCase() + name.slice(1) : "";
};

/** One schema issue as a sentence a user can act on. */
function issueText(issue: ZodError["issues"][number]): string {
    const what = (() => {
        switch (issue.code) {
            case "too_big": {
                const n = Number(issue.maximum);
                if (issue.type === "string") return `at most ${n} characters`;
                if (issue.type === "array") return `at most ${n} items`;
                return issue.inclusive ? `at most ${n}` : `less than ${n}`;
            }
            case "too_small": {
                const n = Number(issue.minimum);
                if (issue.type === "string") return n <= 1 ? "required" : `at least ${n} characters`;
                if (issue.type === "array") return `at least ${n} items`;
                return issue.inclusive ? `at least ${n}` : `more than ${n}`;
            }
            case "invalid_enum_value":
                return `must be one of ${issue.options.join(", ")}`;
            case "invalid_type":
                return issue.received === "undefined" || issue.received === "null"
                    ? "required" : `must be a ${issue.expected}`;
            case "invalid_string":
                return issue.validation === "email" ? "must be an email address" : "isn't valid";
            default:
                return issue.message;
        }
    })();
    const label = fieldLabel(issue.path);
    return label ? `${label}: ${what}` : what.charAt(0).toUpperCase() + what.slice(1);
}

/** The fields the client wouldn't send, as sentences — or undefined if `error` isn't one. */
export function requestValidationMessage(error: unknown): string | undefined {
    if (!isRequestValidationError(error)) return undefined;
    return error.cause.issues.map(issueText).join("; ") || undefined;
}

export function describeApiError(error: unknown): ApiErrorDescription | null {
    if (isRequestValidationError(error)) {
        const method = (error.config?.method ?? "get").toUpperCase();
        const url = error.config?.url ?? "<unknown>";
        return {
            summary: `Request not sent: a value fails the schema — ${method} ${url}`,
            detail: requestValidationMessage(error),
            isValidation: true,
        };
    }
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
/** A DRF error body: `{field: ["message", ...]}`, or `{detail: "message"}`,
 *  or one-off keys like `{invitation_url: "..."}`. Values are deliberately
 *  `unknown` — the shape varies per endpoint, so reading one goes through
 *  `apiErrorField` below rather than being asserted. */
export type ApiErrorBody = Record<string, unknown>;

/**
 * Pull the parsed error body off an Axios-style rejection.
 *
 * Four call sites each wrote `(error as any)?.response?.data`, with a disable
 * comment saying narrowing would be too verbose. It is verbose — once. Doing it
 * here means `any` doesn't leak into four components, where it silently opts
 * every subsequent property read out of checking.
 *
 * Duck-typed rather than importing axios, matching describeApiError above.
 */
export function apiErrorBody(error: unknown): ApiErrorBody | undefined {
    if (!error || typeof error !== "object") return undefined;
    const response = (error as { response?: unknown }).response;
    if (!response || typeof response !== "object") return undefined;
    const data = (response as { data?: unknown }).data;
    if (!data || typeof data !== "object") return undefined;
    return data as ApiErrorBody;
}

/**
 * Read one field's message out of an error body.
 *
 * DRF sends field errors as arrays (`{"old_password": ["Too short."]}`) but
 * plain strings for one-off keys (`{"invitation_url": "https://..."}`), so both
 * are handled. Returns undefined rather than throwing on any other shape — an
 * error handler that itself throws replaces a useful message with a blank
 * screen.
 */
export function apiErrorField(body: ApiErrorBody | undefined, field: string): string | undefined {
    const value = body?.[field];
    if (typeof value === "string") return value;
    if (Array.isArray(value) && typeof value[0] === "string") return value[0];
    return undefined;
}

/**
 * The server's own sentence for a failed request, for a toast or an inline alert.
 *
 * Without it a refusal reads "Request failed with status code 400" — axios's message —
 * and a deliberate "Self-approval is not permitted" looks like the app breaking. DRF
 * puts the sentence in `detail` (a string, or a list), `non_field_errors`, or under a
 * field name; a list is joined rather than shown as one. Undefined when the body carries
 * no message (a network error, a 500 page), so callers fall back to their own wording.
 */
export function apiErrorMessage(error: unknown): string | undefined {
    // Refused before it was sent — "Demand time fence days: at most 365", not zodios's
    // "Invalid Body parameter 'body'".
    const local = requestValidationMessage(error);
    if (local) return local;
    const body = apiErrorBody(error);
    if (!body) return undefined;
    const text = (v: unknown): string | undefined => {
        if (typeof v === "string") return v || undefined;
        if (Array.isArray(v)) {
            const parts = v.filter((x): x is string => typeof x === "string" && x !== "");
            return parts.length ? parts.join(" ") : undefined;
        }
        return undefined;
    };
    const top = text(body.detail) ?? text(body.non_field_errors);
    // A refusal with `blockers` names its causes there; `detail` is only the headline.
    // Returning `detail` alone used to drop the reasons — the FPI sign-off showed a
    // headline and discarded the quarantine and the out-of-spec reading behind it.
    // Reasons the headline already states aren't repeated.
    const reasons = apiErrorBlockers(error).filter((b) => !top?.includes(b));
    if (top && reasons.length) return `${top.replace(/[.:]\s*$/, "")}: ${reasons.join("; ")}`;
    if (top) return top;
    if (reasons.length) return reasons.join("; ");
    for (const [field, value] of Object.entries(body)) {
        if (field === "blockers") continue;
        const msg = text(value);
        // The reason a correction asks for is a sentence on its own ("Say why…"); its
        // field name added nothing but "edit reason:" (walk 2026-10-26).
        if (msg) return field === "detail" || field === "edit_reason" ? msg : `${field.replace(/_/g, " ")}: ${msg}`;
    }
    return undefined;
}

/**
 * The reasons a refusal gives, for a screen that lists them. The server sends them as
 * `blockers`: plain strings (FPI sign-off, advancement) or `{code, detail}` objects
 * (work-order release). Empty when there are none.
 */
export function apiErrorBlockers(error: unknown): string[] {
    const raw = apiErrorBody(error)?.blockers;
    if (!Array.isArray(raw)) return [];
    return raw
        .map((b): string | undefined => {
            if (typeof b === "string") return b;
            if (b && typeof b === "object") {
                const o = b as { detail?: unknown; message?: unknown };
                if (typeof o.detail === "string") return o.detail;
                if (typeof o.message === "string") return o.message;
            }
            return undefined;
        })
        .filter((x): x is string => !!x);
}
