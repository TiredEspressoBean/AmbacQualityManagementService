import { useRetrieveProcesses, processesOptions, processesMetadataOptions } from "@/hooks/useRetrieveProcesses";
import { useNavigate } from "@tanstack/react-router";
import {ModelEditorPage, createColumnHelper} from "@/pages/editors/ModelEditorPage.tsx";
import {EditProcessActionsCell} from "@/components/edit-process-action-cell.tsx";
import { Badge } from "@/components/ui/badge";
import type { QueryClient } from "@tanstack/react-query";
import type { Schema } from "@/lib/api/types";
import type { operations } from "@/lib/api/generated-types";

const col = createColumnHelper<Schema<"Processes">>();

type ProcessesListQueries = NonNullable<operations["api_Processes_list"]["parameters"]["query"]>;

// Default params that match what useProcessList passes on initial render
const DEFAULT_LIST_PARAMS = {
    offset: 0,
    limit: 25,
    search: "",
};

// Prefetch function for route loader
export const prefetchProcessEditor = (queryClient: QueryClient) => {
    queryClient.prefetchQuery(processesOptions(DEFAULT_LIST_PARAMS));
    queryClient.prefetchQuery(processesMetadataOptions());
};

function ProcessStatusBadge({ status }: { status: string }) {
    switch (status) {
        case 'APPROVED':
            return <Badge className="bg-green-600 hover:bg-green-700">Approved</Badge>;
        case 'DRAFT':
            return <Badge variant="secondary">Draft</Badge>;
        case 'DEPRECATED':
            return <Badge variant="outline" className="text-muted-foreground">Deprecated</Badge>;
        default:
            return <Badge variant="outline">{status}</Badge>;
    }
}

// Custom wrapper hook for consistent usage
function useProcessList({
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
    // Build the queries object incrementally so optional fields are simply
    // absent rather than `key: undefined` — `exactOptionalPropertyTypes: true`
    // rejects the latter when assigning into the strict openapi-typescript
    // queries shape.
    const queries: ProcessesListQueries = {
        offset,
        limit,
        ...filters,
    };
    if (ordering !== undefined) queries.ordering = ordering;
    if (search !== undefined) queries.search = search;
    return useRetrieveProcesses(queries);
}

export function ProcessEditorPage() {
    const navigate = useNavigate();
    return (
        <ModelEditorPage
            title="Process"
            modelName="Processes"
            showDetailsLink={true}
            useList={useProcessList}
            columns={[
                col({ header: "Name", renderCell: (p) => p.name, priority: 1 }),
                col({ header: "Status", renderCell: (p) => <ProcessStatusBadge status={p.status || 'DRAFT'} />, priority: 1 }),
                col({ header: "Updated At", renderCell: (p) => new Date(p.updated_at).toLocaleString(), priority: 4 }),
                col({ header: "Number of Steps", renderCell: (p) => p.num_steps, priority: 2 }),
                col({ header: "Reman Process", renderCell: (p) => p.is_remanufactured ? "Yes" : "No", priority: 3 }),
            ]}
            renderActions={(process) => <EditProcessActionsCell processId={process.id} />}
            onCreate={() => navigate({ to: "/ProcessForm/create" })}
        />
    );
}
