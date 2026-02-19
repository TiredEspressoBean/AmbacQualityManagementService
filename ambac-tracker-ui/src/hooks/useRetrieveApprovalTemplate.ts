import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export function useRetrieveApprovalTemplate(
    options: { params: { id: string } },
    queryOptions?: { enabled?: boolean }
) {
    return useQuery({
        queryKey: ["approvalTemplate", options.params],
        queryFn: () => api.api_ApprovalTemplates_retrieve({ params: options.params }),
        enabled: queryOptions?.enabled ?? true,
    });
}
