import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage";
import { useRetrieveApprovalTemplates, approvalTemplatesOptions, approvalTemplatesMetadataOptions } from "@/hooks/useRetrieveApprovalTemplates";
import { EditApprovalTemplateActionsCell } from "@/components/edit-approval-template-action-cell";
import { Badge } from "@/components/ui/badge";
import type { QueryClient } from "@tanstack/react-query";
import type { Schema } from "@/lib/api/types";

const col = createColumnHelper<Schema<"ApprovalTemplate">>();

// Default params that match what useApprovalTemplatesList passes on initial render
const DEFAULT_LIST_PARAMS = {
    offset: 0,
    limit: 25,
    search: "",
};

// Prefetch function for route loader
export const prefetchApprovalTemplatesEditor = (queryClient: QueryClient) => {
    queryClient.prefetchQuery(approvalTemplatesOptions(DEFAULT_LIST_PARAMS));
    queryClient.prefetchQuery(approvalTemplatesMetadataOptions());
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
    const queries: Parameters<typeof useRetrieveApprovalTemplates>[0] = {
        offset,
        limit,
        ...filters,
    };
    if (ordering !== undefined) queries.ordering = ordering;
    if (search !== undefined) queries.search = search;
    return useRetrieveApprovalTemplates(queries);
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
                col({ header: "Name", renderCell: (item) => item.template_name }),
                col({ header: "Type", renderCell: (item) => item.approval_type_display || item.approval_type }),
                col({ header: "Flow", renderCell: (item) => item.approval_flow_type_display || item.approval_flow_type }),
                col({ header: "Due Days", renderCell: (item) => item.default_due_days }),
                col({
                    header: "Status",
                    renderCell: (item) => (
                        <Badge variant={item.deactivated_at ? "secondary" : "default"}>
                            {item.deactivated_at ? "Inactive" : "Active"}
                        </Badge>
                    ),
                }),
            ]}
            renderActions={(item) => <EditApprovalTemplateActionsCell templateId={item.id} />}
            onCreate={() => navigate({ to: "/ApprovalTemplateForm/create" })}
            showDetailsLink={false}
        />
    );
}
