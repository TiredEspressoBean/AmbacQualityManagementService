/** Release, Obsolete and Reinstate on a controlled document — the document controller's
 *  acts (`release_documents`). Approval says the content is right; release puts it in
 *  force from an effective date (review and retention dates follow from the document
 *  type); obsolete retires it; reinstate undoes a mistaken obsolete while nothing has
 *  replaced it. All confirm first: they change what the floor works to. */
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Archive, Rocket } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
    AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
    AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api/generated";
import { apiErrorMessage } from "@/lib/api/describeApiError";
import { usePermissionSet } from "@/hooks/useMyPermissions";
import { getCookie } from "@/lib/utils";
import { ReasonActionButton } from "@/components/common/ReasonActionButton";

export function DocumentLifecycleActions({ document }: {
    document: {
        id: string | number; file_name?: string | null; status?: string | null;
        /** Set on an obsolete document a later revision replaced — it can't be reinstated. */
        superseded_by_version?: number | null;
        /** Its type; a type that needs no approval is released straight from Draft. */
        document_type_info?: unknown;
    };
}) {
    const qc = useQueryClient();
    const { has } = usePermissionSet();
    const [effective, setEffective] = useState("");
    const id = String(document.id);
    const headers = { "X-CSRFToken": getCookie("csrftoken") ?? "" };
    const refresh = () => qc.invalidateQueries({
        predicate: (q) => q.queryKey[0] === "document" || q.queryKey[0] === "documents",
    });
    const release = useMutation({
        mutationFn: () => api.api_Documents_release_create(
            effective ? { effective_date: effective } : {}, { params: { id }, headers }),
        onSuccess: () => { toast.success(`${document.file_name ?? "Document"} released`); refresh(); },
        onError: (e) => toast.error(apiErrorMessage(e) ?? "Couldn't release the document"),
        meta: { suppressGlobalError: true },
    });
    const obsolete = useMutation({
        mutationFn: () => api.api_Documents_mark_obsolete_create(undefined, { params: { id }, headers }),
        onSuccess: () => { toast.success(`${document.file_name ?? "Document"} marked obsolete`); refresh(); },
        onError: (e) => toast.error(apiErrorMessage(e) ?? "Couldn't mark the document obsolete"),
        meta: { suppressGlobalError: true },
    });

    if (!has("release_documents")) return null;
    const status = document.status ?? "";
    // A draft whose type needs no approval (a CoC, a test report…) is put in force
    // directly; the server holds the same rule (services/core/documents.py).
    const noApproval = (document.document_type_info as { requires_approval?: unknown } | null | undefined)
        ?.requires_approval === false;
    const releasable = status === "APPROVED" || (status === "DRAFT" && noApproval);
    return (
        <>
            {releasable && (
                <AlertDialog>
                    <AlertDialogTrigger asChild>
                        <Button disabled={release.isPending}>
                            <Rocket className="h-4 w-4 mr-2" /> Release
                        </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                        <AlertDialogHeader>
                            <AlertDialogTitle>Release {document.file_name}?</AlertDialogTitle>
                            <AlertDialogDescription>
                                It comes into force on the effective date, and its review and
                                retention dates are set from its document type. Work is done to it
                                from then on.
                            </AlertDialogDescription>
                        </AlertDialogHeader>
                        <div className="space-y-1.5">
                            <Label htmlFor="doc-effective">Effective date (blank = today)</Label>
                            <Input id="doc-effective" type="date" value={effective}
                                   onChange={(e) => setEffective(e.target.value)} />
                        </div>
                        <AlertDialogFooter>
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction onClick={() => release.mutate()}>Release</AlertDialogAction>
                        </AlertDialogFooter>
                    </AlertDialogContent>
                </AlertDialog>
            )}
            {(status === "APPROVED" || status === "RELEASED") && (
                <AlertDialog>
                    <AlertDialogTrigger asChild>
                        <Button variant="outline" disabled={obsolete.isPending}>
                            <Archive className="h-4 w-4 mr-2" /> Mark obsolete
                        </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                        <AlertDialogHeader>
                            <AlertDialogTitle>Mark {document.file_name} obsolete?</AlertDialogTitle>
                            <AlertDialogDescription>
                                It is withdrawn from use from today and kept for its retention
                                period. Marked obsolete by mistake, it can be reinstated while no
                                later revision has replaced it.
                            </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction onClick={() => obsolete.mutate()}>Mark obsolete</AlertDialogAction>
                        </AlertDialogFooter>
                    </AlertDialogContent>
                </AlertDialog>
            )}
            {status === "OBSOLETE" && !document.superseded_by_version && (
                <ReasonActionButton
                    label="Reinstate" size="default"
                    title={`Reinstate ${document.file_name ?? "this document"}`}
                    description={<>Marked obsolete by mistake: it goes back in force — released again if it had
                        been released — and its obsolete date clears. Your reason is kept on the document.</>}
                    placeholder="Why — e.g. obsoleted the wrong work instruction"
                    done={`${document.file_name ?? "Document"} reinstated`}
                    run={(reason) => api.api_Documents_reinstate_create({ reason }, { params: { id }, headers })}
                />
            )}
        </>
    );
}
