/**
 * Notification preferences card — the simple, customer-friendly entry point
 * for the weekly order digest, shown on `/profile`.
 *
 * Audience: customers who just want "send me a weekly email about my orders."
 * For multi-digest, event-driven, or channel-matrix configuration, the full
 * UI lives at `/profile/notifications`.
 *
 * Surface contract: this card and the "Scheduled digests" section on
 * `/profile/notifications` are two views of the same underlying data —
 * personal NotificationSchedule rows with `provider_kind='customer_active_orders'`.
 * Both write through `usePersonalSchedule*` mutations so cache invalidation
 * propagates between surfaces; the card simply filters to the
 * customer_active_orders one and presents it as a single toggle.
 */
import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";

import { PersonalScheduleSheet } from "@/components/notifications/PersonalScheduleSheet";
import {
    useDeletePersonalSchedule,
    usePersonalSchedules,
    type PersonalSchedule,
} from "@/hooks/notificationSchedules";

const DAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
];

function summarize(schedule: PersonalSchedule): string {
    const time = (schedule.time_of_day ?? "").slice(0, 5);
    if (schedule.cadence === "weekly" && schedule.day_of_week !== null && schedule.day_of_week !== undefined) {
        return `Every ${DAYS[schedule.day_of_week]} at ${time} ${schedule.timezone ?? "UTC"}`;
    }
    if (schedule.cadence === "monthly" && schedule.day_of_month) {
        return `Every month on day ${schedule.day_of_month} at ${time} ${schedule.timezone ?? "UTC"}`;
    }
    return schedule.cadence ?? "";
}

export function NotificationPreferencesCard() {
    const { data, isLoading } = usePersonalSchedules();
    const deleteSchedule = useDeletePersonalSchedule();
    const [sheetOpen, setSheetOpen] = useState(false);

    // Find the customer_active_orders personal schedule — the "weekly orders"
    // subscription this card represents. Customers usually have at most one.
    const ordersSchedule = (data?.results ?? []).find(
        (s) => s.provider_kind === "customer_active_orders",
    );

    if (isLoading) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle>Notification Preferences</CardTitle>
                </CardHeader>
                <CardContent>
                    <Loader2 className="h-6 w-6 animate-spin" />
                </CardContent>
            </Card>
        );
    }

    const handleDisable = () => {
        if (!ordersSchedule) return;
        deleteSchedule.mutate(ordersSchedule.id);
    };

    return (
        <>
            <Card>
                <CardHeader>
                    <CardTitle>Notification Preferences</CardTitle>
                    <CardDescription>
                        Manage your email notifications about your orders.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="flex items-center justify-between gap-4">
                        <div className="flex-1">
                            <h4 className="font-medium">Weekly Order Updates</h4>
                            <p className="text-sm text-muted-foreground">
                                {ordersSchedule ? (
                                    summarize(ordersSchedule)
                                ) : (
                                    "You are not receiving order updates."
                                )}
                            </p>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                            {ordersSchedule && (
                                <Button
                                    variant="ghost"
                                    onClick={handleDisable}
                                    disabled={deleteSchedule.isPending}
                                >
                                    Disable
                                </Button>
                            )}
                            <Button variant="outline" onClick={() => setSheetOpen(true)}>
                                {ordersSchedule ? "Edit" : "Set up"}
                            </Button>
                        </div>
                    </div>

                    <div className="text-xs text-muted-foreground">
                        Want event-driven pings (shipments, holds, NCRs) or other digests?{" "}
                        <Link
                            to="/profile/notifications"
                            className="underline underline-offset-2 hover:text-foreground"
                        >
                            Open My Notifications
                        </Link>
                        .
                    </div>
                </CardContent>
            </Card>

            <PersonalScheduleSheet
                open={sheetOpen}
                onOpenChange={setSheetOpen}
                editingSchedule={ordersSchedule ?? null}
            />
        </>
    );
}
