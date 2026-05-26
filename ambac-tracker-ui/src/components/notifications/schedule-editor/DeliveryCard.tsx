import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";

import type { ScheduleDraft } from "@/lib/notifications/scheduleDraft";

export function DeliveryCard({
    draft,
    patch,
}: {
    draft: ScheduleDraft;
    patch: (u: Partial<ScheduleDraft>) => void;
}) {
    return (
        <Card>
            <CardHeader>
                <CardTitle className="text-base">Delivery</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="space-y-2">
                    <Label>Channels</Label>
                    <p className="text-xs text-muted-foreground">
                        Email only at launch. In-app delivery for scheduled reports lands in a follow-up.
                    </p>
                </div>

                <div className="flex items-center justify-between rounded-md border px-3 py-2">
                    <div>
                        <Label>Active</Label>
                        <p className="text-xs text-muted-foreground">
                            Disabled schedules don't fire, but history is kept.
                        </p>
                    </div>
                    <Switch
                        checked={draft.enabled}
                        onCheckedChange={(v) => patch({ enabled: v })}
                    />
                </div>
            </CardContent>
        </Card>
    );
}
