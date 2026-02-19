import { useRetrieveSamplingRulesSets } from "@/hooks/useRetrieveSamplingRulesSets";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage } from "@/pages/editors/ModelEditorPage.tsx";
import { EditRuleTypeActionsCell } from "@/components/edit-sample-rule-types-action-cell.tsx";
import { api } from "@/lib/api/generated";
import type { QueryClient } from "@tanstack/react-query";

// Default params that match what useSamplingRuleList passes on initial render
const DEFAULT_LIST_PARAMS = {
    offset: 0,
    limit: 25,
    search: "",
};

// Prefetch function for route loader
export const prefetchSamplingRuleSetsEditor = (queryClient: QueryClient) => {
    queryClient.prefetchQuery({
        queryKey: ["sampling-rules-sets", DEFAULT_LIST_PARAMS],
        queryFn: () => api["api_Sampling-rule-sets_list"](DEFAULT_LIST_PARAMS),
    });
    queryClient.prefetchQuery({
        queryKey: ["metadata", "SamplingRuleSets", "Sampling-rule-sets"],
        queryFn: () => api["api_Sampling-rule-sets_metadata_retrieve"](),
    });
};

// Custom wrapper hook for consistent usage
function useSamplingRuleList({
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
    return useRetrieveSamplingRulesSets({
        offset,
        limit,
        ordering,
        search,
        ...filters,
    });
}

export function SamplingRuleSetsEditorPage() {
    const navigate = useNavigate();

    return (
        <ModelEditorPage
            title="Sampling Rules"
            modelName="SamplingRuleSets"
            showDetailsLink={true}
            useList={useSamplingRuleList}
            columns={[
                { header: "Rule Set Name", renderCell: (ruleSet: any) => ruleSet.name || ruleSet.code || "-", priority: 1 },
                { header: "Part Type", renderCell: (ruleSet: any) => ruleSet.part_type_name ?? "-", priority: 2 },
                { header: "Process", renderCell: (ruleSet: any) => ruleSet.process_name ?? "-", priority: 3 },
                { header: "Active", renderCell: (ruleSet: any) => ruleSet.active ? "Yes" : "No", priority: 1 },
                { header: "Version", renderCell: (ruleSet: any) => ruleSet.version ?? "-", priority: 5 },
                { header: "Created At", renderCell: (ruleSet: any) => new Date(ruleSet.created_at).toLocaleString(), priority: 4 },
            ]}
            renderActions={(ruleSet) => <EditRuleTypeActionsCell ruleSetId={ruleSet.id} />} // temporary until a dedicated component is created
            onCreate={() => navigate({ to: "/SamplingRuleSetForm/create" })}
        />
    );
}
