/** The QA inspector's task inbox — one flat list across every inspection
 *  source (FPI / receiving / OSP / in-process). Standard list-of-rows
 *  contract (the useIncomingInspection pattern); derive type-count chips
 *  from the rows. See services.qms.inspection_inbox for tone rules. */
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { components } from "@/lib/api/generated-types";

export type InspectionInboxRow = components["schemas"]["InspectionInboxRow"];

export function useInspectionInbox() {
    return useQuery({
        queryKey: ["inspectionInbox"] as const,
        queryFn: () => api.api_InspectionInbox_list() as Promise<InspectionInboxRow[]>,
        staleTime: 15_000,
    });
}
