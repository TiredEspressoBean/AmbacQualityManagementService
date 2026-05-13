import { useRetrieveSamplingRules, samplingRulesOptions, samplingRulesMetadataOptions } from "@/hooks/useRetrieveSamplingRules";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage.tsx";
import { EditSamplingRuleActionsCell } from "@/components/edit-sample-rule-action-cell.tsx";
import type { QueryClient } from "@tanstack/react-query";
import type { Schema } from "@/lib/api/types";

const col = createColumnHelper<Schema<"SamplingRule">>();

// Default params that match what useSamplingRuleList passes on initial render
const DEFAULT_LIST_PARAMS = {
    offset: 0,
    limit: 25,
    search: "",
};

// Prefetch function for route loader
export const prefetchSamplingRulesEditor = (queryClient: QueryClient) => {
    queryClient.prefetchQuery(samplingRulesOptions(DEFAULT_LIST_PARAMS));
    queryClient.prefetchQuery(samplingRulesMetadataOptions());
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
    const queries: Parameters<typeof useRetrieveSamplingRules>[0] = {
        offset,
        limit,
        ...filters,
    };
    if (ordering !== undefined) queries.ordering = ordering;
    if (search !== undefined) queries.search = search;
    return useRetrieveSamplingRules(queries);
}

export function SamplingRulesEditorPage() {
    const navigate = useNavigate();

    return (
        <ModelEditorPage
            title="Sampling Rules"
            modelName="SamplingRules"
            showDetailsLink={true}
            useList={useSamplingRuleList}
            columns={[
                col({ header: "Rule Type", renderCell: (rule) => rule.ruletype_name || rule.rule_type || "-", priority: 2 }),
                col({ header: "Ruleset", renderCell: (rule) => rule.ruleset_name || (rule.ruleset ? `#${rule.ruleset}` : "-"), priority: 3 }),
                col({ header: "Order", renderCell: (rule) => rule.order ?? "-", priority: 2 }),
                col({ header: "Value", renderCell: (rule) => rule.value ?? "-", priority: 2 }),
                col({ header: "Created At", renderCell: (rule) => new Date(rule.created_at).toLocaleString(), priority: 4 }),
            ]}
            renderActions={(rule) => <EditSamplingRuleActionsCell ruleId={rule.id} />} // temporary until a dedicated component is created
            onCreate={() => navigate({ to: "/SamplingRuleForm/create" })}
        />
    );
}
