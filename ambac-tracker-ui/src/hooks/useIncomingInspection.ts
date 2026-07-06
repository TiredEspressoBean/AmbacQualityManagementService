/** Unified incoming-inspection worklist (purchased lots + subcontract returns). */
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { components } from "@/lib/api/generated-types";

export type IncomingInspectionRow = components["schemas"]["IncomingInspectionRow"];

export function useIncomingInspection() {
    return useQuery({
        queryKey: ["incomingInspection"] as const,
        queryFn: () => api.api_IncomingInspection_list() as Promise<IncomingInspectionRow[]>,
        staleTime: 15_000,
    });
}
