import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";

import type { RuleDraft } from "@/lib/notifications/ruleDraft";

const KNOWN_CHANNELS = ["in_app", "email"] as const;

export function DeliveryCard({
    draft,
    patch,
}: {
    draft: RuleDraft;
    patch: (u: Partial<RuleDraft>) => void;
}) {
    const isChannelOn = (code: string) => draft.channels.includes(code);
    const setChannel = (code: string, on: boolean) => {
        const next = on
            ? [...new Set([...draft.channels, code])]
            : draft.channels.filter((c) => c !== code);
        patch({ channels: next });
    };

    return (
        <Card>
            <CardHeader>
                <CardTitle className="text-base">Delivery</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="space-y-2">
                    <Label>Channels</Label>
                    <div className="flex items-center gap-6">
                        {KNOWN_CHANNELS.map((code) => (
                            <ChannelToggle
                                key={code}
                                label={code === "in_app" ? "In-app" : "Email"}
                                checked={isChannelOn(code)}
                                onChange={(v) => setChannel(code, v)}
                            />
                        ))}
                    </div>
                </div>

                <div className="flex items-center justify-between rounded-md border px-3 py-2">
                    <div>
                        <Label>Active</Label>
                        <p className="text-xs text-muted-foreground">
                            Paused rules don't fire, but history is kept.
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

function ChannelToggle({
    label,
    checked,
    onChange,
}: {
    label: string;
    checked: boolean;
    onChange: (v: boolean) => void;
}) {
    return (
        <label className="flex items-center gap-2 cursor-pointer">
            <Switch checked={checked} onCheckedChange={onChange} />
            <span className="text-sm">{label}</span>
        </label>
    );
}
