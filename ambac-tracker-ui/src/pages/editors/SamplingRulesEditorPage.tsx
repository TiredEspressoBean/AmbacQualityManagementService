import { useRetrieveSamplingRules } from "@/hooks/useRetrieveSamplingRules";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage } from "@/pages/editors/ModelEditorPage.tsx";
import { EditSamplingRuleActionsCell } from "@/components/edit-sample-rule-action-cell.tsx";

// Custom wrapper hook for consistent usage
function useSamplingRuleList({
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
    return useRetrieveSamplingRules({
        queries: {
            offset,
            limit,
            ordering,
            search,
        },
    });
}

export function SamplingRulesEditorPage() {
    const navigate = useNavigate();

    return (
        <ModelEditorPage
            title="Sampling Rules"
            useList={useSamplingRuleList}
            sortOptions={[
                { label: "Created (Newest)", value: "-created_at" },
                { label: "Created (Oldest)", value: "created_at" },
                { label: "Order (Low to High)", value: "order" },
                { label: "Order (High to Low)", value: "-order" },
            ]}
            columns={[
                { header: "Rule Type", renderCell: (rule: any) => rule.ruletype_name || rule.rule_type?.code || "-" },
                { header: "Ruleset", renderCell: (rule: any) => rule.ruleset_name || `#${rule.ruleset?.id}` },
                { header: "Order", renderCell: (rule: any) => rule.order ?? "-" },
                { header: "Value", renderCell: (rule: any) => rule.value ?? "-" },
                { header: "Created At", renderCell: (rule: any) => new Date(rule.created_at).toLocaleString() },
            ]}
            renderActions={(rule) => <EditSamplingRuleActionsCell ruleId={rule.id} />} // temporary until a dedicated component is created
            onCreate={() => navigate({ to: "/SamplingRuleForm/create" })}
        />
    );
}
