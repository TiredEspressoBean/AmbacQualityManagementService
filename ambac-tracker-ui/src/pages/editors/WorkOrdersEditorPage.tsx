import { useRetrieveWorkOrders } from "@/hooks/useRetrieveWorkOrders";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage.tsx";
import { EditWorkOrderActionsCell } from "@/components/edit-work-order-action-cell.tsx";
import { StatusBadge } from "@/components/ui/status-badge";
import { format } from "date-fns";
import { api } from "@/lib/api/generated";
import type { QueryClient } from "@tanstack/react-query";
import type { Schema } from "@/lib/api/types";
import type { operations } from "@/lib/api/generated-types";

const col = createColumnHelper<Schema<"WorkOrder">>();

type WorkOrdersListQueries = NonNullable<operations["api_WorkOrders_list"]["parameters"]["query"]>;

// Default params that match what useWorkOrdersList passes on initial render
const DEFAULT_LIST_PARAMS = {
    offset: 0,
    limit: 25,
    search: "",
};

// Prefetch function for route loader
export const prefetchWorkOrdersEditor = (queryClient: QueryClient) => {
    queryClient.prefetchQuery({
        queryKey: ["work_orders", DEFAULT_LIST_PARAMS],
        queryFn: () => api.api_WorkOrders_list({ queries: DEFAULT_LIST_PARAMS } as never),
    });
    queryClient.prefetchQuery({
        queryKey: ["metadata", "WorkOrders", "WorkOrders"],
        queryFn: () => api.api_WorkOrders_metadata_retrieve(),
    });
};

// Custom wrapper hook for consistent usage
function useWorkOrdersList({
                               offset, limit, ordering, search, filters,
                           }: {
    offset: number; limit: number; ordering?: string; search?: string; filters?: Record<string, string>;
}) {
    // Build the queries object incrementally so optional fields are simply
    // absent rather than `key: undefined` — `exactOptionalPropertyTypes: true`
    // rejects the latter when assigning into the strict openapi-typescript
    // queries shape.
    const queries: WorkOrdersListQueries = {
        offset,
        limit,
        ...filters,
    };
    if (ordering !== undefined) queries.ordering = ordering;
    if (search !== undefined) queries.search = search;
    return useRetrieveWorkOrders(queries);
}

export function WorkOrdersEditorPage() {
    const navigate = useNavigate();

    return (
        <ModelEditorPage
            title="Work Orders"
            modelName="WorkOrders"
            showDetailsLink={true}
            useList={useWorkOrdersList}
            columns={[
                col({
                    header: "ERP ID",
                    priority: 1,
                    renderCell: (workOrder) => (
                        <span className="font-mono text-sm">{workOrder.ERP_id || "—"}</span>
                    ),
                }),
                col({
                    header: "Status",
                    priority: 1,
                    renderCell: (workOrder) => {
                        const status = workOrder.workorder_status;
                        if (!status) return "—";
                        return <StatusBadge status={status} />;
                    },
                }),
                col({
                    header: "Parts",
                    priority: 2,
                    renderCell: (workOrder) => workOrder.parts_summary?.total ?? workOrder.parts_count ?? 0,
                }),
                col({
                    header: "Process",
                    priority: 3,
                    renderCell: (workOrder) => workOrder.process_info?.name || "—",
                }),
                col({
                    header: "Expected",
                    priority: 4,
                    renderCell: (workOrder) =>
                        workOrder.expected_completion
                            ? format(new Date(workOrder.expected_completion), "MMM d, yyyy")
                            : "—",
                }),
                col({
                    header: "Priority",
                    priority: 5,
                    renderCell: (workOrder) => {
                        if (!workOrder.priority) return "—";
                        return <StatusBadge status={workOrder.priority} />;
                    },
                }),
                col({
                    header: "Related Order",
                    priority: 6,
                    renderCell: (workOrder) => workOrder.related_order_info?.name || "—",
                }),
            ]}
            renderActions={(workOrder) => <EditWorkOrderActionsCell workOrderId={workOrder.id} />}
            onCreate={() => navigate({ to: "/WorkOrderForm/create" })}
        />
    );
}
