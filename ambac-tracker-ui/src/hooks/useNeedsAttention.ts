import { api } from "@/lib/api/generated";
import { useQuery, queryOptions } from "@tanstack/react-query";
import type { Severity } from "@/components/analytics";

export type AttentionItemData = {
    type: string;
    message: string;
    count: number;
    severity: Severity;
    link: string;
    linkParams?: Record<string, string>;
};

export type NeedsAttentionResponse = {
    data: AttentionItemData[];
};

type UseNeedsAttentionParams = {
    enabled?: boolean;
};

export const needsAttentionOptions = () => queryOptions({
    queryKey: ["needs-attention"] as const,
    queryFn: () => api.api_dashboard_needs_attention_retrieve() as Promise<NeedsAttentionResponse>,
});

export const useNeedsAttention = ({ enabled = true }: UseNeedsAttentionParams = {}) => {
    return useQuery({
        ...needsAttentionOptions(),
        enabled,
        refetchInterval: 2 * 60 * 1000, // Poll every 2 minutes - actionable alerts
    });
};
