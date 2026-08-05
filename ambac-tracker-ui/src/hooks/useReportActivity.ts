import { useEffect, useRef } from "react";

/**
 * Report a self-hiding panel's "has content" state up to a parent.
 *
 * Lets a parent gate shared chrome (e.g. a single "Needs attention" heading
 * over several panels) on whether any child actually has content, while each
 * child stays the single source of truth for its own emptiness. Fires only when
 * `active` changes, and always calls the latest `onActivity` via a ref — so a
 * parent passing an inline `(a) => setState(...)` callback can't cause a render
 * loop.
 */
export function useReportActivity(active: boolean, onActivity?: (active: boolean) => void) {
    const ref = useRef(onActivity);
    ref.current = onActivity;
    useEffect(() => {
        ref.current?.(active);
    }, [active]);
}
