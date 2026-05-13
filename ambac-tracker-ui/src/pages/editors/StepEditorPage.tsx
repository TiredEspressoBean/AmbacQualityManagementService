import { useRetrieveSteps, stepsOptions, stepsMetadataOptions } from "@/hooks/useRetrieveSteps.ts";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage.tsx";
import { EditStepActionsCell } from "@/components/edit-step-action-cell.tsx";
import type { QueryClient } from "@tanstack/react-query";
import type { Schema } from "@/lib/api/types";

const col = createColumnHelper<Schema<"Steps">>();

// Default params that match what useStepsList passes on initial render
const DEFAULT_LIST_PARAMS = {
    offset: 0,
    limit: 25,
    search: "",
};

// Prefetch function for route loader
export const prefetchStepsEditor = (queryClient: QueryClient) => {
    queryClient.prefetchQuery(stepsOptions(DEFAULT_LIST_PARAMS));
    queryClient.prefetchQuery(stepsMetadataOptions());
};

// Matches Django filter fields exactly
function useStepsList({
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
    return useRetrieveSteps({
        offset,
        limit,
        ordering,
        search,
        ...filters,
    });
}

export function StepsEditorPage() {
    const navigate = useNavigate();

    return (
        <ModelEditorPage
            title="Steps"
            modelName="Steps"
            showDetailsLink={true}
            useList={useStepsList}
            columns={[
                col({ header: "Description", renderCell: (step) => step.description, priority: 5 }),
                col({ header: "Part Type", renderCell: (step) => step.part_type_name || step.part_type, priority: 2 }),
            ]}
            renderActions={(step) => <EditStepActionsCell stepId={step.id} />}
            onCreate={() => navigate({ to: "/StepForm/create" })}
        />
    );
}
