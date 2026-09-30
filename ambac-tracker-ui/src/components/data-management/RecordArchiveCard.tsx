/**
 * Archive a record from its own edit page. Deleting archives (SecureModel soft
 * delete): the row leaves lists and pickers, its history stays, and the list's
 * "Show archived" can restore it. The table's name and list page come from the
 * Data Management registry.
 */
import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useQueryClient } from "@tanstack/react-query";
import { Archive } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
    AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
    AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { endpointFn } from "@/lib/api/endpoint-fn";
import { apiErrorBody, apiErrorField } from "@/lib/api/describeApiError";
import { ALL_TABLES } from "@/lib/data-management/tables";
import { getCookie } from "@/lib/utils";
import { useAllows } from "@/pages/scheduling/setup/shared";

export function RecordArchiveCard({ endpoint, id, model, listPath, thingName }: {
    /** Route under /api/ (e.g. "Equipment"). */
    endpoint: string;
    id: string;
    /** Model codename; `delete_<model>` shows the button. */
    model: string;
    /** Where to go after archiving, for a table sharing an endpoint (receiving plans are steps). */
    listPath?: string;
    /** What to call the record, likewise. */
    thingName?: string;
}) {
    const allows = useAllows();
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const [confirming, setConfirming] = useState(false);
    const [busy, setBusy] = useState(false);

    const destroy = endpointFn(endpoint, "destroy");
    const table = ALL_TABLES.find((t) => t.endpoint === endpoint);
    if (typeof destroy !== "function" || !allows(`delete_${model}`)) return null;
    const thing = thingName ?? (table ? table.name.replace(/s$/, "").toLowerCase() : "record");

    const archive = async () => {
        setBusy(true);
        try {
            await (destroy as (b: undefined, c: unknown) => Promise<unknown>)(undefined, {
                params: { id }, headers: { "X-CSRFToken": getCookie("csrftoken") },
            });
            toast.success(`Archived. "Show archived" on the list can restore it.`);
            queryClient.invalidateQueries();
            navigate({ to: listPath ?? table?.list ?? "/Edit" });
        } catch (e) {
            const body = apiErrorBody(e);
            toast.error(apiErrorField(body, "detail") ?? apiErrorField(body, "non_field_errors")
                ?? "Couldn't archive it — something still depends on it.");
        } finally {
            setBusy(false);
            setConfirming(false);
        }
    };

    return (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-dashed p-4">
            <div className="space-y-0.5">
                <p className="text-sm font-medium">Archive this {thing}</p>
                <p className="text-sm text-muted-foreground">
                    It leaves lists and pickers. Its history is kept, and it can be restored.
                </p>
            </div>
            <Button type="button" variant="outline" className="text-destructive" onClick={() => setConfirming(true)}>
                <Archive className="mr-1.5 h-4 w-4" /> Archive
            </Button>
            <AlertDialog open={confirming} onOpenChange={setConfirming}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Archive this {thing}?</AlertDialogTitle>
                        <AlertDialogDescription>
                            It stops appearing in lists and pickers. Records that already point at it keep
                            doing so, and "Show archived" on the list can restore it.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel disabled={busy}>Cancel</AlertDialogCancel>
                        <AlertDialogAction disabled={busy} onClick={(e) => { e.preventDefault(); void archive(); }}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
                            {busy ? "Archiving…" : "Archive"}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
}
