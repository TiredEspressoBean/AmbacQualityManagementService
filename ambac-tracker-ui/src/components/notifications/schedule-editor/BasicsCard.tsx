import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { ScheduleDraft } from "@/lib/notifications/scheduleDraft";

export function BasicsCard({
    draft,
    patch,
}: {
    draft: ScheduleDraft;
    patch: (u: Partial<ScheduleDraft>) => void;
}) {
    return (
        <Card>
            <CardHeader>
                <CardTitle className="text-base">Basics</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="space-y-2">
                    <Label>Name</Label>
                    <Input
                        value={draft.name}
                        onChange={(e) => patch({ name: e.target.value })}
                        placeholder="e.g. Acme weekly order digest"
                    />
                </div>
                <div className="space-y-2">
                    <Label>Description (optional)</Label>
                    <Textarea
                        value={draft.description}
                        onChange={(e) => patch({ description: e.target.value })}
                        placeholder="Notes for other admins about why this schedule exists."
                        rows={2}
                    />
                </div>
            </CardContent>
        </Card>
    );
}
