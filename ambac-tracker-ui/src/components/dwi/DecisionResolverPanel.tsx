/**
 * Decision-point resolver (4a).
 *
 * Surfaces when the part's current step is a decision point:
 *   - QA_RESULT → routes automatically from the QualityReport. Informational
 *     only; the operator completes the step normally and the engine picks the
 *     branch from the inspection result.
 *   - MANUAL → a manager/lead picks the routing branch (DEFAULT/ALTERNATE).
 *     Gated server-side by `resolve_step_decision`; the buttons are hidden
 *     for users without it.
 *
 * Branch labels come from the resolved StepEdges so the operator sees real
 * target step names ("Pass → Final Test" / "Fail → Rework").
 */
import { useState } from "react";
import { GitBranch, Loader2, ArrowRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { useDecisionOptions, useResolveDecision } from "@/hooks/parts";
import { usePermissionSet } from "@/hooks/useMyPermissions";

export function DecisionResolverPanel({
    partId,
    onResolved,
}: {
    partId: string;
    onResolved?: () => void;
}) {
    const { data } = useDecisionOptions(partId);
    const { has } = usePermissionSet();
    const resolve = useResolveDecision();
    const [pending, setPending] = useState<"DEFAULT" | "ALTERNATE" | null>(null);

    if (!data?.is_decision_point) return null;

    const def = data.default_branch ?? null;
    const alt = data.alternate_branch ?? null;

    // ---- QA_RESULT: automatic routing from the inspection result ----
    if (data.decision_type === "QA_RESULT") {
        const suggestedTarget =
            data.qa_suggested === "PASS"
                ? def?.step_name
                : data.qa_suggested
                    ? alt?.step_name
                    : null;
        return (
            <div className="rounded-lg border bg-card p-3">
                <div className="flex items-center gap-2">
                    <GitBranch className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm font-medium">Decision point</span>
                    <Badge variant="secondary" className="text-[10px]">Auto · QA result</Badge>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                    Routes automatically from the inspection result when you complete the step —
                    pass takes <span className="font-medium">{def?.step_name ?? "the next step"}</span>,
                    fail takes <span className="font-medium">{alt?.step_name ?? "the rework branch"}</span>.
                </p>
                {data.qa_suggested && (
                    <p className="mt-1 text-xs">
                        Latest inspection: <span className="font-medium">{data.qa_suggested}</span>
                        {suggestedTarget && (
                            <span className="text-muted-foreground"> → {suggestedTarget}</span>
                        )}
                    </p>
                )}
            </div>
        );
    }

    // ---- MANUAL: manager/lead picks the branch ----
    const canResolve = has("resolve_step_decision");

    const choose = (decision: "DEFAULT" | "ALTERNATE") => {
        setPending(decision);
        resolve.mutate(
            { partId, decision },
            {
                onSuccess: (r) => {
                    toast.success(`Routed to ${r.new_step_name ?? "the next step"}.`);
                    onResolved?.();
                },
                onError: (err: unknown) => {
                    const detail = (err as { response?: { data?: { detail?: string } } })
                        ?.response?.data?.detail;
                    toast.error(detail ?? "Couldn't resolve the decision.");
                },
                onSettled: () => setPending(null),
            },
        );
    };

    return (
        <div className="rounded-lg border border-amber-500/40 bg-amber-50/50 p-3 dark:bg-amber-950/20">
            <div className="flex items-center gap-2">
                <GitBranch className="h-4 w-4 text-amber-600" />
                <span className="text-sm font-medium">Decision required — choose the routing branch</span>
                <Badge variant="secondary" className="text-[10px]">Manual</Badge>
            </div>

            {!canResolve ? (
                <p className="mt-2 text-xs text-muted-foreground">
                    A manager or lead must resolve this decision — you don't have permission to
                    pick the routing branch.
                </p>
            ) : (
                <div className="mt-2 flex flex-wrap gap-2">
                    <Button
                        size="sm"
                        variant="default"
                        disabled={pending !== null || !def}
                        onClick={() => choose("DEFAULT")}
                        title={def ? `Route to ${def.step_name}` : "No pass branch configured"}
                    >
                        {pending === "DEFAULT" ? (
                            <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                        ) : (
                            <ArrowRight className="mr-1 h-3 w-3" />
                        )}
                        Pass → {def?.step_name ?? "—"}
                    </Button>
                    <Button
                        size="sm"
                        variant="outline"
                        disabled={pending !== null || !alt}
                        onClick={() => choose("ALTERNATE")}
                        title={alt ? `Route to ${alt.step_name}` : "No fail/rework branch configured"}
                    >
                        {pending === "ALTERNATE" ? (
                            <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                        ) : (
                            <ArrowRight className="mr-1 h-3 w-3" />
                        )}
                        Fail / rework → {alt?.step_name ?? "—"}
                    </Button>
                </div>
            )}
        </div>
    );
}
