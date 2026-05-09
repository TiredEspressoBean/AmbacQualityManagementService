import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { Schema } from "@/lib/api/types";

type ApprovalTemplateResponse = Schema<"ApprovalTemplate">;

export function useRetrieveApprovalTemplate(
    options: { params: { id: string } },
    queryOptions?: { enabled?: boolean }
) {
    return useQuery<ApprovalTemplateResponse>({
        queryKey: ["approvalTemplate", options.params],
        queryFn: () => api.api_ApprovalTemplates_retrieve({ params: options.params }) as Promise<ApprovalTemplateResponse>,
        enabled: queryOptions?.enabled ?? true,
    });
}
