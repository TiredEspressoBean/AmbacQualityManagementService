import { useRetrieveWorkOrders } from "@/hooks/useRetrieveWorkOrders";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage.tsx";
import { StatusBadge } from "@/components/ui/status-badge";
import type { Schema } from "@/lib/api/types";

// Custom wrapper hook for consistent usage
function useQaWorkOrdersList({
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
    return useRetrieveWorkOrders({
        offset,
        limit,
        ordering,
        search,
        // Note: Backend filtering by QA requirements would be done server-side
        // For now, we'll get all work orders and filter client-side if needed
    });
}

type WO = Schema<"WorkOrderList">;

// Sub-field shapes not captured by the openapi-typescript spec (both typed as {})
type ProcessInfo = { name?: string };
type QaProgress = { completed?: number; required?: number };
type OrderInfo = { name?: string; company?: { name?: string }; customer?: { first_name?: string; last_name?: string } };

const col = createColumnHelper<WO>();

export function QaWorkOrdersPage() {
    const navigate = useNavigate();

    const handleWorkOrderClick = (workOrder: WO) => {
        navigate({ to: `/workorder/${workOrder.id}` });
    };

    return (
        <ModelEditorPage
            title="Work Orders"
            useList={useQaWorkOrdersList}
            generateDetailLink={(workOrder: WO) => `/workorder/${workOrder.id}`}
            showDetailsLink={true}
            sortOptions={[
                { label: "Due Date (Earliest)", value: "expected_completion" },
                { label: "Work Order (A-Z)", value: "ERP_id" },
                { label: "Created (Newest)", value: "-created_at" },
            ]}
            columns={[
                col({
                    header: "Work Order",
                    renderCell: (wo) => (
                        <button
                            onClick={() => handleWorkOrderClick(wo)}
                            className="font-medium hover:underline text-left"
                        >
                            {wo.ERP_id}
                        </button>
                    )
                }),
                col({
                    header: "Process",
                    // eslint-disable-next-line local/no-double-cast-via-unknown -- process_info is {} in openapi spec; actual shape has .name
                    renderCell: (wo) => (wo.process_info as unknown as ProcessInfo)?.name || <span className="text-muted-foreground">—</span>
                }),
                col({
                    header: "QA Progress",
                    renderCell: (wo) => {
                        // eslint-disable-next-line local/no-double-cast-via-unknown -- qa_progress is {} in openapi spec; actual shape has .completed/.required
                        const progress = wo.qa_progress as unknown as QaProgress;
                        const completed = progress?.completed ?? 0;
                        const required = progress?.required ?? 0;

                        if (required === 0) {
                            return <span className="text-muted-foreground">No QA Required</span>;
                        }

                        if (completed >= required) {
                            return <StatusBadge status="COMPLETED" label="Complete" />;
                        }

                        return (
                            <div>
                                <span className="font-medium">{completed}</span>
                                <span className="text-muted-foreground">/{required}</span>
                            </div>
                        );
                    }
                }),
                col({
                    header: "Due Date",
                    renderCell: (wo) => {
                        if (!wo.expected_completion) return <span className="text-muted-foreground">—</span>;
                        return new Date(wo.expected_completion).toLocaleDateString();
                    }
                }),
                col({
                    header: "Customer",
                    renderCell: (wo) => {
                        // eslint-disable-next-line local/no-double-cast-via-unknown -- related_order_info is {} in openapi spec; actual shape has .company/.customer
                        const orderInfo = wo.related_order_info as unknown as OrderInfo | undefined;
                        if (!orderInfo) return <span className="text-muted-foreground">—</span>;

                        // Prefer company name, fall back to customer name
                        if (orderInfo.company?.name) return orderInfo.company.name;
                        if (orderInfo.customer) {
                            const { first_name, last_name } = orderInfo.customer;
                            if (first_name || last_name) return `${first_name || ''} ${last_name || ''}`.trim();
                        }
                        return orderInfo.name || <span className="text-muted-foreground">—</span>;
                    }
                }),
                col({
                    header: "Order",
                    // eslint-disable-next-line local/no-double-cast-via-unknown -- related_order_info is {} in openapi spec; actual shape has .name
                    renderCell: (wo) => (wo.related_order_info as unknown as OrderInfo)?.name || <span className="text-muted-foreground">—</span>
                }),
            ]}
        />
    );
}