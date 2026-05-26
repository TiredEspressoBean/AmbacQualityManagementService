/**
 * Tenant default channel matrix (admin surface).
 *
 * Backs `TenantNotificationDefault` once Phase 2 ships. Demo state holds
 * overrides in component-local React state; switches update instantly and
 * a "Save changes" button is the contract for when the real mutation
 * endpoint exists.
 *
 * Source: Documents/NOTIFICATION_SYSTEM_DESIGN.md → "Default channel matrix".
 */
import { Link } from "@tanstack/react-router";
import { useState } from "react";
import { ArrowLeft, Bell } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import {
    NotificationChannelMatrix,
    type ChannelMatrixValue,
} from "@/components/notifications/NotificationChannelMatrix";
import type { NotificationChannel } from "@/lib/notifications/eventCatalog";

export function NotificationDefaultsPage() {
    // Demo: local overrides over the registry default_channels. Real
    // implementation reads/writes TenantNotificationDefault rows.
    const [overrides, setOverrides] = useState<ChannelMatrixValue>({});
    const [isDirty, setIsDirty] = useState(false);

    function handleChange(event_code: string, channel: NotificationChannel, enabled: boolean) {
        setOverrides((prev) => ({
            ...prev,
            [event_code]: { ...(prev[event_code] ?? {}), [channel]: enabled },
        }));
        setIsDirty(true);
    }

    function handleSave() {
        // Phase 2: POST /api/notifications/defaults/ with the diff.
        toast.success("Saved (demo — not yet persisted)", {
            description: `${Object.keys(overrides).length} event override(s) staged.`,
        });
        setIsDirty(false);
    }

    function handleReset() {
        setOverrides({});
        setIsDirty(false);
    }

    return (
        <div className="container mx-auto p-6 max-w-5xl">
            <div className="mb-6">
                <Link
                    to="/settings"
                    className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-4"
                >
                    <ArrowLeft className="h-4 w-4 mr-1" />
                    Back to Settings
                </Link>
                <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                        <Bell className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold">Notification Defaults</h1>
                        <p className="text-muted-foreground text-sm">
                            Choose which events and channels are enabled by default for new users.
                            Individual users can override these on their notification preferences page.
                        </p>
                    </div>
                </div>
            </div>

            <Card>
                <CardHeader className="flex flex-row items-start justify-between gap-4">
                    <div>
                        <CardTitle>Default Channels by Event</CardTitle>
                        <CardDescription>
                            Toggle the channels a new user starts subscribed to for each event.
                            Bold rows ship enabled in the starter pack.
                        </CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button variant="outline" onClick={handleReset} disabled={!isDirty}>
                            Reset
                        </Button>
                        <Button onClick={handleSave} disabled={!isDirty}>
                            Save changes
                        </Button>
                    </div>
                </CardHeader>
                <CardContent>
                    <NotificationChannelMatrix
                        value={overrides}
                        onChange={handleChange}
                        fallback={(event, channel) => event.defaultChannels.includes(channel)}
                        columnLabel="Default channels"
                    />
                </CardContent>
            </Card>
        </div>
    );
}
