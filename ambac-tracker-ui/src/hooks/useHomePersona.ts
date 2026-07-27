import { useCallback, useEffect, useState } from "react";
import type { AuthUser } from "@/hooks/useAuthUser";
import { candidatePersonas, primaryPersona } from "@/components/home/home-blocks";

/**
 * Per-user home landing preference — which persona surface to show when the
 * account is a member of more than one persona group (a QA-Manager who's also
 * Engineering, a Shift Lead who also inspects). Stored in localStorage, keyed
 * by user pk so a shared machine doesn't leak preferences across accounts.
 *
 * Falls back to primaryPersona (deterministic PERSONA_ORDER match) if:
 *   - no preference is stored yet,
 *   - the stored value is no longer in the user's candidate list (role change).
 */
const STORAGE_KEY = "uqmes.homePersona";

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

    const [selected, setSelected] = useState<string | null>(() => {
        if (user.pk == null) return fallback;
        const stored = readStored(user.pk);
        return stored && candidates.includes(stored) ? stored : fallback;
    });

    // Re-validate on user change (login/logout, role update).
    useEffect(() => {
        if (user.pk == null) return;
        const stored = readStored(user.pk);
        const next = stored && candidates.includes(stored) ? stored : fallback;
        setSelected(next);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [user.pk, candidates.join(","), fallback]);

    const choose = useCallback(
        (persona: string) => {
            if (user.pk == null || !candidates.includes(persona)) return;
            writeStored(user.pk, persona);
            setSelected(persona);
        },
        [user.pk, candidates],
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
