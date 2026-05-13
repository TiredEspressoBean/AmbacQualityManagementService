import { useRetrieveSamplingRulesSets, samplingRuleSetsOptions, samplingRuleSetsMetadataOptions } from "@/hooks/useRetrieveSamplingRulesSets";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage.tsx";
import { EditRuleTypeActionsCell } from "@/components/edit-sample-rule-types-action-cell.tsx";
import type { QueryClient } from "@tanstack/react-query";
import type { Schema } from "@/lib/api/types";

const col = createColumnHelper<Schema<"SamplingRuleSet">>();

// Default params that match what useSamplingRuleList passes on initial render
const DEFAULT_LIST_PARAMS = {
    offset: 0,
    limit: 25,
    search: "",
};

// Prefetch function for route loader
export const prefetchSamplingRuleSetsEditor = (queryClient: QueryClient) => {
    queryClient.prefetchQuery(samplingRuleSetsOptions(DEFAULT_LIST_PARAMS));
    queryClient.prefetchQuery(samplingRuleSetsMetadataOptions());
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
    const queries: Parameters<typeof useRetrieveSamplingRulesSets>[0] = {
        offset,
        limit,
        ...filters,
    };
    if (ordering !== undefined) queries.ordering = ordering;
    if (search !== undefined) queries.search = search;
    return useRetrieveSamplingRulesSets(queries);
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
                col({ header: "Rule Set Name", renderCell: (ruleSet) => ruleSet.name || "-", priority: 1 }),
                col({ header: "Part Type", renderCell: (ruleSet) => ruleSet.part_type_name ?? "-", priority: 2 }),
                col({ header: "Process", renderCell: (ruleSet) => ruleSet.process_name ?? "-", priority: 3 }),
                col({ header: "Active", renderCell: (ruleSet) => ruleSet.active ? "Yes" : "No", priority: 1 }),
                col({ header: "Version", renderCell: (ruleSet) => ruleSet.version ?? "-", priority: 5 }),
                col({ header: "Created At", renderCell: (ruleSet) => new Date(ruleSet.created_at).toLocaleString(), priority: 4 }),
            ]}
            renderActions={(ruleSet) => <EditRuleTypeActionsCell ruleSetId={ruleSet.id} />} // temporary until a dedicated component is created
            onCreate={() => navigate({ to: "/SamplingRuleSetForm/create" })}
        />
    );
}
