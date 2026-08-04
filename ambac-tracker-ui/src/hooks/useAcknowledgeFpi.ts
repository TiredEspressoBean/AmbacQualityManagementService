/** QA acknowledges a pending FPI ("I'm on it") — idempotent, first ack wins;
 *  the operator surface shows "Seen by X" from the record. */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

export function useAcknowledgeFpi() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (fpiId: string) =>
            api.api_FPIRecords_acknowledge_create(undefined as never, {
                params: { id: fpiId },
                // Every mutation in useFpiRecords.ts sends this; this hook was
                // the odd one out. A POST without it fails CSRF wherever the
                // session cookie isn't accompanied by a matching header.
                headers: { "X-CSRFToken": getCookie("csrftoken") ?? "" },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["pendingFpis"] });
            queryClient.invalidateQueries({ queryKey: ["inspectionInbox"] });
            // The WO-scoped Control panel reads `fpi-records`, not `pendingFpis`.
            queryClient.invalidateQueries({ queryKey: ["fpi-records"] });
        },
    });
}
