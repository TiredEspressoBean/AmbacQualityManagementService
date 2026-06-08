/**
 * In-memory ring buffer of uncaught errors + unhandled promise rejections.
 *
 * Purpose: when a transient client-side error flashes the UI ("unable to load
 * data" etc.) we can dump the recent entries from the dev console to figure
 * out what fired — most of the time the original error tracing is lost by
 * the time we open DevTools.
 *
 * Usage:
 *   - Module is auto-installed once via the side-effect import in main.tsx.
 *   - From DevTools console: `__errorLog()` to print, `__errorLog.clear()` to reset.
 *   - Buffer size capped at 50; oldest dropped when full.
 */

type ErrorEntry = {
    kind: "error" | "unhandledrejection" | "query" | "mutation";
    ts: string; // ISO
    message: string;
    stack?: string;
    url: string;
    /** For query/mutation errors: the query key or mutation key. */
    source?: string;
    /** Raw error object stashed for inspection (not serialized). */
    raw?: unknown;
};

const MAX_ENTRIES = 50;
const buffer: ErrorEntry[] = [];

function record(entry: ErrorEntry) {
    buffer.push(entry);
    if (buffer.length > MAX_ENTRIES) buffer.shift();
}

function dump() {
    if (buffer.length === 0) {
        // eslint-disable-next-line no-console
        console.log("__errorLog: no entries");
        return;
    }
    // eslint-disable-next-line no-console
    console.groupCollapsed(`__errorLog: ${buffer.length} entries (newest first)`);
    [...buffer].reverse().forEach((e, i) => {
        const head = `#${buffer.length - i} [${e.ts}] (${e.kind})${
            e.source ? ` ${e.source}` : ""
        } ${e.url}`;
        // eslint-disable-next-line no-console
        console.log(`${head}\n  ${e.message}${e.stack ? "\n" + e.stack : ""}`);
        if (e.raw) {
            // eslint-disable-next-line no-console
            console.log("  raw:", e.raw);
        }
    });
    // eslint-disable-next-line no-console
    console.groupEnd();
}

dump.clear = () => {
    buffer.length = 0;
};
dump.entries = () => buffer.slice();

let installed = false;
export function installErrorLog() {
    if (installed || typeof window === "undefined") return;
    installed = true;

    window.addEventListener("error", (event) => {
        record({
            kind: "error",
            ts: new Date().toISOString(),
            message: event.message,
            stack: event.error?.stack,
            url: window.location.href,
        });
    });

    window.addEventListener("unhandledrejection", (event) => {
        const reason = event.reason;
        record({
            kind: "unhandledrejection",
            ts: new Date().toISOString(),
            message:
                reason instanceof Error
                    ? reason.message
                    : typeof reason === "string"
                        ? reason
                        : safeStringify(reason),
            stack: reason instanceof Error ? reason.stack : undefined,
            url: window.location.href,
        });
    });

    // Expose so devs can run `__errorLog()` from the console.
    (window as unknown as { __errorLog: typeof dump }).__errorLog = dump;
}

/** Record a React Query / mutation error so it shows up in __errorLog().
 *  Errors thrown inside queryFn become query state, not unhandled rejections,
 *  so the window-level listeners never see them — call this from the
 *  QueryCache / MutationCache onError hooks. */
export function recordCaughtError(
    kind: "query" | "mutation",
    source: string,
    error: unknown,
) {
    if (typeof window === "undefined") return;
    record({
        kind,
        ts: new Date().toISOString(),
        message:
            error instanceof Error
                ? error.message
                : typeof error === "string"
                    ? error
                    : safeStringify(error),
        stack: error instanceof Error ? error.stack : undefined,
        url: window.location.href,
        source,
        raw: error,
    });
}

function safeStringify(v: unknown) {
    try {
        return JSON.stringify(v);
    } catch {
        return String(v);
    }
}
