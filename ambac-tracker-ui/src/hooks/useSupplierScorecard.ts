import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { Schema } from "@/lib/api/types";

export const supplierScorecardOptions = (supplierId: string) =>
    queryOptions({
        queryKey: ["supplier-scorecard", supplierId] as const,
        queryFn: () =>
            api.api_Companies_scorecard_retrieve({ params: { id: supplierId } } as never) as Promise<
                Schema<"SupplierScorecard">
            >,
    });

export function useSupplierScorecard(supplierId: string | undefined) {
    return useQuery({
        ...supplierScorecardOptions(supplierId ?? ""),
        enabled: !!supplierId,
    });
}
