import { useRetrieveCompanies } from "@/hooks/useRetrieveCompanies.ts";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage.tsx";
import { EditCompanyActionsCell } from "@/components/edit-company-action-cell.tsx";
import { api } from "@/lib/api/generated";
import type { QueryClient } from "@tanstack/react-query";
import type { Schema } from "@/lib/api/types";

const col = createColumnHelper<Schema<"Company">>();

// Default params that match what useCompaniesList passes on initial render
const DEFAULT_LIST_PARAMS = {
    offset: 0,
    limit: 25,
    search: "",
};

// Prefetch function for route loader
export const prefetchCompaniesEditor = (queryClient: QueryClient) => {
    queryClient.prefetchQuery({
        queryKey: ["company", DEFAULT_LIST_PARAMS],
        queryFn: () => api.api_Companies_list({ queries: DEFAULT_LIST_PARAMS }),
    });
    queryClient.prefetchQuery({
        queryKey: ["metadata", "Companies", "Companies"],
        queryFn: () => api.api_Companies_metadata_retrieve(),
    });
};

// Custom wrapper hook for consistent usage
function useCompaniesList({
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
    return useRetrieveCompanies({
        offset,
        limit,
        ordering,
        search,
        ...filters,
    });
}

export function CompaniesEditorPage() {
    const navigate = useNavigate();

    return (
        <ModelEditorPage
            title="Companies"
            modelName="Companies"
            useList={useCompaniesList}
            columns={[
                col({ header: "Name", renderCell: (company) => company.name, priority: 1 }),
                col({ header: "Description", renderCell: (company) => company.description, priority: 5 }),
            ]}
            renderActions={(company) => <EditCompanyActionsCell companyId={company.id} />}
            onCreate={() => navigate({ to: "/CompaniesForm/create" })}
        />
    );
}