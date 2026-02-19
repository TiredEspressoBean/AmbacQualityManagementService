import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

// Model names that have metadata endpoints
const MODELS_WITH_METADATA = [
    "WorkOrders",
    "Orders",
    "Parts",
    "PartTypes",
    "Processes",
    "Steps",
    "Documents",
    "DocumentTypes",
    "Equipment",
    "Equipment_types",
    "Error_types",
    "Companies",
    "Customers",
    "Sampling_rules",
    "Sampling_rule_sets",
    "ThreeDModels",
    "User",
    "CAPAs",
    "ApprovalTemplates",
    "ApprovalRequests",
] as const;

type ModelName = (typeof MODELS_WITH_METADATA)[number];

// Map model names to their metadata API functions
const metadataFetchers: Record<ModelName, () => Promise<any>> = {
    WorkOrders: api.api_WorkOrders_metadata_retrieve,
    Orders: api.api_Orders_metadata_retrieve,
    Parts: api.api_Parts_metadata_retrieve,
    PartTypes: api.api_PartTypes_metadata_retrieve,
    Processes: api.api_Processes_metadata_retrieve,
    Steps: api.api_Steps_metadata_retrieve,
    Documents: api.api_Documents_metadata_retrieve,
    DocumentTypes: api.api_DocumentTypes_metadata_retrieve,
    Equipment: api.api_Equipment_metadata_retrieve,
    Equipment_types: api.api_Equipment_types_metadata_retrieve,
    Error_types: api.api_Error_types_metadata_retrieve,
    Companies: api.api_Companies_metadata_retrieve,
    Customers: api.api_Customers_metadata_retrieve,
    Sampling_rules: api.api_Sampling_rules_metadata_retrieve,
    Sampling_rule_sets: api.api_Sampling_rule_sets_metadata_retrieve,
    ThreeDModels: api.api_ThreeDModels_metadata_retrieve,
    User: api.api_User_metadata_retrieve,
    CAPAs: api.api_CAPAs_metadata_retrieve,
    ApprovalTemplates: api.api_ApprovalTemplates_metadata_retrieve,
    ApprovalRequests: api.api_ApprovalRequests_metadata_retrieve,
};

export function useSchemaMetadata(modelName: ModelName) {
    return useQuery({
        queryKey: ["schema-metadata", modelName],
        queryFn: () => metadataFetchers[modelName](),
        staleTime: Infinity, // Metadata doesn't change during a session
        enabled: !!modelName && modelName in metadataFetchers,
    });
}

export function useAllSchemaMetadata() {
    return useQuery({
        queryKey: ["schema-metadata", "all"],
        queryFn: async () => {
            const results: Record<string, any> = {};
            for (const model of MODELS_WITH_METADATA) {
                try {
                    results[model] = await metadataFetchers[model]();
                } catch (e) {
                    results[model] = { error: e instanceof Error ? e.message : "Unknown error" };
                }
            }
            return results;
        },
        staleTime: Infinity,
    });
}

export { MODELS_WITH_METADATA };
export type { ModelName };
