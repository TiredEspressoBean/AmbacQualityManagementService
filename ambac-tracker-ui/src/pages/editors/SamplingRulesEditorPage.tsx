import { useRetrieveSamplingRules } from "@/hooks/useRetrieveSamplingRules";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage } from "@/pages/editors/ModelEditorPage.tsx";
import { EditSamplingRuleActionsCell } from "@/components/edit-sample-rule-action-cell.tsx";
import { api } from "@/lib/api/generated";
import type { QueryClient } from "@tanstack/react-query";

// Default params that match what useSamplingRuleList passes on initial render
const DEFAULT_LIST_PARAMS = {
    offset: 0,
    limit: 25,
    search: "",
};

// Prefetch function for route loader
export const prefetchSamplingRulesEditor = (queryClient: QueryClient) => {
    queryClient.prefetchQuery({
        queryKey: ["sampling-rules", DEFAULT_LIST_PARAMS],
        queryFn: () => api["api_Sampling-rules_list"](DEFAULT_LIST_PARAMS),
    });
    queryClient.prefetchQuery({
        queryKey: ["metadata", "SamplingRules", "Sampling-rules"],
        queryFn: () => api["api_Sampling-rules_metadata_retrieve"](),
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
    return useRetrieveSamplingRules({
        offset,
        limit,
        ordering,
        search,
        ...filters,
    });
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
                { header: "Rule Type", renderCell: (rule: any) => rule.ruletype_name || rule.rule_type?.code || "-", priority: 2 },
                { header: "Ruleset", renderCell: (rule: any) => rule.ruleset_name || `#${rule.ruleset?.id}`, priority: 3 },
                { header: "Order", renderCell: (rule: any) => rule.order ?? "-", priority: 2 },
                { header: "Value", renderCell: (rule: any) => rule.value ?? "-", priority: 2 },
                { header: "Created At", renderCell: (rule: any) => new Date(rule.created_at).toLocaleString(), priority: 4 },
            ]}
            renderActions={(rule) => <EditSamplingRuleActionsCell ruleId={rule.id} />} // temporary until a dedicated component is created
            onCreate={() => navigate({ to: "/SamplingRuleForm/create" })}
        />
    );
}
