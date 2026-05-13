import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { Schema } from "@/lib/api/types";

type CompanyResponse = Schema<"Company">;

export const retrieveCompanyOptions = (query: Parameters<typeof api.api_Companies_retrieve>[0]) => queryOptions({
    queryKey: ["company", query] as const,
    queryFn: () => api.api_Companies_retrieve(query) as Promise<CompanyResponse>,
});

export function useRetrieveCompany(query: Parameters<typeof api.api_Companies_retrieve>[0], options?: { enabled?: boolean }){
    return useQuery({ ...retrieveCompanyOptions(query), enabled: options?.enabled ?? true });
}