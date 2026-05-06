import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage";
import { useTenantGroups } from "@/hooks/useTenantGroups";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Users } from "lucide-react";
import { useNavigate } from "@tanstack/react-router";
import { api } from "@/lib/api/generated";
import type { QueryClient } from "@tanstack/react-query";
import type { Schema } from "@/lib/api/types";

const col = createColumnHelper<Schema<"TenantGroup">>();

// Default params for prefetch
const DEFAULT_LIST_PARAMS = {
    offset: 0,
    limit: 25,
};

// Prefetch function for route loader
export const prefetchGroupsEditor = (queryClient: QueryClient) => {
    queryClient.prefetchQuery({
        queryKey: ["tenantGroups", DEFAULT_LIST_PARAMS],
        queryFn: () => api.api_TenantGroups_list({ queries: DEFAULT_LIST_PARAMS }),
    });
};

function useGroupsList({
    offset,
    limit,
    ordering,
    search,
}: {
    offset: number;
    limit: number;
    ordering?: string;
    search?: string;
    filters?: Record<string, string>;
}) {
    const queries: Parameters<typeof useTenantGroups>[0] = { offset, limit };
    if (ordering !== undefined) queries.ordering = ordering;
    if (search !== undefined) queries.search = search;
    return useTenantGroups(queries);
}

export function GroupsEditorPage() {
    const navigate = useNavigate();

    return (
        <ModelEditorPage
            title="User Groups"
            modelName="TenantGroups"
            useList={useGroupsList}
            sortOptions={[
                { label: "Name (A-Z)", value: "name" },
                { label: "Name (Z-A)", value: "-name" },
                { label: "Newest", value: "-created_at" },
                { label: "Oldest", value: "created_at" },
            ]}
            columns={[
                col({ header: "Name", renderCell: (item) => item.name }),
                col({
                    header: "Type",
                    renderCell: (item) => (
                        <Badge variant={item.is_custom ? "secondary" : "outline"}>
                            {item.is_custom ? "Custom" : item.preset_key || "Preset"}
                        </Badge>
                    ),
                }),
                col({
                    header: "Members",
                    renderCell: (item) => (
                        <Badge variant="outline">
                            {item.member_count ?? 0}
                        </Badge>
                    ),
                }),
                col({
                    header: "Permissions",
                    renderCell: (item) => (
                        <Badge variant="secondary">
                            {item.permission_count ?? 0}
                        </Badge>
                    ),
                }),
            ]}
            renderActions={(item) => (
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => navigate({ to: "/editor/groups/$id", params: { id: String(item.id) } })}
                    title="View Group Details"
                >
                    <Users className="h-4 w-4 mr-1" />
                    View
                </Button>
            )}
            showDetailsLink={false}
        />
    );
}
