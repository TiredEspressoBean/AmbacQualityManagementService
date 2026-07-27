import { useCallback, useSyncExternalStore } from "react";
import type { AuthUser } from "@/hooks/useAuthUser";
import { candidatePersonas, primaryPersona } from "@/components/home/home-blocks";

/**
 * Per-user home landing preference — which persona surface to show when the
 * account is a member of more than one persona group (a QA-Manager who's also
 * Engineering, a Shift Lead who also inspects). Stored in localStorage, keyed
 * by user pk so a shared machine doesn't leak preferences across accounts.
 *
 * Multiple hook instances stay in sync via a module-scoped subscribe/emit set
 * plus useSyncExternalStore — so the PersonaSwitcher inside QaHomePage can
 * update the persona and Home.tsx (which decides which surface to render)
 * picks up the change and swaps landings.
 *
 * Falls back to primaryPersona (deterministic PERSONA_ORDER match) if:
 *   - no preference is stored yet,
 *   - the stored value is no longer in the user's candidate list (role change).
 */
const STORAGE_KEY = "uqmes.homePersona";
const listeners = new Set<() => void>();

function subscribe(cb: () => void) {
    listeners.add(cb);
    // Cross-tab sync: writing in another tab fires a `storage` event here.
    const onStorage = (e: StorageEvent) => {
        if (e.key === STORAGE_KEY) cb();
    };
    window.addEventListener("storage", onStorage);
    return () => {
        listeners.delete(cb);
        window.removeEventListener("storage", onStorage);
    };
}

function emit() {
    for (const cb of listeners) cb();
}

function readStored(userPk: number | string): string | null {
    try {
        const raw = window.localStorage.getItem(STORAGE_KEY);
        if (!raw) return null;
        const parsed = JSON.parse(raw) as Record<string, string>;
        return parsed[String(userPk)] ?? null;
    } catch {
        return null;
    }
}

function writeStored(userPk: number | string, value: string | null) {
    try {
        const raw = window.localStorage.getItem(STORAGE_KEY);
        const parsed = (raw ? JSON.parse(raw) : {}) as Record<string, string>;
        if (value == null) {
            delete parsed[String(userPk)];
        } else {
            parsed[String(userPk)] = value;
        }
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(parsed));
    } catch {
        // localStorage disabled — non-fatal, just no persistence.
    }
}

export function useHomePersona(user: AuthUser) {
    const candidates = candidatePersonas(user);
    const fallback = primaryPersona(user);
    const pk = user.pk;

    // Read from localStorage on every notification (subscribe/emit). Same key,
    // same value → useSyncExternalStore does its own equality check.
    const stored = useSyncExternalStore(
        subscribe,
        () => (pk != null ? readStored(pk) : null),
        () => null,
    );

    const selected = stored && candidates.includes(stored) ? stored : fallback;

    const choose = useCallback(
        (persona: string) => {
            if (pk == null || !candidates.includes(persona)) return;
            writeStored(pk, persona);
            emit();
        },
        [pk, candidates],
    );

    return {
        /** The persona whose surface should render. */
        persona: selected,
        /** Every persona the user could switch to (>= 1). */
        candidates,
        /** Set the persona (persisted to localStorage under the user's pk). */
        choose,
        /** True when the account has more than one eligible persona. */
        canSwitch: candidates.length > 1,
    };
}
