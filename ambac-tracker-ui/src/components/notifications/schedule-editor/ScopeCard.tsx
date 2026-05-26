import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";

import { useRetrieveCompanies } from "@/hooks/useRetrieveCompanies";
import type { ScheduleDraft, ScheduleScope } from "@/lib/notifications/scheduleDraft";

export function ScopeCard({
    draft,
    patch,
    lockedScope,
    hidePersonal,
}: {
    draft: ScheduleDraft;
    patch: (u: Partial<ScheduleDraft>) => void;
    /** When editing an existing row, scope can't change. */
    lockedScope: boolean;
    /** Hide the Personal option (admin pages only let admins create
     * tenant/customer schedules; personal schedules live on /profile). */
    hidePersonal: boolean;
}) {
    const { data: companiesResp } = useRetrieveCompanies();
    const companies = companiesResp?.results ?? [];

    const onScopeChange = (next: ScheduleScope) => {
        patch({
            scope: next,
            scopeCustomerId:
                next === "customer"
                    ? draft.scopeCustomerId || companies[0]?.id || ""
                    : "",
            recipientExternalIds: next === "customer" ? draft.recipientExternalIds : [],
        });
    };

    return (
        <Card>
            <CardHeader>
                <CardTitle className="text-base">Scope</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                <RadioGroup
                    value={draft.scope}
                    onValueChange={(v) => onScopeChange(v as ScheduleScope)}
                    className="grid grid-cols-1 md:grid-cols-2 gap-3"
                    disabled={lockedScope}
                >
                    <ScopeOption
                        value="tenant"
                        label="Tenant-wide"
                        hint="Admin-authored. Recipients are internal users/groups."
                    />
                    <ScopeOption
                        value="customer"
                        label="Customer-scoped"
                        hint="Routes to one customer's recipients (users, groups, or external contacts)."
                    />
                    {!hidePersonal && (
                        <ScopeOption
                            value="personal"
                            label="Personal"
                            hint="Owner is the implicit recipient."
                        />
                    )}
                </RadioGroup>

                {lockedScope && (
                    <p className="text-xs text-muted-foreground">
                        Scope is fixed after a schedule is created. Make a new schedule to change scope.
                    </p>
                )}

                {draft.scope === "customer" && (
                    <div className="space-y-2">
                        <Label>Customer</Label>
                        <Select
                            value={draft.scopeCustomerId}
                            onValueChange={(v) => patch({ scopeCustomerId: v })}
                        >
                            <SelectTrigger className="max-w-md">
                                <SelectValue placeholder="Select a customer" />
                            </SelectTrigger>
                            <SelectContent>
                                {companies.map((c) => (
                                    <SelectItem key={c.id} value={String(c.id)}>
                                        {c.name}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}

function ScopeOption({
    value,
    label,
    hint,
}: {
    value: ScheduleScope;
    label: string;
    hint: string;
}) {
    return (
        <label className="flex items-start gap-3 cursor-pointer rounded-md border p-3 hover:bg-muted/40 has-[input:checked]:border-primary has-[input:checked]:bg-primary/5">
            <RadioGroupItem value={value} className="mt-0.5" />
            <div>
                <div className="text-sm font-medium">{label}</div>
                <div className="text-xs text-muted-foreground">{hint}</div>
            </div>
        </label>
    );
}
