import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { Schema } from "@/lib/api/types";

type CompanyResponse = Schema<"Company">;

export function useRetrieveCompany(
    query: Parameters<typeof api.api_Companies_retrieve>[0],
    options?: { enabled?: boolean }
) {
    return useQuery<CompanyResponse>({
        queryKey: ["company", query],
        queryFn: () => api.api_Companies_retrieve(query) as Promise<CompanyResponse>,
        enabled: options?.enabled ?? true,
    });
}