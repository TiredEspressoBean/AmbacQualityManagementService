import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

type MaterialLotListQueries = NonNullable<operations["api_MaterialLots_list"]["parameters"]["query"]>;
type MaterialLotListResponse = components["schemas"]["PaginatedMaterialLotList"];

type ListHookConfig = { headers?: Record<string, string> };

export const listMaterialLotsOptions = (queries?: MaterialLotListQueries, config?: ListHookConfig) =>
    queryOptions({
        queryKey: ["material-lots", queries, config] as const,
        queryFn: () =>
            api.api_MaterialLots_list(
                (queries || config ? { queries, ...config } : undefined) as never,
            ) as Promise<MaterialLotListResponse>,
    });

export function useListMaterialLots(
    queries?: MaterialLotListQueries,
    config?: ListHookConfig,
    options?: Omit<ReturnType<typeof listMaterialLotsOptions>, "queryKey" | "queryFn">,
) {
    return useQuery({
        ...listMaterialLotsOptions(queries, config),
        ...options,
    });
}
