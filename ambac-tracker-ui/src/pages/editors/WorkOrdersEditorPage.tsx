import { useRetrieveWorkOrders } from "@/hooks/useRetrieveWorkOrders";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage } from "@/pages/editors/ModelEditorPage.tsx";
import { EditWorkOrderActionsCell } from "@/components/edit-work-order-action-cell.tsx";
import { WorkOrderUploadForm } from "@/components/work-order-csv-upload-form"; // adjust import if needed

// Custom wrapper hook for consistent usage
function useWorkOrdersList({
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
        },
    });
}

export function WorkOrdersEditorPage() {
    const navigate = useNavigate();

    return (
        <ModelEditorPage
            title="Work Orders"
            useList={useWorkOrdersList}
            sortOptions={[
                { label: "Created (Newest)", value: "-created_at" },
                { label: "Created (Oldest)", value: "created_at" },
                { label: "Order (Low to High)", value: "order" },
                { label: "Order (High to Low)", value: "-order" },
            ]}
            columns={[
                {
                    header: "ERP ID",
                    renderCell: (workOrder: any) => workOrder.ERP_id || "-",
                },
                {
                    header: "Status",
                    renderCell: (workOrder: any) =>
                        workOrder.workorder_status ?? "-",
                },
                {
                    header: "Related Order",
                    renderCell: (workOrder: any) =>
                        workOrder.related_order_detail?.name ?? "-",
                },
                {
                    header: "Active",
                    renderCell: (workOrder: any) =>
                        workOrder.active ? "Yes" : "No",
                },
                {
                    header: "Created At",
                    renderCell: (workOrder: any) =>
                        new Date(workOrder.created_at).toLocaleString(),
                },
                {
                    header: "Expected Completion",
                    renderCell: (workOrder: any) =>
                        new Date(workOrder.expected_completion).toLocaleString(),
                },
            ]}
            renderActions={(workOrder) => (
                <EditWorkOrderActionsCell workOrderId={workOrder.id} />
            )}
            onCreate={() => navigate({ to: "/WorkOrderForm/create" })}
            extraToolbarContent={<WorkOrderUploadForm />} // ✅ You can also pass props here
        />
    );
}
