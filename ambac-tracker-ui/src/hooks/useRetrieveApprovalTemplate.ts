import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { Schema } from "@/lib/api/types";

type ApprovalTemplateResponse = Schema<"ApprovalTemplate">;

export const retrieveApprovalTemplateOptions = (params: { id: string }) => queryOptions<ApprovalTemplateResponse>({
    queryKey: ["approvalTemplate", params] as const,
    queryFn: () => api.api_ApprovalTemplates_retrieve({ params }) as Promise<ApprovalTemplateResponse>,
});

export function useRetrieveApprovalTemplate(
    options: { params: { id: string } },
    queryOptions?: { enabled?: boolean }
) {
    return useQuery({
        ...retrieveApprovalTemplateOptions(options.params),
        enabled: queryOptions?.enabled ?? true,
    });
}
