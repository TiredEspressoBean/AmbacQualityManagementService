import { useRetrieveCompanies } from "@/hooks/useRetrieveCompanies.ts";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage } from "@/pages/editors/ModelEditorPage.tsx";
import { EditCompanyActionsCell } from "@/components/edit-company-action-cell.tsx";
import { api } from "@/lib/api/generated";
import type { QueryClient } from "@tanstack/react-query";

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
        queryFn: () => api.api_Companies_list(DEFAULT_LIST_PARAMS),
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
                { header: "Name", renderCell: (company: any) => company.name, priority: 1 },
                { header: "Description", renderCell: (company: any) => company.description, priority: 5 },
                { header: "HubSpot API ID", renderCell: (company: any) => company.hubspot_api_id, priority: 4 },
            ]}
            renderActions={(company) => <EditCompanyActionsCell companyId={company.id} />}
            onCreate={() => navigate({ to: "/CompaniesForm/create" })}
        />
    );
}