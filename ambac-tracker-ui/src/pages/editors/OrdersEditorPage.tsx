import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage } from "@/pages/editors/ModelEditorPage";
import { useRetrieveOrders } from "@/hooks/useRetrieveOrders";
import { EditOrderActionsCell } from "@/components/edit-orders-action-cell";
import { StatusBadge } from "@/components/ui/status-badge";
import { format } from "date-fns";
import { api } from "@/lib/api/generated";
import type { QueryClient } from "@tanstack/react-query";

// Default params that match what useOrdersList passes on initial render
const DEFAULT_LIST_PARAMS = {
    offset: 0,
    limit: 25,
    search: "",
    archived: false,
    active_pipeline: true,
};

// Prefetch function for route loader
export const prefetchOrdersEditor = (queryClient: QueryClient) => {
    queryClient.prefetchQuery({
        queryKey: ["order", DEFAULT_LIST_PARAMS],
        queryFn: () => api.api_Orders_list(DEFAULT_LIST_PARAMS),
    });
    queryClient.prefetchQuery({
        queryKey: ["metadata", "Orders", "Orders"],
        queryFn: () => api.api_Orders_metadata_retrieve(),
    });
};

function useOrdersList({
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
    return useRetrieveOrders({
        offset,
        limit,
        ordering,
        search,
        archived: false,
        active_pipeline: true,
        ...filters, // Spread filter params into queries
    });
}

export default function OrdersEditorPage() {
    const navigate = useNavigate();

    return (
        <ModelEditorPage
            title="Orders"
            modelName="Orders"
            useList={useOrdersList}
            columns={[
                {
                    header: "Order #",
                    renderCell: (order: any) => (
                        <span className="font-mono text-sm text-primary">{order.order_number || "—"}</span>
                    ),
                    priority: 1,
                },
                { header: "Name", renderCell: (order: any) => order.name, priority: 1 },
                {
                    header: "Status",
                    renderCell: (order: any) => order.order_status
                        ? <StatusBadge status={order.order_status} />
                        : "—",
                    priority: 1,
                },
                { header: "Company", renderCell: (order: any) => order.company_name || "—", priority: 2 },
                {
                    header: "Customer",
                    renderCell: (order: any) =>
                        `${order.customer_first_name || ""} ${order.customer_last_name || ""}`.trim() || "—",
                    priority: 2,
                },
                {
                    header: "Est. Completion",
                    renderCell: (order: any) =>
                        order.estimated_completion
                            ? format(new Date(order.estimated_completion), "MMM d, yyyy")
                            : "—",
                    priority: 4,
                },
            ]}
            renderActions={(order) => <EditOrderActionsCell orderId={order.id} />}
            onCreate={() => navigate({ to: "/OrderForm" })}
        />
    );
}
