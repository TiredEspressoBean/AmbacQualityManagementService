import { useMemo } from "react";
import { Mail } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { MultiPicker } from "@/components/ui/multi-picker";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";

import { useExternalContacts } from "@/hooks/externalContacts";
import { useRetrieveUsers } from "@/hooks/useRetrieveUsers";
import { useTenantGroups } from "@/hooks/useTenantGroups";
import type { RecipientStrategy, RuleDraft } from "@/lib/notifications/ruleDraft";

const STRATEGY_OPTIONS: Array<{
    value: RecipientStrategy;
    label: string;
    description: string;
}> = [
    {
        value: "static",
        label: "Specific people I pick",
        description:
            "Notifications go to the users / groups I list below. The same recipients for every event of this type.",
    },
    {
        value: "from_payload",
        label: "Whoever the event says",
        description:
            "Each event carries its own recipient list (e.g. the approver of a specific request, the assignee of a specific CAPA). Use for per-instance routing where the recipient depends on the source record.",
    },
    {
        value: "union",
        label: "Whoever the event says + people I pick (CCs)",
        description:
            "Domain-driven primary recipients plus my static CCs on top. Use to layer visibility (e.g. CC the QA Manager on every event of this type).",
    },
];

export function RecipientsCard({
    draft,
    patch,
}: {
    draft: RuleDraft;
    patch: (u: Partial<RuleDraft>) => void;
}) {
    const { data: groupsResp } = useTenantGroups();
    const { data: usersResp } = useRetrieveUsers();
    const showExternal = draft.scope === "customer";
    const isPersonal = draft.scope === "personal";
    // Strategy only applies to tenant/customer rules. Personal rules always
    // resolve to the owner, so we hide the strategy selector for them.
    const showStrategy = !isPersonal;
    const showStaticPickers =
        draft.recipientStrategy === "static" || draft.recipientStrategy === "union";
    const showFromPayloadHint = draft.recipientStrategy === "from_payload";

    const { data: externalResp } = useExternalContacts(
        { customer: draft.scopeCustomerId, limit: 200 },
        { enabled: showExternal && Boolean(draft.scopeCustomerId) },
    );

    const groupItems = useMemo(
        () =>
            (groupsResp?.results ?? []).map((g) => ({
                id: String(g.id),
                label: g.name,
            })),
        [groupsResp],
    );

    const userItems = useMemo(
        () =>
            (usersResp?.results ?? []).map((u) => ({
                id: u.id,
                label: `${u.first_name ?? ""} ${u.last_name ?? ""}`.trim() || u.username,
            })),
        [usersResp],
    );

    const externalItems = useMemo(
        () =>
            (externalResp?.results ?? []).map((c) => ({
                id: c.id,
                label: `${c.name} · ${c.email}`,
            })),
        [externalResp],
    );

    return (
        <Card>
            <CardHeader>
                <CardTitle className="text-base">Recipients</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                {showStrategy && (
                    <div className="space-y-2">
                        <Label className="text-sm font-medium">Who gets notified?</Label>
                        <RadioGroup
                            value={draft.recipientStrategy}
                            onValueChange={(v) =>
                                patch({ recipientStrategy: v as RecipientStrategy })
                            }
                            className="space-y-2"
                        >
                            {STRATEGY_OPTIONS.map((opt) => (
                                <label
                                    key={opt.value}
                                    htmlFor={`recipient-strategy-${opt.value}`}
                                    className="flex gap-3 cursor-pointer rounded-md border bg-background p-3 hover:bg-muted/40 transition-colors"
                                >
                                    <RadioGroupItem
                                        value={opt.value}
                                        id={`recipient-strategy-${opt.value}`}
                                        className="mt-0.5"
                                    />
                                    <div className="space-y-0.5">
                                        <div className="text-sm font-medium">{opt.label}</div>
                                        <div className="text-xs text-muted-foreground">
                                            {opt.description}
                                        </div>
                                    </div>
                                </label>
                            ))}
                        </RadioGroup>
                    </div>
                )}

                {showFromPayloadHint && (
                    <div className="rounded-md border border-dashed bg-muted/30 px-3 py-4 text-xs text-muted-foreground flex items-start gap-2">
                        <Mail className="h-4 w-4 mt-0.5 shrink-0" />
                        <div>
                            Recipients come from the event payload at fire time. Domain code
                            (the signal that emits this event) decides who gets notified — for
                            example, the assignee of a specific CAPA or the pending approver
                            of a specific request. Nothing to configure here.
                        </div>
                    </div>
                )}

                {showStaticPickers && (
                    <>
                        {draft.recipientStrategy === "union" && (
                            <div className="text-xs text-muted-foreground">
                                These users/groups are CC'd on every fire alongside the
                                event's primary recipients.
                            </div>
                        )}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <MultiPicker
                                label="Groups"
                                items={groupItems}
                                selected={draft.recipientGroupIds}
                                onChange={(ids) => patch({ recipientGroupIds: ids })}
                            />
                            <MultiPicker
                                label="Users"
                                items={userItems}
                                selected={draft.recipientUserIds}
                                onChange={(ids) => patch({ recipientUserIds: ids })}
                            />
                        </div>
                        {showExternal && (
                            <MultiPicker
                                label="External contacts (this customer)"
                                items={externalItems}
                                selected={draft.recipientExternalIds}
                                onChange={(ids) => patch({ recipientExternalIds: ids })}
                                emptyHint={
                                    draft.scopeCustomerId
                                        ? "No external contacts on this customer yet."
                                        : "Pick a customer first."
                                }
                            />
                        )}
                    </>
                )}
            </CardContent>
        </Card>
    );
}
