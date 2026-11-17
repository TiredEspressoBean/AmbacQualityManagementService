/** A harvested part reserved to its core (the customer's property under repair-and-
 *  return), and the way to free it when the arrangement changed: Release reservation,
 *  for whoever may reserve one (accept_component). Its refusal elsewhere says "release
 *  the reservation first" — this is where (doc audit 2026-11-17). */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { usePermissionSet } from "@/hooks/useMyPermissions";
import { api } from "@/lib/api/generated";
import { apiErrorBody } from "@/lib/api/describeApiError";
import { getCookie } from "@/lib/utils";

export function PartReservationNotice({ partId, coreNumber }: { partId: string; coreNumber: string | null | undefined }) {
    const { has } = usePermissionSet();
    const queryClient = useQueryClient();
    const release = useMutation({
        mutationFn: () => api.api_Parts_release_reservation_create(undefined, {
            params: { id: partId },
            headers: { "X-CSRFToken": getCookie("csrftoken") ?? "" },
        }),
        meta: { suppressGlobalError: true },
        onSuccess: () => {
            toast.success("Reservation released — the part is general stock now.");
            void queryClient.invalidateQueries();
        },
        onError: (e) => {
            const detail = (apiErrorBody(e) as { detail?: unknown } | undefined)?.detail;
            toast.error("Couldn't release the reservation", {
                description: typeof detail === "string" ? detail : undefined,
            });
        },
    });
    if (!coreNumber) return null;
    return (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm dark:border-amber-800 dark:bg-amber-950/30">
            <p>
                Reserved for core <span className="font-mono font-medium">{coreNumber}</span> — harvested
                from a unit being repaired and returned, so it's that customer's property and can't be
                built into other work.
            </p>
            {has("accept_component") && (
                <Button variant="outline" size="sm" disabled={release.isPending}
                    onClick={() => {
                        if (window.confirm(`Release this part from core ${coreNumber}? It becomes general stock and can be used on any job. Do this only if the customer's arrangement changed.`)) {
                            release.mutate();
                        }
                    }}>
                    Release reservation
                </Button>
            )}
        </div>
    );
}
