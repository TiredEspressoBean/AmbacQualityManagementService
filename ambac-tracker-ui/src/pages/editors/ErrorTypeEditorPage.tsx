import { useRetrieveErrorTypes } from "@/hooks/useRetrieveErrorTypes.ts";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage.tsx";
import { EditErrorTypeActionsCell } from "@/components/edit-error-type-action-cell.tsx";
import { Badge } from "@/components/ui/badge";
import { Box } from "lucide-react";
import { api } from "@/lib/api/generated";
import type { QueryClient } from "@tanstack/react-query";
import type { Schema } from "@/lib/api/types";

const col = createColumnHelper<Schema<"QualityErrorsList">>();

// Default params that match what useErrorTypesList passes on initial render
const DEFAULT_LIST_PARAMS = {
    offset: 0,
    limit: 25,
    search: "",
};

// Prefetch function for route loader
export const prefetchErrorTypesEditor = (queryClient: QueryClient) => {
    queryClient.prefetchQuery({
        queryKey: ["error-types", DEFAULT_LIST_PARAMS],
        queryFn: () => api.api_Error_types_list({ queries: DEFAULT_LIST_PARAMS }),
    });
    queryClient.prefetchQuery({
        queryKey: ["metadata", "ErrorTypes", "Error-types"],
        queryFn: () => api.api_Error_types_metadata_retrieve(),
    });
};

// Matches Django filter fields exactly
function useErrorTypesList({
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
    return useRetrieveErrorTypes({
        offset,
        limit,
        ordering,
        search,
        ...filters,
    });
}

export function ErrorTypeEditorPage() {
    const navigate = useNavigate();

    return (
        <ModelEditorPage
            title="Error Types"
            modelName="ErrorTypes"
            useList={useErrorTypesList}
            columns={[
                col({ header: "Name", renderCell: (error) => error.error_name, priority: 1 }),
                col({ header: "Part Type", renderCell: (error) => error.part_type_name || "All", priority: 2 }),
                col({
                    header: "3D Annotation",
                    renderCell: (error) =>
                        error.requires_3d_annotation ? (
                            <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                                <Box className="h-3 w-3 mr-1" />
                                Required
                            </Badge>
                        ) : (
                            <span className="text-muted-foreground">—</span>
                        ),
                    priority: 2
                }),
            ]}
            renderActions={(errorType) => <EditErrorTypeActionsCell errorTypeId={errorType.id} />}
            onCreate={() => navigate({ to: "/ErrorTypeForm/create" })}
        />
    );
}
