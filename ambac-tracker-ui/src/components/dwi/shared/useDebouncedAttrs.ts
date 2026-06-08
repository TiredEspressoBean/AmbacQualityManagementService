import { useCallback, useEffect, useRef } from "react";

export type AttrPartial = Record<string, unknown>;

/** Debounce attr writes so typing doesn't flood the undo stack one keystroke
 * at a time. Caller passes the node's `updateAttributes` from NodeViewProps. */
export function useDebouncedAttrs(
    updateAttributes: (attrs: AttrPartial) => void,
    ms = 250,
) {
    const pendingRef = useRef<AttrPartial>({});
    const timerRef = useRef<number | null>(null);

    useEffect(() => {
        return () => {
            if (timerRef.current != null) window.clearTimeout(timerRef.current);
        };
    }, []);

    return useCallback(
        (partial: AttrPartial) => {
            pendingRef.current = { ...pendingRef.current, ...partial };
            if (timerRef.current != null) window.clearTimeout(timerRef.current);
            timerRef.current = window.setTimeout(() => {
                updateAttributes(pendingRef.current);
                pendingRef.current = {};
                timerRef.current = null;
            }, ms);
        },
        [updateAttributes, ms],
    );
}
