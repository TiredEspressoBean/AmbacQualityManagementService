/** Findings raised after teardown, waiting on a lead — shown on the unit's rebuild plan.
 *
 * An operator flags a component found worse than teardown graded it (the
 * RebuildFindingCapture DWI node). That is a proposal: the grade drives the slot's
 * resolution and so the rebuild's scope, so a lead applies it — the component takes the
 * new grade and this plan re-resolves — or dismisses it with a reason. Whether the new
 * scope needs the customer's authorisation stays the lead's call. A finding whose repair
 * the check pre-approves applies itself and never lands here; one that waits holds the
 * unit at its check (services/reman/repair_routing).
 * Documents/CORE_AS_PART_DESIGN.md; services/reman/findings.py.
 */
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { SearchCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
    AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
    AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api/generated";
import { retrieveHarvestedComponentsOptions } from "@/hooks/useRetrieveHarvestedComponents";
import { rebuildPlanOptions } from "@/hooks/useRebuildPlan";
import { getCookie } from "@/lib/utils";
import { apiErrorMessage } from "@/lib/api/describeApiError";

const headers = () => ({ "X-CSRFToken": getCookie("csrftoken") });

function detailOf(err: unknown, fallback: string) {
    return apiErrorMessage(err) ?? fallback;
}

export function PendingFindingsCard({ coreId }: { coreId: string }) {
    const qc = useQueryClient();
    const componentsQuery = retrieveHarvestedComponentsOptions({ core: coreId, limit: 200 });
    const { data } = useQuery(componentsQuery);
    const pending = (data?.results ?? []).filter((c) => !!c.proposed_grade);
    const [dismissing, setDismissing] = useState<{ id: string; name: string } | null>(null);
    const [reason, setReason] = useState("");

    const refresh = () => {
        qc.invalidateQueries(componentsQuery);
        qc.invalidateQueries(rebuildPlanOptions(coreId));
    };
    const apply = useMutation({
        mutationFn: (id: string) =>
            api.api_HarvestedComponents_apply_finding_create(undefined, { params: { id }, headers: headers() }),
        onSuccess: (c) => { toast.success(`${c.component_type_name}: grade is now ${c.condition_grade}`); refresh(); },
        onError: (e) => toast.error(detailOf(e, "Could not apply the finding.")),
    });
    const dismiss = useMutation({
        mutationFn: ({ id, why }: { id: string; why: string }) =>
            api.api_HarvestedComponents_dismiss_finding_create({ reason: why }, { params: { id }, headers: headers() }),
        onSuccess: () => { toast.success("Finding dismissed"); setDismissing(null); setReason(""); refresh(); },
        onError: (e) => toast.error(detailOf(e, "Could not dismiss the finding.")),
    });

    if (pending.length === 0) return null;

    return (
        <Card className="border-amber-400/70">
            <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                    <SearchCheck className="h-4 w-4" />
                    {pending.length} finding{pending.length === 1 ? "" : "s"} to decide
                </CardTitle>
                <CardDescription>
                    Raised at the bench after teardown, and not something a check pre-approves —
                    a routine repair applies itself. Nothing below has changed the plan yet:
                    applying one re-grades the component and this plan re-resolves from it.
                    Until you decide, the unit is held at the next check with repairs.
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 pt-0">
                {pending.map((c) => (
                    <div key={String(c.id)} className="flex flex-wrap items-start justify-between gap-3 rounded border p-3">
                        <div className="min-w-0 text-sm">
                            <div className="font-medium">
                                {c.component_type_name}
                                <span className="text-muted-foreground"> · {c.position || "no position"}</span>
                            </div>
                            <div className="tabular-nums">
                                Grade {c.condition_grade} → <span className="font-semibold">{c.proposed_grade}</span>
                            </div>
                            <p className="mt-1 text-muted-foreground">“{c.proposed_finding}”</p>
                            <p className="text-xs text-muted-foreground">
                                {c.proposed_by_name ?? "Unknown"}
                                {c.proposed_at ? ` · ${new Date(c.proposed_at).toLocaleString()}` : ""}
                            </p>
                        </div>
                        <div className="flex shrink-0 gap-2">
                            <Button size="sm" variant="outline"
                                    onClick={() => setDismissing({ id: String(c.id), name: c.component_type_name })}>
                                Dismiss
                            </Button>
                            {c.proposed_grade === "SCRAP" ? (
                                // Applying a scrap grade scraps the component outright — confirmed.
                                <AlertDialog>
                                    <AlertDialogTrigger asChild>
                                        <Button size="sm" disabled={apply.isPending}>Apply</Button>
                                    </AlertDialogTrigger>
                                    <AlertDialogContent>
                                        <AlertDialogHeader>
                                            <AlertDialogTitle>Scrap the {c.component_type_name}?</AlertDialogTitle>
                                            <AlertDialogDescription>
                                                It can't be reused: the component is scrapped, and the rebuild
                                                plan re-resolves to replace it. This can't be undone.
                                            </AlertDialogDescription>
                                        </AlertDialogHeader>
                                        <AlertDialogFooter>
                                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                                            <AlertDialogAction onClick={() => apply.mutate(String(c.id))}>
                                                Scrap component
                                            </AlertDialogAction>
                                        </AlertDialogFooter>
                                    </AlertDialogContent>
                                </AlertDialog>
                            ) : (
                                <Button size="sm" disabled={apply.isPending} onClick={() => apply.mutate(String(c.id))}>
                                    Apply
                                </Button>
                            )}
                        </div>
                    </div>
                ))}
            </CardContent>

            <Dialog open={!!dismissing} onOpenChange={(o) => { if (!o) { setDismissing(null); setReason(""); } }}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Dismiss the finding on {dismissing?.name}</DialogTitle>
                        <DialogDescription>
                            The grade stays as teardown recorded it. Say why, so the next person
                            to look at this unit knows it was considered.
                        </DialogDescription>
                    </DialogHeader>
                    <Textarea rows={3} value={reason} onChange={(e) => setReason(e.target.value)}
                              placeholder="e.g. Test rig out of calibration; retested within limits" />
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setDismissing(null)}>Cancel</Button>
                        <Button disabled={!reason.trim() || dismiss.isPending}
                                onClick={() => dismissing && dismiss.mutate({ id: dismissing.id, why: reason.trim() })}>
                            Dismiss finding
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </Card>
    );
}
