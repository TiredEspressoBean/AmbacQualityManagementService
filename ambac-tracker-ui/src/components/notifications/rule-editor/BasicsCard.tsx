import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { RuleDraft } from "@/lib/notifications/ruleDraft";

export function BasicsCard({
    draft,
    patch,
}: {
    draft: RuleDraft;
    patch: (u: Partial<RuleDraft>) => void;
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
                        placeholder="e.g. QA managers on critical NCRs"
                    />
                </div>
            </CardContent>
        </Card>
    );
}