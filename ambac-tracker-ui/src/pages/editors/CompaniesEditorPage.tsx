import { useRetrieveCompanies } from "@/hooks/useRetrieveCompanies.ts";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage } from "@/pages/editors/ModelEditorPage.tsx";
import { EditCompanyActionsCell } from "@/components/edit-company-action-cell.tsx";

// Custom wrapper hook for consistent usage
function useCompaniesList({
                              offset,
                              limit,
                              ordering,
                              search,
                          }: {
    offset: number;
    limit: number;
    ordering?: string;
    search?: string;
}) {
    return useRetrieveCompanies({
        queries: {
            offset,
            limit,
            ordering,
            search,
        },
    });
}

export function CompaniesEditorPage() {
    const navigate = useNavigate();

    return (
        <ModelEditorPage
            title="Companies"
            modelName="Companies"
            useList={useCompaniesList}
            sortOptions={[
                { label: "Name (A-Z)", value: "name" },
                { label: "Name (Z-A)", value: "-name" },
                { label: "Created (Newest)", value: "-created_at" },
                { label: "Created (Oldest)", value: "created_at" },
                { label: "Updated (Newest)", value: "-updated_at" },
                { label: "Updated (Oldest)", value: "updated_at" },
                { label: "HubSpot API ID (A-Z)", value: "hubspot_api_id" },
                { label: "HubSpot API ID (Z-A)", value: "-hubspot_api_id" },
            ]}
            columns={[
                { header: "Name", renderCell: (company: any) => company.name },
                { header: "Description", renderCell: (company: any) => company.description },
                { header: "HubSpot API ID", renderCell: (company: any) => company.hubspot_api_id },
            ]}
            renderActions={(company) => <EditCompanyActionsCell companyId={company.id} />}
            onCreate={() => navigate({ to: "/CompaniesForm/create" })}
        />
    );
}