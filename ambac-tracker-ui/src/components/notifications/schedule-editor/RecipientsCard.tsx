import { useMemo } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MultiPicker } from "@/components/ui/multi-picker";

import { useExternalContacts } from "@/hooks/externalContacts";
import { useRetrieveUsers } from "@/hooks/useRetrieveUsers";
import { useTenantGroups } from "@/hooks/useTenantGroups";
import type { ScheduleDraft } from "@/lib/notifications/scheduleDraft";

export function RecipientsCard({
    draft,
    patch,
}: {
    draft: ScheduleDraft;
    patch: (u: Partial<ScheduleDraft>) => void;
}) {
    const { data: groupsResp } = useTenantGroups();
    const { data: usersResp } = useRetrieveUsers();
    const showExternal = draft.scope === "customer";
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
            </CardContent>
        </Card>
    );
}
