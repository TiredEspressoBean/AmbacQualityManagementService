/**
 * Keeping an operator's work in progress when they leave a step.
 *
 * Exit events alone can't be trusted on a shop tablet: a killed browser, a flat
 * battery or a dropped network fires no `pagehide` at all. So the draft is saved
 * WHILE the operator works — `DEBOUNCE_MS` after the last change — and the exits
 * only flush what is still inside that window:
 *
 *   - moving to another substep, or leaving the runtime (the effect cleanup);
 *   - the tab hidden or closed (`visibilitychange`, `pagehide`), with a keepalive
 *     request so it can finish after the page is gone;
 *   - logout: `LogoutMenuItem` awaits `flushDrafts()` before the session ends,
 *     since a save sent after it would be refused.
 *
 * `sendBeacon` isn't used: it can't carry the CSRF header Django requires. The
 * keepalive request goes through the typed client on axios's fetch adapter.
 *
 * A draft records nothing official (Complete step does). A save refused with 403
 * means the step is now someone else's — autosave stops, rather than writing over
 * the new owner's draft.
 */
import { useCallback, useEffect, useRef } from "react";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

export const DEBOUNCE_MS = 1500;

export type DraftPayload = {
    /** The step execution's id — or, for a load's batch substeps, the batch's. */
    executionId: string;
    substepId: string;
    responses: Record<string, unknown>;
    /** Whose draft: a part's step visit (default) or a load (BatchExecution). */
    kind?: "step" | "batch";
};

type SaveResult = { status: number; detail?: string };

function request(d: DraftPayload, keepalive: boolean) {
    const config = {
        params: { id: d.executionId },
        headers: { "X-CSRFToken": getCookie("csrftoken") ?? "" },
        // axios's fetch adapter, for `keepalive`: the request outlives the page.
        ...(keepalive ? { adapter: "fetch" as const, fetchOptions: { keepalive: true } } : {}),
    };
    const body = { substep: d.substepId, responses: d.responses };
    return d.kind === "batch"
        ? api.api_BatchExecutions_save_draft_create(body, config)
        : api.api_StepExecutions_save_draft_create(body, config);
}

async function postDraft(d: DraftPayload, keepalive: boolean): Promise<SaveResult> {
    try {
        await request(d, keepalive);
        return { status: 200 };
    } catch (err) {
        const resp = (err as { response?: { status?: number; data?: { detail?: string } } }).response;
        if (resp?.status) return { status: resp.status, detail: resp.data?.detail };
        // No response: offline, or a keepalive body over the browser's ~64 KB limit,
        // which is refused outright. Send it plainly — fine for every case but the
        // page already closing.
        if (!keepalive) return { status: 0 };
        try {
            await request(d, false);
            return { status: 200 };
        } catch (retry) {
            const r = (retry as { response?: { status?: number; data?: { detail?: string } } }).response;
            return { status: r?.status ?? 0, detail: r?.data?.detail };
        }
    }
}

// Every mounted autosave's flush, so logout can wait for them. Kept on globalThis, not
// in module scope: a dev-server hot update re-runs this module, and an importer still
// holding the old copy would otherwise flush an empty set while the runtime registered
// in the new one — logout ran before the save (walk 2026-11-03).
const g = globalThis as { __uqmesDraftFlushers?: Set<() => Promise<void>> };
const flushers = (g.__uqmesDraftFlushers ??= new Set<() => Promise<void>>());

/** Send every pending draft now. Logout awaits this before ending the session. */
export async function flushDrafts(): Promise<void> {
    await Promise.all([...flushers].map((f) => f().catch(() => undefined)));
}

/**
 * Autosave the current substep's responses. `ready` holds saving off until the
 * stored draft has been loaded — an empty screen saved before then would erase it.
 * `markSaved` records what the server already holds, so loading it doesn't save it
 * straight back.
 */
export function useDraftAutosave({
    current,
    ready,
    onRefused,
    onSignedOut,
    onFailed,
}: {
    current: DraftPayload | null;
    ready: boolean;
    /** 403: the step is now someone else's. Autosave stops. */
    onRefused: (detail: string) => void;
    /** 401: the session ended before the save reached the server. */
    onSignedOut: () => void;
    /** Anything else (offline, a server error): it will be tried again. */
    onFailed: () => void;
}) {
    const saved = useRef(new Map<string, string>());
    const pending = useRef<DraftPayload | null>(null);
    const timer = useRef<number | undefined>(undefined);
    const stopped = useRef(false);
    const callbacks = useRef({ onRefused, onSignedOut, onFailed });
    callbacks.current = { onRefused, onSignedOut, onFailed };

    const key = (d: { executionId: string; substepId: string }) => `${d.executionId}:${d.substepId}`;

    const send = useCallback(async (keepalive: boolean) => {
        window.clearTimeout(timer.current);
        const d = pending.current;
        pending.current = null; // taken synchronously: a second flush finds nothing
        if (!d || stopped.current) return;
        const json = JSON.stringify(d.responses);
        if ((saved.current.get(key(d)) ?? "{}") === json) return;
        const { status, detail } = await postDraft(d, keepalive);
        if (status >= 200 && status < 300) {
            saved.current.set(key(d), json);
        } else if (status === 403) {
            stopped.current = true;
            callbacks.current.onRefused(detail ?? "This step is now someone else's.");
        } else if (status === 401) {
            stopped.current = true;
            callbacks.current.onSignedOut();
        } else {
            // Back in the queue (unless newer entries took its place), so the next
            // change or exit tries again rather than the entry quietly dropping.
            if (!pending.current) pending.current = d;
            callbacks.current.onFailed();
        }
    }, []);

    const markSaved = useCallback((executionId: string, state: Record<string, Record<string, unknown>>) => {
        for (const [substepId, responses] of Object.entries(state)) {
            saved.current.set(key({ executionId, substepId }), JSON.stringify(responses ?? {}));
        }
    }, []);

    // Queue the current substep's responses whenever they change.
    const json = current ? JSON.stringify(current.responses) : null;
    useEffect(() => {
        if (!ready || !current) return;
        pending.current = current;
        window.clearTimeout(timer.current);
        timer.current = window.setTimeout(() => void send(false), DEBOUNCE_MS);
        // eslint-disable-next-line react-hooks/exhaustive-deps -- keyed on the content, not the object
    }, [ready, current?.executionId, current?.substepId, json, send]);

    // Leaving the substep (or the runtime): send what's pending now.
    useEffect(() => () => void send(true), [current?.executionId, current?.substepId, send]);

    // Tab hidden or closed, and logout.
    useEffect(() => {
        const onHide = () => {
            if (document.visibilityState === "hidden") void send(true);
        };
        const onPageHide = () => void send(true);
        document.addEventListener("visibilitychange", onHide);
        window.addEventListener("pagehide", onPageHide);
        const flush = () => send(true);
        flushers.add(flush);
        return () => {
            document.removeEventListener("visibilitychange", onHide);
            window.removeEventListener("pagehide", onPageHide);
            flushers.delete(flush);
        };
    }, [send]);

    return { markSaved };
}
