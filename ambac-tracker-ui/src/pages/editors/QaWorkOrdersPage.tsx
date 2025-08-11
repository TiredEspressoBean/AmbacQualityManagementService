import { useRetrieveWorkOrders } from "@/hooks/useRetrieveWorkOrders";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage } from "@/pages/editors/ModelEditorPage.tsx";
import { Badge } from "@/components/ui/badge";

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
        queries: {
            offset,
            limit,
            ordering,
            search,
            // Note: Backend filtering by QA requirements would be done server-side
            // For now, we'll get all work orders and filter client-side if needed
        },
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
                    header: "QA Required", 
                    renderCell: (wo: any) => {
                        const requiresQa = wo.parts_summary?.requiring_qa || 0;
                        const total = wo.parts_summary?.total || 0;
                        
                        if (requiresQa === 0) {
                            return <span className="text-muted-foreground">Complete</span>;
                        }
                        
                        return (
                            <div>
                                <span className="font-medium">{requiresQa}</span>
                                <span className="text-muted-foreground text-sm ml-1">of {total}</span>
                            </div>
                        );
                    }
                },
                {
                    header: "Type",
                    renderCell: (wo: any) => {
                        const hasBatchParts = wo.parts_summary?.has_batch_parts;
                        return hasBatchParts ? 'Batch' : 'Individual';
                    }
                },
                { 
                    header: "Due Date", 
                    renderCell: (wo: any) => {
                        if (!wo.expected_completion) return <span className="text-muted-foreground">-</span>;
                        return new Date(wo.expected_completion).toLocaleDateString();
                    }
                },
                { 
                    header: "Customer", 
                    renderCell: (wo: any) => wo.related_order_detail?.company_name || 
                                            wo.related_order_detail?.name || 
                                            <span className="text-muted-foreground">-</span>
                },
            ]}
        />
    );
}