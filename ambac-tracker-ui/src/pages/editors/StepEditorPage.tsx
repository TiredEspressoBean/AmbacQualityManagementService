import { useRetrieveSteps } from "@/hooks/useRetrieveSteps.ts";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage } from "@/pages/editors/ModelEditorPage.tsx";
import { EditStepActionsCell } from "@/components/edit-step-action-cell.tsx";

// Matches Django filter fields exactly
function useStepsList({
                          offset,
                          limit,
                          ordering,
                          search,
                          part_type,
                          process,
                      }: {
    offset: number;
    limit: number;
    ordering?: string;
    search?: string;
    part_type?: string;
    process?: string;
}) {
    return useRetrieveSteps({
        queries: {
            offset,
            limit,
            ordering,
            search,
            part_type: part_type ? Number(part_type) : undefined,
            process: process ? Number(process) : undefined,
        },
    });
}

export function StepsEditorPage() {
    const navigate = useNavigate();

    return (
        <ModelEditorPage
            title="Steps"
            useList={useStepsList}
            sortOptions={[
                { label: "Process Name (A-Z)", value: "process__name" },
                { label: "Process Name (Z-A)", value: "-process__name" },
                { label: "Part Type Name (A-Z)", value: "part_type__name" },
                { label: "Part Type Name (Z-A)", value: "-part_type__name" },
            ]}
            columns={[
                { header: "Ordering #", renderCell: (step: any) => step.order },
                { header: "Description", renderCell: (step: any) => step.description },
                { header: "Is Last Step?", renderCell: (step: any) => step.is_last_step ? "Yes" : "No" },
                { header: "Process", renderCell: (step: any) => step.process_name || step.process },
                { header: "Part Type", renderCell: (step: any) => step.part_type_name || step.part_type },
            ]}
            renderActions={(step) => <EditStepActionsCell stepId={step.id} />}
            onCreate={() => navigate({ to: "/StepForm/create" })}
        />
    );
}
