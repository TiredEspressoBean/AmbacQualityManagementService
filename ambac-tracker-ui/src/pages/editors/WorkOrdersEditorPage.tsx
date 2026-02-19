import { useRetrieveWorkOrders } from "@/hooks/useRetrieveWorkOrders";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage } from "@/pages/editors/ModelEditorPage.tsx";
import { EditWorkOrderActionsCell } from "@/components/edit-work-order-action-cell.tsx";
import { StatusBadge } from "@/components/ui/status-badge";
import { format } from "date-fns";
import { api } from "@/lib/api/generated";
import type { QueryClient } from "@tanstack/react-query";

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
        queryFn: () => api.api_WorkOrders_list(DEFAULT_LIST_PARAMS),
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
    return useRetrieveWorkOrders({
        offset, limit, ordering, search, ...filters,
    });
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
                {
                    header: "ERP ID",
                    priority: 1,
                    renderCell: (workOrder: any) => (
                        <span className="font-mono text-sm">{workOrder.ERP_id || "—"}</span>
                    ),
                },
                {
                    header: "Status",
                    priority: 1,
                    renderCell: (workOrder: any) => {
                        const status = workOrder.workorder_status;
                        if (!status) return "—";
                        return <StatusBadge status={status} />;
                    },
                },
                {
                    header: "Parts",
                    priority: 2,
                    renderCell: (workOrder: any) => workOrder.parts_summary?.total ?? workOrder.parts_count ?? 0,
                },
                {
                    header: "Process",
                    priority: 3,
                    renderCell: (workOrder: any) => workOrder.process_info?.name || "—",
                },
                {
                    header: "Expected",
                    priority: 4,
                    renderCell: (workOrder: any) =>
                        workOrder.expected_completion
                            ? format(new Date(workOrder.expected_completion), "MMM d, yyyy")
                            : "—",
                },
                {
                    header: "Priority",
                    priority: 5,
                    renderCell: (workOrder: any) => {
                        if (!workOrder.priority) return "—";
                        return <StatusBadge status={workOrder.priority} />;
                    },
                },
                {
                    header: "Related Order",
                    priority: 6,
                    renderCell: (workOrder: any) => workOrder.related_order_info?.name || "—",
                },
            ]}
            renderActions={(workOrder) => <EditWorkOrderActionsCell workOrderId={workOrder.id} />}
            onCreate={() => navigate({ to: "/WorkOrderForm/create" })}
        />
    );
}
