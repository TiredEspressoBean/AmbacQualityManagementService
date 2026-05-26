/**
 * Reusable events × channels matrix grid.
 *
 * Used by:
 *   - /settings/notifications  → tenant default matrix (admin)
 *   - /profile/notifications   → user's per-channel preferences
 *
 * The component is stateless w.r.t. persistence — callers pass the
 * `value` map and an `onChange` handler. Demo pages use local state;
 * Phase 2 backend swaps to a server-backed mutation.
 */
import { useMemo, useState } from "react";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
    NOTIFICATION_CHANNELS,
    groupByDomain,
    useNotificationEventCatalog,
    type NotificationChannel,
    type NotificationEventDescriptor,
} from "@/lib/notifications/eventCatalog";

/**
 * Channel matrix state shape.
 *
 *   { [event_code]: { [channel]: boolean } }
 *
 * Missing entries default to "use upstream" (tenant default for users;
 * registry default for tenants).
 */
export type ChannelMatrixValue = Record<string, Partial<Record<NotificationChannel, boolean>>>;

interface NotificationChannelMatrixProps {
    /** Per (event, channel) toggle state. */
    value: ChannelMatrixValue;
    /** Called when a toggle flips. Caller persists. */
    onChange: (event_code: string, channel: NotificationChannel, enabled: boolean) => void;
    /**
     * Fallback enabled state when `value[event][channel]` is unset.
     * Tenant default page passes `(event) => event.defaultChannels.includes(channel)`.
     * User preferences page passes the resolved tenant default.
     */
    fallback: (event: NotificationEventDescriptor, channel: NotificationChannel) => boolean;
    /** Header label for the channel columns block ("Default" / "My preference"). */
    columnLabel?: string;
    /** Whether non-default-on events start hidden behind a toggle. */
    hideUncommonByDefault?: boolean;
}

export function NotificationChannelMatrix({
    value,
    onChange,
    fallback,
    columnLabel = "Channels",
    hideUncommonByDefault = true,
}: NotificationChannelMatrixProps) {
    const [showAll, setShowAll] = useState(!hideUncommonByDefault);
    const { events, isLoading } = useNotificationEventCatalog();

    const visibleEvents = useMemo(() => {
        if (showAll) return events;
        return events.filter((e) => e.defaultOn);
    }, [showAll, events]);

    const grouped = useMemo(() => groupByDomain(visibleEvents), [visibleEvents]);
    const domainNames = Object.keys(grouped);

    const resolveEnabled = (event: NotificationEventDescriptor, channel: NotificationChannel): boolean => {
        const explicit = value[event.code]?.[channel];
        return explicit !== undefined ? explicit : fallback(event, channel);
    };

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground">
                    {isLoading
                        ? "Loading events…"
                        : `Showing ${visibleEvents.length} of ${events.length} events.`}
                </p>
                {hideUncommonByDefault && (
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setShowAll((v) => !v)}
                    >
                        {showAll ? "Show only common events" : "Show all events"}
                    </Button>
                )}
            </div>

            <div className="rounded-md border">
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead className="w-[420px]">Event</TableHead>
                            <TableHead colSpan={NOTIFICATION_CHANNELS.length} className="text-center">
                                {columnLabel}
                            </TableHead>
                        </TableRow>
                        <TableRow>
                            <TableHead></TableHead>
                            {NOTIFICATION_CHANNELS.map((c) => (
                                <TableHead key={c.code} className="text-center w-[120px]">
                                    {c.label}
                                </TableHead>
                            ))}
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {domainNames.map((domain) => (
                            <>
                                <TableRow key={`${domain}-header`} className="bg-muted/50">
                                    <TableCell
                                        colSpan={1 + NOTIFICATION_CHANNELS.length}
                                        className="py-2 font-medium text-sm uppercase tracking-wide text-muted-foreground"
                                    >
                                        {domain}
                                    </TableCell>
                                </TableRow>
                                {grouped[domain].map((event) => (
                                    <TableRow key={event.code}>
                                        <TableCell>
                                            <div className="flex flex-col gap-1">
                                                <div className="flex items-center gap-2">
                                                    <span className="font-medium">{event.label}</span>
                                                    {event.defaultOn && (
                                                        <Badge variant="secondary" className="text-xs">
                                                            default on
                                                        </Badge>
                                                    )}
                                                </div>
                                                <p className="text-xs text-muted-foreground">
                                                    {event.description}
                                                </p>
                                                <code className="text-[10px] text-muted-foreground font-mono">
                                                    {event.code}
                                                </code>
                                            </div>
                                        </TableCell>
                                        {NOTIFICATION_CHANNELS.map((c) => (
                                            <TableCell key={c.code} className="text-center">
                                                <Switch
                                                    checked={resolveEnabled(event, c.code)}
                                                    onCheckedChange={(checked) =>
                                                        onChange(event.code, c.code, checked)
                                                    }
                                                    aria-label={`${event.label} ${c.label}`}
                                                />
                                            </TableCell>
                                        ))}
                                    </TableRow>
                                ))}
                            </>
                        ))}
                    </TableBody>
                </Table>
            </div>
        </div>
    );
}
