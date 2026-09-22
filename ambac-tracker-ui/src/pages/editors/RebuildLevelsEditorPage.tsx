import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage";
import {
    useRetrieveRebuildScopePresets, rebuildScopePresetsOptions,
} from "@/hooks/useRebuildScopePresets";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { QueryClient } from "@tanstack/react-query";
import type { Schema } from "@/lib/api/types";
import { Pencil } from "lucide-react";

const col = createColumnHelper<Schema<"RebuildScopePreset">>();

const DEFAULT_LIST_PARAMS = { offset: 0, limit: 25, search: "" };

export const prefetchRebuildLevelsEditor = (queryClient: QueryClient) => {
    queryClient.prefetchQuery(rebuildScopePresetsOptions(DEFAULT_LIST_PARAMS));
};

function useRebuildLevelsList({
    offset, limit, ordering, search, filters,
}: {
    offset: number; limit: number; ordering?: string; search?: string;
    filters?: Record<string, string>;
}) {
    return useRetrieveRebuildScopePresets({ offset, limit, ordering, search, ...filters });
}

export function RebuildLevelsEditorPage() {
    const navigate = useNavigate();

    return (
        <ModelEditorPage
            title="Rebuild Levels"
            modelName="RebuildScopePresets"
            useList={useRebuildLevelsList}
            sortOptions={[
                { label: "Name (A-Z)", value: "name" },
                { label: "Name (Z-A)", value: "-name" },
            ]}
            columns={[
                col({ header: "Level", priority: 1, renderCell: (item) => item.name }),
                col({
                    header: "Core type",
                    priority: 1,
                    renderCell: (item) => item.core_type_name || "—",
                }),
                col({
                    header: "Default",
                    priority: 2,
                    // At most one per core type, enforced by a partial unique index —
                    // this column is how an engineer sees which one that is.
                    renderCell: (item) =>
                        item.is_default ? (
                            <Badge>Proposed automatically</Badge>
                        ) : (
                            <span className="text-muted-foreground">—</span>
                        ),
                }),
                col({
                    header: "Includes",
                    priority: 2,
                    renderCell: (item) => {
                        const codes = item.code_labels ?? [];
                        if (codes.length === 0) {
                            return (
                                <span className="text-sm text-muted-foreground">
                                    base scope only
                                </span>
                            );
                        }
                        return <span className="font-mono text-sm">{codes.join(", ")}</span>;
                    },
                }),
            ]}
            renderActions={(item) => (
                <Button
                    size="icon"
                    variant="ghost"
                    onClick={() => navigate({ to: `/editor/rebuild-levels/${item.id}/edit` })}
                    aria-label={`Edit ${item.name}`}
                >
                    <Pencil className="h-4 w-4" />
                </Button>
            )}
            onCreate={() => navigate({ to: "/editor/rebuild-levels/new" })}
        />
    );
}
