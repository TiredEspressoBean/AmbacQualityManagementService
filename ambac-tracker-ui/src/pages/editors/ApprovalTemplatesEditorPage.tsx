import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage } from "@/pages/editors/ModelEditorPage";
import { useRetrieveApprovalTemplates } from "@/hooks/useRetrieveApprovalTemplates";
import { EditApprovalTemplateActionsCell } from "@/components/edit-approval-template-action-cell";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api/generated";
import type { QueryClient } from "@tanstack/react-query";

// Default params that match what useApprovalTemplatesList passes on initial render
const DEFAULT_LIST_PARAMS = {
    offset: 0,
    limit: 25,
    search: "",
};

// Prefetch function for route loader
export const prefetchApprovalTemplatesEditor = (queryClient: QueryClient) => {
    queryClient.prefetchQuery({
        queryKey: ["approval-template", DEFAULT_LIST_PARAMS],
        queryFn: () => api.api_ApprovalTemplates_list(DEFAULT_LIST_PARAMS),
    });
    queryClient.prefetchQuery({
        queryKey: ["metadata", "ApprovalTemplates", "ApprovalTemplates"],
        queryFn: () => api.api_ApprovalTemplates_metadata_retrieve(),
    });
};

function useApprovalTemplatesList({
    offset,
    limit,
    ordering,
    search,
    filters,
}: {
    offset: number;
    limit: number;
    ordering?: string;
    search?: string;
    filters?: Record<string, string>;
}) {
    return useRetrieveApprovalTemplates({
        offset,
        limit,
        ordering,
        search,
        ...filters,
    });
}

export function ApprovalTemplatesEditorPage() {
    const navigate = useNavigate();

    return (
        <ModelEditorPage
            title="Approval Templates"
            modelName="ApprovalTemplates"
            useList={useApprovalTemplatesList}
            sortOptions={[
                { label: "Name (A-Z)", value: "template_name" },
                { label: "Name (Z-A)", value: "-template_name" },
                { label: "Type (A-Z)", value: "approval_type" },
                { label: "Type (Z-A)", value: "-approval_type" },
            ]}
            columns={[
                { header: "Name", renderCell: (item: any) => item.template_name },
                { header: "Type", renderCell: (item: any) => item.approval_type_display || item.approval_type },
                { header: "Flow", renderCell: (item: any) => item.approval_flow_type_display || item.approval_flow_type },
                { header: "Due Days", renderCell: (item: any) => item.default_due_days },
                {
                    header: "Status",
                    renderCell: (item: any) => (
                        <Badge variant={item.deactivated_at ? "secondary" : "default"}>
                            {item.deactivated_at ? "Inactive" : "Active"}
                        </Badge>
                    ),
                },
            ]}
            renderActions={(item) => <EditApprovalTemplateActionsCell templateId={item.id} />}
            onCreate={() => navigate({ to: "/ApprovalTemplateForm/create" })}
            showDetailsLink={false}
        />
    );
}
