import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ReasonActionButton } from "@/components/common/ReasonActionButton";
import { api } from "@/lib/api/generated";
import { usePermissionSet } from "@/hooks/useMyPermissions";

/**
 * What went into this unit — the as-built record: each component fitted, by whom and
 * when, and any taken back out with the reason. A component fitted by mistake (wrong
 * slot, wrong part) is removed here, which frees it to go in elsewhere; the record of
 * both stays (Corrections #23).
 */
export function AsBuiltCard({ partId }: { partId: string }) {
    const { has } = usePermissionSet();
    const { data, isLoading } = useQuery({
        queryKey: ["assembly-usages", partId],
        queryFn: () => api.api_AssemblyUsages_list({ queries: { assembly: partId, limit: 200 } }),
        enabled: !!partId,
    });
    const rows = data?.results ?? [];
    if (isLoading || rows.length === 0) return null;
    const canRemove = has("add_assemblyusage");
    return (
        <Card>
            <CardHeader className="pb-2">
                <CardTitle className="text-base">As built</CardTitle>
                <CardDescription>Components fitted to this unit.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
                {rows.map((u) => (
                    <div key={u.id} className="flex flex-wrap items-center justify-between gap-2 rounded-md border p-2 text-sm">
                        <div className={u.is_installed ? "" : "text-muted-foreground line-through"}>
                            <span className="font-medium">{u.component_label}</span>
                            <span className="ml-2 text-xs text-muted-foreground">
                                fitted {new Date(u.installed_at).toLocaleString()}
                                {u.installed_by_name ? ` by ${u.installed_by_name}` : ""}
                            </span>
                        </div>
                        {u.is_installed ? (
                            canRemove && (
                                <ReasonActionButton
                                    label="Remove" variant="ghost"
                                    title={`Remove ${u.component_label}`}
                                    description={<>Taken back out of the unit: it can then be fitted elsewhere, or here again.
                                        The fitting stays on the as-built record, marked removed, with your reason.</>}
                                    placeholder="Why — e.g. fitted to the wrong slot"
                                    done={`${u.component_label} removed.`}
                                    run={(reason) => api.api_AssemblyUsages_remove_create({ reason }, { params: { id: u.id } })}
                                />
                            )
                        ) : (
                            <Badge variant="outline" title={u.removal_reason || undefined}>
                                Removed{u.removal_reason ? ` — ${u.removal_reason}` : ""}
                            </Badge>
                        )}
                    </div>
                ))}
            </CardContent>
        </Card>
    );
}
