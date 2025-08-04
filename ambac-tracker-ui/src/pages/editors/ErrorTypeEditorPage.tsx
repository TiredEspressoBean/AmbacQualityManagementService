import { useRetrieveErrorTypes } from "@/hooks/useRetrieveErrorTypes.ts";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage } from "@/pages/editors/ModelEditorPage.tsx";
import { EditErrorTypeActionsCell } from "@/components/edit-error-type-action-cell.tsx";

// Matches Django filter fields exactly
function useErrorTypesList({
                                   offset,
                                   limit,
                                   ordering,
                                   search,
                               }: {
    offset: number;
    limit: number;
    ordering?: string;
    search?: string;
    part_type?: string;
    process?: string;
}) {
    return useRetrieveErrorTypes({
        queries: {
            offset,
            limit,
            ordering,
            search,
        },
    });
}

export function ErrorTypeEditorPage() {
    const navigate = useNavigate();

    return (
        <ModelEditorPage
            title="Error Types"
            modelName="ErrorTypes"
            useList={useErrorTypesList}
            sortOptions={[
                { label: "Name (A-Z)", value: "name" },
                { label: "Name (Z-A)", value: "-name" },
                { label: "Part Type (A-Z)", value: "part_type" },
                { label: "Part type (Z-A)", value: "-part_type" },
            ]}
            columns={[
                { header: "Name", renderCell: (error: any) => error.error_name },
                { header: "Part Type", renderCell: (error: any) => error.part_type_name },
            ]}
            renderActions={(errorType) => <EditErrorTypeActionsCell errorTypeId={errorType.id} />}
            onCreate={() => navigate({ to: "/ErrorTypeForm/create" })}
        />
    );
}
