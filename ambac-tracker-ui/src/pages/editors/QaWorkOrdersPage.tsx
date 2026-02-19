import { useRetrieveWorkOrders } from "@/hooks/useRetrieveWorkOrders";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage } from "@/pages/editors/ModelEditorPage.tsx";
import { StatusBadge } from "@/components/ui/status-badge";

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

export function QaWorkOrdersPage() {
    const navigate = useNavigate();

    const handleWorkOrderClick = (workOrder: any) => {
        // Navigate to the QA work order detail page
        navigate({ to: `/qa/workorder/${workOrder.id}` });
    };

    return (
        <ModelEditorPage
            title="Quality Assurance - Work Orders"
            useList={useQaWorkOrdersList}
            generateDetailLink={(workOrder: any) => `/qa/workorder/${workOrder.id}`}
            showDetailsLink={true}
            sortOptions={[
                { label: "Due Date (Earliest)", value: "expected_completion" },
                { label: "Work Order (A-Z)", value: "ERP_id" },
                { label: "Created (Newest)", value: "-created_at" },
            ]}
            columns={[
                {
                    header: "Work Order",
                    renderCell: (wo: any) => (
                        <button
                            onClick={() => handleWorkOrderClick(wo)}
                            className="font-medium hover:underline text-left"
                        >
                            {wo.ERP_id}
                        </button>
                    )
                },
                {
                    header: "Process",
                    renderCell: (wo: any) => wo.process_info?.name || <span className="text-muted-foreground">—</span>
                },
                {
                    header: "QA Progress",
                    renderCell: (wo: any) => {
                        const completed = wo.qa_progress?.completed || 0;
                        const required = wo.qa_progress?.required || 0;

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
                },
                {
                    header: "Due Date",
                    renderCell: (wo: any) => {
                        if (!wo.expected_completion) return <span className="text-muted-foreground">—</span>;
                        return new Date(wo.expected_completion).toLocaleDateString();
                    }
                },
                {
                    header: "Customer",
                    renderCell: (wo: any) => {
                        const orderInfo = wo.related_order_info;
                        if (!orderInfo) return <span className="text-muted-foreground">—</span>;

                        // Prefer company name, fall back to customer name
                        if (orderInfo.company?.name) return orderInfo.company.name;
                        if (orderInfo.customer) {
                            const { first_name, last_name } = orderInfo.customer;
                            if (first_name || last_name) return `${first_name || ''} ${last_name || ''}`.trim();
                        }
                        return orderInfo.name || <span className="text-muted-foreground">—</span>;
                    }
                },
                {
                    header: "Order",
                    renderCell: (wo: any) => wo.related_order_info?.name || <span className="text-muted-foreground">—</span>
                },
            ]}
        />
    );
}