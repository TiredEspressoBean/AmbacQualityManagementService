/**
 * The rebuild levels offered for a core of this type, on the part type form. A
 * level always belongs to one core type; its own form holds the repair codes it
 * includes, so rows open it and "New" starts one for this type.
 */
import { Link } from "@tanstack/react-router";
import { Pencil, Plus } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useRetrieveRebuildScopePresets } from "@/hooks/useRebuildScopePresets";
import { useAllows } from "@/pages/scheduling/setup/shared";

export function RebuildLevelsPanel({ partTypeId }: { partTypeId: string }) {
    const allows = useAllows();
    const { data, isLoading } = useRetrieveRebuildScopePresets({ core_type: partTypeId, limit: 100 });
    const levels = data?.results ?? [];

    return (
        <Card>
            <CardHeader>
                <div className="flex items-start justify-between gap-2">
                    <div>
                        <CardTitle className="text-lg">Rebuild levels</CardTitle>
                        <CardDescription>
                            The depths of rebuild offered for a core of this type, and the repair codes
                            each starts with. Leave empty for part types that aren't cores.
                        </CardDescription>
                    </div>
                    {allows("add_rebuildscopepreset") && (
                        <Button asChild size="sm" variant="outline" className="shrink-0">
                            <Link to="/editor/rebuild-levels/new" search={{ core_type: partTypeId } as never}>
                                <Plus className="mr-1 h-4 w-4" /> New level
                            </Link>
                        </Button>
                    )}
                </div>
            </CardHeader>
            <CardContent>
                {isLoading ? (
                    <p className="text-sm text-muted-foreground">Loading…</p>
                ) : levels.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No rebuild levels for this type.</p>
                ) : (
                    <ul className="divide-y">
                        {levels.map((l) => (
                            <li key={l.id} className="flex items-center gap-3 py-2">
                                <span className="flex-1 font-medium">{l.name}</span>
                                {l.is_default && <Badge variant="secondary">Default</Badge>}
                                <span className="text-sm tabular-nums text-muted-foreground">
                                    {(l.codes ?? []).length} codes
                                </span>
                                <Button asChild variant="ghost" size="icon" title={`Edit ${l.name}`}>
                                    <Link to="/editor/rebuild-levels/$id/edit" params={{ id: l.id }}>
                                        <Pencil className="h-4 w-4" />
                                    </Link>
                                </Button>
                            </li>
                        ))}
                    </ul>
                )}
            </CardContent>
        </Card>
    );
}
