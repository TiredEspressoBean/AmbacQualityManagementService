import { ReportButton } from "@/components/reports/ReportButton";

/**
 * A job's paperwork — the traveler that goes with it, the requisition that draws its
 * material, and the labels for its units. One component so every page that shows a
 * work order offers the same set; the detail and control pages used to offer
 * different halves of it.
 */
export function WorkOrderDocuments({ workOrderId }: { workOrderId: string | undefined }) {
    return (
        <>
            <ReportButton
                reportType="work_order_traveler"
                label="Traveler"
                params={workOrderId ? { id: workOrderId } : null}
            />
            <ReportButton
                reportType="pick_list"
                label="Material Requisition"
                params={workOrderId ? { id: workOrderId } : null}
            />
            <ReportButton
                reportType="part_id_label_batch"
                label="Part Labels"
                params={workOrderId ? { work_order_id: workOrderId } : null}
            />
        </>
    );
}
