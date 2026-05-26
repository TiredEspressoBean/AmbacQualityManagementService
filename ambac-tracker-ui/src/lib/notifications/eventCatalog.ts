/**
 * Frontend wrapper around the backend's `/api/notifications/events/`
 * endpoint plus per-event metadata the backend doesn't carry today
 * (ack definitions for the escalation "stops when…" copy).
 *
 * Previously this file held a hardcoded 25-event catalog that drifted
 * from the backend `EVENT_REGISTRY`. As of Phase 6, the catalog is
 * fetched live and consumers use the `useNotificationEventCatalog()`
 * hook. Frontend-only metadata (icons, ack copy) lives in this file.
 */

import { useMemo } from "react";

import {
    useNotificationEvents,
    type NotificationEventTypeCatalogEntry,
} from "@/hooks/notificationRules";

export type NotificationChannel = "in_app" | "email";

export interface NotificationEventDescriptor {
    code: string;
    label: string;
    domain: string;
    description: string;
    /** Channels enabled by default for a new tenant. */
    defaultChannels: NotificationChannel[];
    /** Whether the event ships enabled in the starter pack. */
    defaultOn: boolean;
    /**
     * True when the backend ack registry has an ack predicate for this
     * event — meaning the escalation engine knows when to stop a chain.
     * The rule editor uses this to gate the "Enable escalation" toggle:
     * events without ack support can't host an escalation policy because
     * the runner would have no way to know when to stop firing steps.
     */
    supportsEscalation: boolean;
}

export const NOTIFICATION_CHANNELS: { code: NotificationChannel; label: string }[] = [
    { code: "in_app", label: "In-App" },
    { code: "email", label: "Email" },
];

/**
 * Per-event ack-definition copy shown in the rule editor's escalation card
 * ("Stops escalating when: a disposition is logged for this nonconformance").
 *
 * The backend ack registry is the source of truth for which events SUPPORT
 * escalation (via `event.supportsEscalation`); this map provides the
 * user-facing copy *only*. Events that gain ack support on the backend but
 * don't have copy here render a generic fallback ("the source is acked").
 * Add an entry here to customize the wording.
 */
const ACK_DEFINITION_COPY: Record<string, string> = {
    "ncr.opened": "a disposition is logged for this nonconformance",
    "capa.opened": "an action is logged on this CAPA",
    "document.approval_required": "an approver responds",
};

export function ackCopyFor(eventCode: string): string {
    return ACK_DEFINITION_COPY[eventCode] ?? "the source record is acknowledged";
}

/**
 * Convert a backend catalog row (snake_case) to the camelCase descriptor
 * shape components consume. Filters channel codes against the known
 * channel set so an unexpected backend channel string doesn't poison
 * downstream code.
 */
function descriptorFromRow(
    row: NotificationEventTypeCatalogEntry,
): NotificationEventDescriptor {
    return {
        code: row.code,
        label: row.label,
        domain: row.domain,
        description: row.description,
        defaultChannels: (row.default_channels ?? []).filter(
            (c): c is NotificationChannel => c === "in_app" || c === "email",
        ),
        defaultOn: row.default_on,
        supportsEscalation: row.supports_escalation,
    };
}

/**
 * Live event catalog hook. Returns the descriptor list derived from the
 * backend's registered events. Components should handle the loading
 * state (empty array while pending, populated when settled). Cached via
 * React Query at the hook layer with a 1-hour stale time — events don't
 * change at runtime, just on backend deploys.
 */
export function useNotificationEventCatalog(): {
    events: NotificationEventDescriptor[];
    isLoading: boolean;
    error: unknown;
} {
    const { data, isLoading, error } = useNotificationEvents();
    const events = useMemo(
        () => (data ?? []).map(descriptorFromRow),
        [data],
    );
    return { events, isLoading, error };
}

/** Group catalog by domain. Stable key order matches first appearance in catalog. */
export function groupByDomain(
    events: NotificationEventDescriptor[],
): Record<string, NotificationEventDescriptor[]> {
    const grouped: Record<string, NotificationEventDescriptor[]> = {};
    for (const event of events) {
        if (!grouped[event.domain]) grouped[event.domain] = [];
        grouped[event.domain].push(event);
    }
    return grouped;
}
