import { useRetrieveSteps, stepsOptions, stepsMetadataOptions } from "@/hooks/useRetrieveSteps.ts";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage.tsx";
import { StepInProcessActions } from "@/components/process/StepInProcessActions";
import type { QueryClient } from "@tanstack/react-query";
import type { Schema } from "@/lib/api/types";

const col = createColumnHelper<Schema<"Steps">>();

// Default params that match what useStepsList passes on initial render
const DEFAULT_LIST_PARAMS = {
    offset: 0,
    limit: 25,
    search: "",
    // The endpoint spans versions; a superseded step lives on only in the process
    // versions that still point at it, and is reached through them.
    is_current_version: true,
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
        is_current_version: true,
        ...filters,
    });
}

export function StepsEditorPage() {
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
            renderActions={(step) => <StepInProcessActions stepId={step.id} processes={step.processes ?? []} />}
            headerContent={
                <p className="text-sm text-muted-foreground">
                    Steps are added, edited and removed in their process. A process, its later
                    versions and its copies share step rows, so editing in the process keeps
                    every other version as it was.
                </p>
            }
        />
    );
}
