import { useNavigate } from "@tanstack/react-router";
import { useJobRoles } from "@/hooks/useJobRoles";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage";
import { EditJobRoleActionCell } from "@/components/edit-job-role-action-cell";
import { Badge } from "@/components/ui/badge";
import type { Schema } from "@/lib/api/types";

const col = createColumnHelper<Schema<"JobRole">>();

function useJobRolesList({
    offset,
    limit,
    ordering,
    search,
}: {
    offset: number;
    limit: number;
    ordering?: string;
    search?: string;
}) {
    const queries: Parameters<typeof useJobRoles>[0] = { offset, limit };
    if (ordering !== undefined) queries.ordering = ordering;
    if (search !== undefined) queries.search = search;
    return useJobRoles(queries);
}

export function JobRolesPage() {
    const navigate = useNavigate();

    return (
        <ModelEditorPage
            title="Job Roles"
            modelName="JobRole"
            useList={useJobRolesList}
            sortOptions={[
                { label: "Name (A–Z)", value: "name" },
                { label: "Name (Z–A)", value: "-name" },
                { label: "Created (Newest)", value: "-created_at" },
            ]}
            columns={[
                col({
                    header: "Name",
                    renderCell: (role) => role.name || "—",
                }),
                col({
                    header: "Description",
                    renderCell: (role) => role.description || <span className="text-muted-foreground">—</span>,
                }),
                col({
                    header: "Status",
                    renderCell: (role) =>
                        role.active
                            ? <Badge variant="secondary" className="bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">Active</Badge>
                            : <Badge variant="outline">Inactive</Badge>,
                }),
            ]}
            renderActions={(role) => <EditJobRoleActionCell roleId={role.id} />}
            onCreate={() => navigate({ to: "/quality/training/roles/new" })}
            showDetailsLink={false}
        />
    );
}
