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
import type { RuleDraft, RuleScope } from "@/lib/notifications/ruleDraft";

export function ScopeCard({
    draft,
    patch,
    lockedScope,
}: {
    draft: RuleDraft;
    patch: (u: Partial<RuleDraft>) => void;
    /** When editing an existing rule, the scope can't change. */
    lockedScope: boolean;
}) {
    const { data: companiesResp } = useRetrieveCompanies();
    const companies = companiesResp?.results ?? [];

    const onScopeChange = (next: RuleScope) => {
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
                    onValueChange={(v) => onScopeChange(v as RuleScope)}
                    className="grid grid-cols-1 md:grid-cols-3 gap-3"
                    disabled={lockedScope}
                >
                    <ScopeOption
                        value="tenant"
                        label="Tenant-wide"
                        hint="Admin-authored. Recipients are users/groups."
                    />
                    <ScopeOption
                        value="customer"
                        label="Customer-scoped"
                        hint="Fires only for events referencing one customer. Can route to ExternalContacts."
                    />
                    <ScopeOption
                        value="personal"
                        label="Personal"
                        hint="Owner is the recipient. Use with `owner_user.id` in the condition."
                    />
                </RadioGroup>

                {lockedScope && (
                    <p className="text-xs text-muted-foreground">
                        Scope is fixed after a rule is created. Make a new rule to change scope.
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

                {draft.scope === "personal" && (
                    <p className="text-xs text-muted-foreground">
                        You're the implicit recipient — no recipient picker needed.
                    </p>
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
    value: RuleScope;
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