import {useRetrieveProcesses} from "@/hooks/useRetrieveProcesses";
import { useNavigate } from "@tanstack/react-router";
import {ModelEditorPage} from "@/pages/editors/ModelEditorPage.tsx";
import {EditProcessActionsCell} from "@/components/edit-process-action-cell.tsx";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api/generated";
import type { QueryClient } from "@tanstack/react-query";

// Default params that match what useProcessList passes on initial render
const DEFAULT_LIST_PARAMS = {
    offset: 0,
    limit: 25,
    search: "",
};

// Prefetch function for route loader
export const prefetchProcessEditor = (queryClient: QueryClient) => {
    queryClient.prefetchQuery({
        queryKey: ["process", DEFAULT_LIST_PARAMS],
        queryFn: () => api.api_Processes_list(DEFAULT_LIST_PARAMS),
    });
    queryClient.prefetchQuery({
        queryKey: ["metadata", "Processes", "Processes"],
        queryFn: () => api.api_Processes_metadata_retrieve(),
    });
};

function ProcessStatusBadge({ status }: { status: string }) {
    switch (status) {
        case 'approved':
            return <Badge className="bg-green-600 hover:bg-green-700">Approved</Badge>;
        case 'draft':
            return <Badge variant="secondary">Draft</Badge>;
        case 'deprecated':
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

    return useRetrieveProcesses({
        offset,
        limit,
        ordering,
        search,
        ...filters,
    })
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
                { header: "Name", renderCell: (p: any) => p.name, priority: 1 },
                { header: "Status", renderCell: (p: any) => <ProcessStatusBadge status={p.status || 'draft'} />, priority: 1 },
                { header: "Updated At", renderCell: (p: any) => new Date(p.updated_at).toLocaleString(), priority: 4 },
                { header: "Number of Steps", renderCell: (p: any) => p.num_steps, priority: 2 },
                { header: "Reman Process", renderCell: (p: any) => p.is_remanufactured ? "Yes" : "No", priority: 3 },
            ]}
            renderActions={(process) => <EditProcessActionsCell processId={process.id} />}
            onCreate={() => navigate({ to: "/ProcessForm/create" })}
        />
    );
}
