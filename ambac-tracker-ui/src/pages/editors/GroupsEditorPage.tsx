import { ModelEditorPage } from "@/pages/editors/ModelEditorPage";
import { useTenantGroups } from "@/hooks/useTenantGroups";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Users } from "lucide-react";
import { useNavigate } from "@tanstack/react-router";
import { api } from "@/lib/api/generated";
import type { QueryClient } from "@tanstack/react-query";

// Default params for prefetch
const DEFAULT_LIST_PARAMS = {
    offset: 0,
    limit: 25,
};

// Prefetch function for route loader
export const prefetchGroupsEditor = (queryClient: QueryClient) => {
    queryClient.prefetchQuery({
        queryKey: ["tenantGroups", DEFAULT_LIST_PARAMS],
        queryFn: () => api.api_TenantGroups_list(DEFAULT_LIST_PARAMS),
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
    return useTenantGroups({
        offset,
        limit,
        ordering,
        search,
    });
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
                { header: "Name", renderCell: (item: any) => item.name },
                {
                    header: "Type",
                    renderCell: (item: any) => (
                        <Badge variant={item.is_custom ? "secondary" : "outline"}>
                            {item.is_custom ? "Custom" : item.preset_key || "Preset"}
                        </Badge>
                    ),
                },
                {
                    header: "Members",
                    renderCell: (item: any) => (
                        <Badge variant="outline">
                            {item.member_count ?? 0}
                        </Badge>
                    ),
                },
                {
                    header: "Permissions",
                    renderCell: (item: any) => (
                        <Badge variant="secondary">
                            {item.permission_count ?? 0}
                        </Badge>
                    ),
                },
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
