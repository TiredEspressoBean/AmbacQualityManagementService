/** QA acknowledges a pending FPI ("I'm on it") — idempotent, first ack wins;
 *  the operator surface shows "Seen by X" from the record. */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export function useAcknowledgeFpi() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (fpiId: string) =>
            api.api_FPIRecords_acknowledge_create(undefined as never, { params: { id: fpiId } }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["pendingFpis"] });
            queryClient.invalidateQueries({ queryKey: ["inspectionInbox"] });
        },
    });
}
