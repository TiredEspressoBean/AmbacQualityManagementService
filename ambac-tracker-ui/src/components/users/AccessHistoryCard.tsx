/**
 * A person's access changes here: roles granted and removed, and their membership
 * suspended or reinstated. These live on UserRole and TenantMembership, not on the
 * User record, so the record's own History never showed them (Administrator walk).
 */
import { useQuery } from "@tanstack/react-query";
import { formatDistanceToNowStrict } from "date-fns";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api/generated";

type Entry = {
    id: number; action: number; timestamp: string; object_repr?: string | null;
    content_type_name?: string | null;
    changes?: unknown;
    actor_info?: { full_name?: string | null; username?: string | null } | null;
};

const statusChange = (changes: unknown): string | null => {
    const s = (changes as Record<string, unknown> | null)?.status;
    if (!Array.isArray(s) || s.length !== 2) return null;
    const [from, to] = s.map((v) => String(v).toLowerCase());
    if (from === "none") return null;
    return `Membership ${from} → ${to}`;
};

function describe(e: Entry): string | null {
    const model = (e.content_type_name ?? "").toLowerCase().replace(/\s/g, "");
    const repr = e.object_repr ?? "";
    if (model === "userrole") {
        // "dave@x is Shift Lead"
        const role = repr.includes(" is ") ? repr.split(" is ").slice(1).join(" is ") : repr;
        if (e.action === 0) return `Role granted: ${role}`;
        if (e.action === 2) return `Role removed: ${role}`;
        return null;
    }
    if (model === "tenantmembership") {
        if (e.action === 0) return "Added to this company";
        return statusChange(e.changes);
    }
    return null;
}

export function AccessHistoryCard({ userId }: { userId: string }) {
    const { data } = useQuery({
        queryKey: ["user", userId, "access-history"],
        queryFn: () => api.api_User_access_history_list({ params: { id: Number(userId) } }) as Promise<Entry[]>,
        // A grant or suspend made on this page must show without a reload.
        staleTime: 0,
        refetchOnMount: "always",
    });
    const rows = (data ?? []).map((e) => ({ e, text: describe(e) })).filter((r) => r.text);

    return (
        <Card>
            <CardHeader>
                <CardTitle className="text-lg">Access changes</CardTitle>
                <CardDescription>Roles granted and removed, and suspensions, newest first.</CardDescription>
            </CardHeader>
            <CardContent>
                {rows.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No access changes recorded.</p>
                ) : (
                    <ol className="divide-y">
                        {rows.map(({ e, text }) => (
                            <li key={e.id} className="py-2 text-sm">
                                <div>{text}</div>
                                <div className="text-xs text-muted-foreground">
                                    {e.actor_info?.full_name || e.actor_info?.username || "System"} ·{" "}
                                    <span title={new Date(e.timestamp).toLocaleString()}>
                                        {formatDistanceToNowStrict(new Date(e.timestamp), { addSuffix: true })}
                                    </span>
                                </div>
                            </li>
                        ))}
                    </ol>
                )}
            </CardContent>
        </Card>
    );
}
