import { useRetrieveSteps } from "@/hooks/useRetrieveSteps.ts";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage } from "@/pages/editors/ModelEditorPage.tsx";
import { EditStepActionsCell } from "@/components/edit-step-action-cell.tsx";
import { api } from "@/lib/api/generated";
import type { QueryClient } from "@tanstack/react-query";

// Default params that match what useStepsList passes on initial render
const DEFAULT_LIST_PARAMS = {
    offset: 0,
    limit: 25,
    search: "",
};

// Prefetch function for route loader
export const prefetchStepsEditor = (queryClient: QueryClient) => {
    queryClient.prefetchQuery({
        queryKey: ["steps", DEFAULT_LIST_PARAMS],
        queryFn: () => api.api_Steps_list(DEFAULT_LIST_PARAMS),
    });
    queryClient.prefetchQuery({
        queryKey: ["metadata", "Steps", "Steps"],
        queryFn: () => api.api_Steps_metadata_retrieve(),
    });
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
                { header: "Description", renderCell: (step: any) => step.description, priority: 5 },
                { header: "Part Type", renderCell: (step: any) => step.part_type_name || step.part_type, priority: 2 },
            ]}
            renderActions={(step) => <EditStepActionsCell stepId={step.id} />}
            onCreate={() => navigate({ to: "/StepForm/create" })}
        />
    );
}
