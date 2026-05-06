import { useRetrieveThreeDModels } from "@/hooks/useRetrieveThreeDModels.ts";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage.tsx";
import { EditThreeDModelActionsCell } from "@/components/edit-three-d-model-action-cell.tsx";
import { api } from "@/lib/api/generated";
import type { QueryClient } from "@tanstack/react-query";
import type { Schema } from "@/lib/api/types";

const col = createColumnHelper<Schema<"ThreeDModel">>();

// Default params that match what useThreeDModelsList passes on initial render
const DEFAULT_LIST_PARAMS = {
    offset: 0,
    limit: 25,
    search: "",
};

// Prefetch function for route loader
export const prefetchThreeDModelsEditor = (queryClient: QueryClient) => {
    queryClient.prefetchQuery({
        queryKey: ["threeDModel", DEFAULT_LIST_PARAMS],
        queryFn: () => api.api_ThreeDModels_list({ queries: DEFAULT_LIST_PARAMS }),
    });
    queryClient.prefetchQuery({
        queryKey: ["metadata", "ThreeDModels", "ThreeDModels"],
        queryFn: () => api.api_ThreeDModels_metadata_retrieve(),
    });
};

// Custom wrapper hook for consistent usage
function useThreeDModelsList({
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
    return useRetrieveThreeDModels({
        offset,
        limit,
        ordering,
        search,
        ...filters,
    });
}

export function ThreeDModelsEditorPage() {
    const navigate = useNavigate();

    return (
        <ModelEditorPage
            title="3D Models"
            modelName="ThreeDModels"
            useList={useThreeDModelsList}
            columns={[
                col({ header: "Name", renderCell: (model) => model.name, priority: 1 }),
                col({ header: "Part Type", renderCell: (model) => model.part_type_display || "N/A", priority: 2 }),
                col({ header: "Step", renderCell: (model) => model.step_display || "N/A", priority: 3 }),
                col({ header: "File Type", renderCell: (model) => model.file_type || "N/A", priority: 2 }),
            ]}
            renderActions={(model) => <EditThreeDModelActionsCell modelId={model.id} />}
            onCreate={() => navigate({ to: "/ThreeDModelsForm/create" })}
        />
    );
}
