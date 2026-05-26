/**
 * User's "My Notifications" page.
 *
 * Three sections per Documents/NOTIFICATION_SYSTEM_DESIGN.md:
 *   1. Channel preferences (Phase 2)   — mute/unmute per event × channel
 *   2. My subscriptions  (Phase 3)     — personal rules
 *   3. Watched records   (Phase 4)     — followed records
 *
 * Section 2 is the lightest-tier rule-creation surface: a tier-2 user
 * who just wants "ping me when X happens" never sees CEL, scope pickers,
 * or recipient selectors — same data model as the full editor, very
 * different surface.
 */
import { useState } from "react";
import { Bell, BellOff, Bookmark, CalendarClock, Eye, Pencil, Plus, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";

import {
    NotificationChannelMatrix,
    type ChannelMatrixValue,
} from "@/components/notifications/NotificationChannelMatrix";
import { PersonalScheduleSheet } from "@/components/notifications/PersonalScheduleSheet";
import { SubscribeToEventSheet } from "@/components/notifications/SubscribeToEventSheet";

import {
    useDeletePersonalRule,
    usePersonalRules,
    useUpdatePersonalRule,
    type PersonalRule,
} from "@/hooks/notificationRules";
import {
    useDeletePersonalSchedule,
    usePersonalSchedules,
    useUpdatePersonalSchedule,
    type PersonalSchedule,
} from "@/hooks/notificationSchedules";

import {
    useNotificationEventCatalog,
    type NotificationChannel,
} from "@/lib/notifications/eventCatalog";

function channelsToList(value: unknown): string[] {
    return Array.isArray(value)
        ? value.filter((c): c is string => typeof c === "string")
        : [];
}

export function MyNotificationsPage() {
    // Channel-preferences matrix is currently a read-only preview. Wiring it
    // to the per-(event, channel) NotificationPreference API lands in a
    // follow-up — the UI lets users explore the surface but doesn't persist.
    const [overrides, setOverrides] = useState<ChannelMatrixValue>({});

    const { data: personalRulesResp, isLoading } = usePersonalRules();
    const personalRules = personalRulesResp?.results ?? [];

    const updateRule = useUpdatePersonalRule();
    const deleteRule = useDeletePersonalRule();

    const { data: personalSchedulesResp, isLoading: schedulesLoading } =
        usePersonalSchedules();
    const personalSchedules = personalSchedulesResp?.results ?? [];
    const updateSchedule = useUpdatePersonalSchedule();
    const deleteSchedule = useDeletePersonalSchedule();

    const [sheetOpen, setSheetOpen] = useState(false);
    const [editingRule, setEditingRule] = useState<PersonalRule | null>(null);
    const [scheduleSheetOpen, setScheduleSheetOpen] = useState(false);
    const [editingSchedule, setEditingSchedule] = useState<PersonalSchedule | null>(null);

    const openScheduleNew = () => {
        setEditingSchedule(null);
        setScheduleSheetOpen(true);
    };
    const openScheduleEdit = (s: PersonalSchedule) => {
        setEditingSchedule(s);
        setScheduleSheetOpen(true);
    };
    const toggleScheduleEnabled = (s: PersonalSchedule) =>
        updateSchedule.mutate({
            id: s.id,
            data: { enabled: !(s.enabled ?? true) },
        });
    const removeSchedule = (s: PersonalSchedule) => deleteSchedule.mutate(s.id);

    function handleChange(event_code: string, channel: NotificationChannel, enabled: boolean) {
        setOverrides((prev) => ({
            ...prev,
            [event_code]: { ...(prev[event_code] ?? {}), [channel]: enabled },
        }));
    }

    const openSubscribe = () => {
        setEditingRule(null);
        setSheetOpen(true);
    };

    const openEdit = (rule: PersonalRule) => {
        setEditingRule(rule);
        setSheetOpen(true);
    };

    const toggleEnabled = (rule: PersonalRule) =>
        updateRule.mutate({
            id: rule.id,
            data: { enabled: !(rule.enabled ?? true) },
        });

    const removeRule = (rule: PersonalRule) => deleteRule.mutate(rule.id);

    return (
        <div className="container mx-auto p-6 max-w-5xl space-y-6">
            <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                    <Bell className="h-5 w-5 text-primary" />
                </div>
                <div>
                    <h1 className="text-2xl font-bold">My Notifications</h1>
                    <p className="text-muted-foreground text-sm">
                        Control which events reach you and how. Defaults come from your organization;
                        anything you toggle here overrides the default for your account only.
                    </p>
                </div>
            </div>

            {/* Section 1: Channel preferences (Phase 2) */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <BellOff className="h-4 w-4" />
                        Channel preferences
                        <Badge variant="outline" className="ml-1 text-[10px] font-normal">
                            preview
                        </Badge>
                    </CardTitle>
                    <CardDescription>
                        Toggle which channels you want for each event. Off = muted; on = delivered.
                        Persistence to the per-event preference API lands in a follow-up — toggles
                        here don't save yet.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <NotificationChannelMatrix
                        value={overrides}
                        onChange={handleChange}
                        fallback={(event, channel) => event.defaultChannels.includes(channel)}
                        columnLabel="My preference"
                    />
                </CardContent>
            </Card>

            {/* Section 2: My subscriptions */}
            <Card>
                <CardHeader className="flex flex-row items-start justify-between gap-4">
                    <div>
                        <CardTitle className="flex items-center gap-2">
                            <Bookmark className="h-4 w-4" />
                            My subscriptions
                        </CardTitle>
                        <CardDescription>
                            Get pinged when specific things happen — like NCRs assigned to you,
                            or critical CAPAs on your work orders.
                        </CardDescription>
                    </div>
                    <Button variant="outline" onClick={openSubscribe}>
                        <Plus className="h-4 w-4 mr-2" />
                        Subscribe to event
                    </Button>
                </CardHeader>
                <CardContent>
                    {isLoading ? (
                        <p className="text-sm text-muted-foreground py-6 text-center">
                            Loading…
                        </p>
                    ) : personalRules.length === 0 ? (
                        <div className="rounded-md border border-dashed py-10 text-center text-muted-foreground">
                            <p className="text-sm font-medium">No subscriptions yet</p>
                            <p className="text-xs mt-1">
                                Click "Subscribe to event" to follow your first one.
                            </p>
                        </div>
                    ) : (
                        <ul className="space-y-2">
                            {personalRules.map((rule) => (
                                <SubscriptionRow
                                    key={rule.id}
                                    rule={rule}
                                    onEdit={() => openEdit(rule)}
                                    onDelete={() => removeRule(rule)}
                                    onToggle={() => toggleEnabled(rule)}
                                />
                            ))}
                        </ul>
                    )}
                </CardContent>
            </Card>

            {/* Section 3: Scheduled digests (personal schedules) */}
            <Card>
                <CardHeader className="flex flex-row items-start justify-between gap-4">
                    <div>
                        <CardTitle className="flex items-center gap-2">
                            <CalendarClock className="h-4 w-4" />
                            Scheduled digests
                        </CardTitle>
                        <CardDescription>
                            Recurring email summaries delivered on a cadence you choose. Off by default — turn one on if you want a weekly or monthly update.
                        </CardDescription>
                    </div>
                    <Button variant="outline" onClick={openScheduleNew}>
                        <Plus className="h-4 w-4 mr-2" />
                        Schedule a digest
                    </Button>
                </CardHeader>
                <CardContent>
                    {schedulesLoading ? (
                        <p className="text-sm text-muted-foreground py-6 text-center">
                            Loading…
                        </p>
                    ) : personalSchedules.length === 0 ? (
                        <div className="rounded-md border border-dashed py-10 text-center text-muted-foreground">
                            <p className="text-sm font-medium">No scheduled digests yet</p>
                            <p className="text-xs mt-1">
                                Click "Schedule a digest" to set one up.
                            </p>
                        </div>
                    ) : (
                        <ul className="space-y-2">
                            {personalSchedules.map((s) => (
                                <ScheduleRow
                                    key={s.id}
                                    schedule={s}
                                    onEdit={() => openScheduleEdit(s)}
                                    onDelete={() => removeSchedule(s)}
                                    onToggle={() => toggleScheduleEnabled(s)}
                                />
                            ))}
                        </ul>
                    )}
                </CardContent>
            </Card>

            {/* Section 4: Watched records (Phase 4 placeholder) */}
            <Card className="opacity-75">
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Eye className="h-4 w-4" />
                        Watched records
                    </CardTitle>
                    <CardDescription>
                        Records you've followed. You get notified on every event fired against them.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="rounded-md border border-dashed py-12 text-center text-muted-foreground">
                        <p className="text-sm font-medium">Coming in Phase 4</p>
                        <p className="text-xs mt-1">
                            Click "Watch" on any order, NCR, or CAPA detail page to follow it here.
                        </p>
                    </div>
                </CardContent>
            </Card>

            <SubscribeToEventSheet
                open={sheetOpen}
                onOpenChange={setSheetOpen}
                editingRule={editingRule}
            />
            <PersonalScheduleSheet
                open={scheduleSheetOpen}
                onOpenChange={setScheduleSheetOpen}
                editingSchedule={editingSchedule}
            />
        </div>
    );
}

function SubscriptionRow({
    rule,
    onEdit,
    onDelete,
    onToggle,
}: {
    rule: PersonalRule;
    onEdit: () => void;
    onDelete: () => void;
    onToggle: () => void;
}) {
    const { events } = useNotificationEventCatalog();
    const event = events.find((e) => e.code === rule.event_code);
    const channels = channelsToList(rule.channels);
    return (
        <li className="flex items-center gap-3 rounded-md border p-3">
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                    <button
                        className="font-medium text-sm text-left hover:underline"
                        onClick={onEdit}
                    >
                        {rule.name}
                    </button>
                    <Badge variant="outline" className="text-[10px]">
                        {event?.label ?? rule.event_code ?? "—"}
                    </Badge>
                </div>
                <div className="flex items-center gap-2 mt-1 flex-wrap">
                    {rule.conditions_source ? (
                        <code className="text-[11px] bg-muted px-1.5 py-0.5 rounded font-mono break-all">
                            {rule.conditions_source}
                        </code>
                    ) : (
                        <span className="text-xs text-muted-foreground">
                            fires on every event
                        </span>
                    )}
                </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
                <div className="flex gap-1">
                    {channels.includes("in_app") && (
                        <Badge variant="secondary" className="text-[10px]">In-app</Badge>
                    )}
                    {channels.includes("email") && (
                        <Badge variant="secondary" className="text-[10px]">Email</Badge>
                    )}
                </div>
                <Switch checked={rule.enabled ?? true} onCheckedChange={onToggle} />
                <Button size="icon" variant="ghost" onClick={onEdit} aria-label="Edit">
                    <Pencil className="h-4 w-4" />
                </Button>
                <Button size="icon" variant="ghost" onClick={onDelete} aria-label="Delete">
                    <Trash2 className="h-4 w-4" />
                </Button>
            </div>
        </li>
    );
}

const DAYS_OF_WEEK_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function scheduleCadenceSummary(s: PersonalSchedule): string {
    const time = (s.time_of_day ?? "").slice(0, 5);
    if (s.cadence === "weekly" && s.day_of_week !== null && s.day_of_week !== undefined) {
        return `${DAYS_OF_WEEK_SHORT[s.day_of_week]} ${time} ${s.timezone ?? "UTC"}`;
    }
    if (s.cadence === "monthly" && s.day_of_month) {
        return `Day ${s.day_of_month} ${time} ${s.timezone ?? "UTC"}`;
    }
    return s.cadence ?? "—";
}

function ScheduleRow({
    schedule,
    onEdit,
    onDelete,
    onToggle,
}: {
    schedule: PersonalSchedule;
    onEdit: () => void;
    onDelete: () => void;
    onToggle: () => void;
}) {
    return (
        <li className="flex items-center gap-3 rounded-md border p-3">
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                    <button
                        className="font-medium text-sm text-left hover:underline"
                        onClick={onEdit}
                    >
                        {schedule.name}
                    </button>
                    <Badge variant="outline" className="text-[10px] capitalize">
                        {schedule.cadence}
                    </Badge>
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                    {scheduleCadenceSummary(schedule)}
                </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
                <Badge variant="secondary" className="text-[10px]">Email</Badge>
                <Switch checked={schedule.enabled ?? true} onCheckedChange={onToggle} />
                <Button size="icon" variant="ghost" onClick={onEdit} aria-label="Edit">
                    <Pencil className="h-4 w-4" />
                </Button>
                <Button size="icon" variant="ghost" onClick={onDelete} aria-label="Delete">
                    <Trash2 className="h-4 w-4" />
                </Button>
            </div>
        </li>
    );
}

export default MyNotificationsPage;
