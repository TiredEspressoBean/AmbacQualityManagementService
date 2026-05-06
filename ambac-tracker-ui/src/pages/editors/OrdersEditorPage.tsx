import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage";
import { useRetrieveOrders } from "@/hooks/useRetrieveOrders";
import { EditOrderActionsCell } from "@/components/edit-orders-action-cell";
import { StatusBadge } from "@/components/ui/status-badge";
import { format } from "date-fns";
import { api } from "@/lib/api/generated";
import type { QueryClient } from "@tanstack/react-query";
import type { Schema } from "@/lib/api/types";
import type { operations } from "@/lib/api/generated-types";

const col = createColumnHelper<Schema<"Orders">>();

type OrdersListQueries = NonNullable<operations["api_Orders_list"]["parameters"]["query"]>;

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
        queryFn: () => api.api_Orders_list({ queries: DEFAULT_LIST_PARAMS } as never),
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
    // Build the queries object incrementally so optional fields are simply
    // absent rather than `key: undefined` — `exactOptionalPropertyTypes: true`
    // rejects the latter when assigning into the strict openapi-typescript
    // queries shape.
    const queries: OrdersListQueries = {
        offset,
        limit,
        archived: false,
        active_pipeline: true,
        ...filters,
    };
    if (ordering !== undefined) queries.ordering = ordering;
    if (search !== undefined) queries.search = search;
    return useRetrieveOrders(queries);
}

export default function OrdersEditorPage() {
    const navigate = useNavigate();

    return (
        <ModelEditorPage
            title="Orders"
            modelName="Orders"
            useList={useOrdersList}
            columns={[
                col({
                    header: "Order #",
                    renderCell: (order) => (
                        <span className="font-mono text-sm text-primary">{order.order_number || "—"}</span>
                    ),
                    priority: 1,
                }),
                col({ header: "Name", renderCell: (order) => order.name, priority: 1 }),
                col({
                    header: "Status",
                    renderCell: (order) => order.order_status
                        ? <StatusBadge status={order.order_status} />
                        : "—",
                    priority: 1,
                }),
                col({ header: "Company", renderCell: (order) => order.company_name || "—", priority: 2 }),
                col({
                    header: "Customer",
                    renderCell: (order) =>
                        `${order.customer_first_name || ""} ${order.customer_last_name || ""}`.trim() || "—",
                    priority: 2,
                }),
                col({
                    header: "Est. Completion",
                    renderCell: (order) =>
                        order.estimated_completion
                            ? format(new Date(order.estimated_completion), "MMM d, yyyy")
                            : "—",
                    priority: 4,
                }),
            ]}
            renderActions={(order) => <EditOrderActionsCell orderId={order.id} />}
            onCreate={() => navigate({ to: "/OrderForm" })}
        />
    );
}
