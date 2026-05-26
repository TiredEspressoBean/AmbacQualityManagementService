import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";

import { useScheduledContentProviders } from "@/hooks/notificationSchedules";
import type { ScheduleDraft } from "@/lib/notifications/scheduleDraft";

export function ContentCard({
    draft,
    patch,
}: {
    draft: ScheduleDraft;
    patch: (u: Partial<ScheduleDraft>) => void;
}) {
    const { data: providers } = useScheduledContentProviders();
    const current = providers?.find((p) => p.name === draft.providerKind);

    return (
        <Card>
            <CardHeader>
                <CardTitle className="text-base">Content</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="space-y-2">
                    <Label>Report</Label>
                    <Select
                        value={draft.providerKind}
                        onValueChange={(v) => patch({ providerKind: v, providerParams: {} })}
                    >
                        <SelectTrigger>
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            {(providers ?? []).map((p) => (
                                <SelectItem key={p.name} value={p.name}>
                                    {p.title}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                    {current && (
                        <p className="text-xs text-muted-foreground">{current.description}</p>
                    )}
                </div>

                {draft.scope === "customer" && (
                    <p className="text-xs text-muted-foreground rounded-md border bg-muted/30 px-3 py-2">
                        The customer is auto-passed to the report from this schedule's scope. No extra parameters needed.
                    </p>
                )}
            </CardContent>
        </Card>
    );
}
