import { useRetrieveSamplingRulesSets } from "@/hooks/useRetrieveSamplingRulesSets";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage } from "@/pages/editors/ModelEditorPage.tsx";
import { EditRuleTypeActionsCell } from "@/components/edit-sample-rule-types-action-cell.tsx";

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
    return useRetrieveSamplingRulesSets({
        queries: {
            offset,
            limit,
            ordering,
            search,
        },
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
            sortOptions={[
                { label: "Created (Newest)", value: "-created_at" },
                { label: "Created (Oldest)", value: "created_at" },
                { label: "Order (Low to High)", value: "order" },
                { label: "Order (High to Low)", value: "-order" },
            ]}
            columns={[
                { header: "Rule Set Name", renderCell: (ruleSet: any) => ruleSet.name || ruleSet.code || "-" },
                { header: "Part Type", renderCell: (ruleSet: any) => ruleSet.part_type_name ?? "-" },
                { header: "Process", renderCell: (ruleSet: any) => ruleSet.process_name ?? "-" },
                { header: "Active", renderCell: (ruleSet: any) => ruleSet.active ? "Yes" : "No" },
                { header: "Version", renderCell: (ruleSet: any) => ruleSet.version ?? "-" },
                { header: "Created At", renderCell: (ruleSet: any) => new Date(ruleSet.created_at).toLocaleString() },
            ]}
            renderActions={(ruleSet) => <EditRuleTypeActionsCell ruleSetId={ruleSet.id} />} // temporary until a dedicated component is created
            onCreate={() => navigate({ to: "/SamplingRuleSetForm/create" })}
        />
    );
}
