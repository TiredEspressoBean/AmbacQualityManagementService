/** Unified incoming-inspection worklist (purchased lots + subcontract returns). */
import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { components } from "@/lib/api/generated-types";

export type IncomingInspectionRow = components["schemas"]["IncomingInspectionRow"];

export const incomingInspectionOptions = () =>
    queryOptions({
        queryKey: ["incomingInspection"] as const,
        queryFn: () => api.api_IncomingInspection_list() as Promise<IncomingInspectionRow[]>,
        staleTime: 15_000,
    });

export function useIncomingInspection() {
    return useQuery(incomingInspectionOptions());
}
