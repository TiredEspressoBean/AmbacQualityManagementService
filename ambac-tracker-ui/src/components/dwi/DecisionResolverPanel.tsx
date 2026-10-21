/**
 * Decision-point resolver (4a).
 *
 * Surfaces when the part's current step is a decision point:
 *   - QA_RESULT → routes automatically from the QualityReport. Informational
 *     only; the operator completes the step normally and the engine picks the
 *     branch from the inspection result.
 *   - MANUAL → a manager/lead picks the routing branch (DEFAULT/ALTERNATE).
 *     Gated server-side by `resolve_step_decision`. An operator without it sees
 *     the same two branch buttons; choosing one opens a co-signature dialog
 *     where a lead authenticates inline at that station. Previously this
 *     rendered a sentence and no affordance, which stopped the part dead
 *     until someone found a lead with their own terminal.
 *
 * Branch labels come from the resolved StepEdges so the operator sees real
 * target step names ("Pass → Final Test" / "Fail → Rework").
 *
 * A reman check with Repair nodes (services/reman/repair_routing, 2026-10-12) also
 * lists the repairs it offers — pre-approved or needing approval, and which this unit
 * needs — and names the hold it would meet leaving now, in the words that decide it.
 */
import { useState } from "react";
import { GitBranch, Loader2, ArrowRight, Wrench } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { useDecisionOptions, useResolveDecision, type RepairBranch } from "@/hooks/parts";
import { useCoreLifecycleAction } from "@/hooks/useReleaseCore";
import { usePermissionSet } from "@/hooks/useMyPermissions";
import { SecondPersonCosignDialog } from "@/components/second-person-cosign-dialog";
import { apiErrorMessage } from "@/lib/api/describeApiError";

/** The repairs this check offers, and the hold the unit meets leaving now. A repair
 *  this unit needs that isn't approved yet can be approved here by a lead (exchange
 *  unit) or sent for the customer's authorisation (their own unit). */
function RepairBranches({ branches, hold, coreId, customerUnit }: {
    branches: RepairBranch[];
    hold: string | null;
    coreId: string | null;
    customerUnit: boolean;
}) {
    const { has } = usePermissionSet();
    const act = useCoreLifecycleAction();
    if (branches.length === 0) return null;
    const waiting = branches.filter((b) => b.needed && !b.approved);
    const run = (v: Parameters<typeof act.mutate>[0], done: string) =>
        act.mutate(v, {
            onSuccess: () => toast.success(done),
            onError: (e) => toast.error(apiErrorMessage(e) ?? "Couldn't record that."),
        });
    return (
        <div className="rounded-lg border bg-card p-3">
            <div className="flex items-center gap-2">
                <Wrench className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">Repairs at this check</span>
            </div>
            <ul className="mt-2 space-y-1.5">
                {branches.map((b) => (
                    <li key={b.step_id} className="flex flex-wrap items-center gap-2 text-sm">
                        <span className="font-mono text-xs">{b.code}</span>
                        <span>{b.step_name}</span>
                        {b.pre_approved ? (
                            <Badge variant="secondary" className="text-[10px]">Pre-approved</Badge>
                        ) : (
                            <Badge variant="outline" className="text-[10px]">Needs approval</Badge>
                        )}
                        {b.needed && (
                            <Badge variant={b.approved ? "default" : "destructive"} className="text-[10px]">
                                {b.approved ? "This unit goes here" : "Needed — waiting for approval"}
                            </Badge>
                        )}
                    </li>
                ))}
            </ul>
            <p className="mt-2 text-xs text-muted-foreground">
                The unit takes a repair only when its finding raises that repair's code;
                otherwise it continues down the line.
            </p>
            {hold && (
                <p role="status" className="mt-2 rounded-md border border-amber-500/40 bg-amber-50/60 p-2 text-sm dark:bg-amber-950/20">
                    {hold}
                </p>
            )}
            {coreId && waiting.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                    {customerUnit ? (
                        has("change_core") && (
                            <Button size="sm" variant="outline" disabled={act.isPending}
                                onClick={() => run({ id: coreId, action: "request_authorisation" },
                                    "Sent for the customer's authorisation — record their answer on the work order.")}>
                                Send for the customer's authorisation
                            </Button>
                        )
                    ) : (
                        has("accept_component") && waiting.map((b) => (
                            <Button key={b.code} size="sm" variant="outline" disabled={act.isPending}
                                onClick={() => run({ id: coreId, action: "approve_repair", code: b.code },
                                    `${b.code} approved for this unit.`)}>
                                Approve {b.code}
                            </Button>
                        ))
                    )}
                </div>
            )}
        </div>
    );
}

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
    /** Which branch is awaiting a lead's co-signature, if any. */
    const [cosignFor, setCosignFor] = useState<"DEFAULT" | "ALTERNATE" | null>(null);
    const [cosignError, setCosignError] = useState<string | null>(null);

    const repairs = (
        <RepairBranches
            branches={data?.repair_branches ?? []}
            hold={data?.repair_hold ?? null}
            coreId={data?.repair_core_id ?? null}
            customerUnit={!!data?.repair_customer_unit}
        />
    );
    if (!data?.is_decision_point) return repairs;

    const def = data.default_branch ?? null;
    const alt = data.alternate_branch ?? null;

    // ---- QA_RESULT: automatic routing from the inspection result ----
    if (data.decision_type === "QA_RESULT") {
        // Only a decided result routes. A PENDING report used to show "→ Rework", as
        // if a result not yet in sends the part to the rework branch.
        const suggestedTarget =
            data.qa_suggested === "PASS"
                ? def?.step_name
                : data.qa_suggested === "FAIL"
                    ? alt?.step_name
                    : null;
        return (
            <div className="space-y-2">
            {repairs}
            <div className="rounded-lg border bg-card p-3">
                <div className="flex items-center gap-2">
                    <GitBranch className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm font-medium">Decision point</span>
                    <Badge variant="secondary" className="text-[10px]">Auto · QA result</Badge>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                    Routes automatically from the inspection result when you complete the step —
                    pass takes <span className="font-medium">{def?.step_name ?? "the next step"}</span>,
                    fail takes <span className="font-medium">{alt?.step_name ?? "the rework branch"}</span>
                    {(data.repair_branches ?? []).length > 0
                        ? ", and Needs repair takes the repair its finding raises."
                        : "."}
                </p>
                {data.qa_suggested && (
                    <p className="mt-1 text-xs">
                        Latest inspection: <span className="font-medium">
                            {data.qa_suggested === "REPAIR" ? "Needs repair" : data.qa_suggested}</span>
                        {data.qa_suggested === "REPAIR" ? (
                            // Never the rework branch: the finding's repair, or a hold.
                            <span className="text-muted-foreground"> → the repair its finding raises (shown above)</span>
                        ) : suggestedTarget ? (
                            <span className="text-muted-foreground"> → {suggestedTarget}</span>
                        ) : (
                            <span className="text-muted-foreground"> — routes once the result is in</span>
                        )}
                    </p>
                )}
            </div>
            </div>
        );
    }

    // ---- MANUAL: manager/lead picks the branch ----
    const canResolve = has("resolve_step_decision");

    const choose = (
        decision: "DEFAULT" | "ALTERNATE",
        cosign?: { email: string; password: string },
    ) => {
        setPending(decision);
        setCosignError(null);
        resolve.mutate(
            {
                partId,
                decision,
                ...(cosign
                    ? { cosign_email: cosign.email, cosign_password: cosign.password }
                    : {}),
            },
            {
                onSuccess: (r) => {
                    const by = cosign && r.decided_by ? ` — resolved by ${r.decided_by}` : "";
                    toast.success(`Routed to ${r.new_step_name ?? "the next step"}${by}.`);
                    setCosignFor(null);
                    onResolved?.();
                },
                onError: (err: unknown) => {
                    const detail = apiErrorMessage(err);
                    const msg = detail ?? "Couldn't resolve the decision.";
                    // Keep the dialog open on a co-sign failure so the lead can
                    // retype, and show the server's reason there rather than
                    // only in a toast that vanishes.
                    if (cosign) setCosignError(msg);
                    toast.error(msg);
                },
                onSettled: () => setPending(null),
            },
        );
    };

    // Without the permission, picking a branch opens the co-sign dialog instead
    // of posting directly.
    const pick = (decision: "DEFAULT" | "ALTERNATE") =>
        canResolve ? choose(decision) : setCosignFor(decision);

    return (
        <div className="space-y-2">
        {repairs}
        <div className="rounded-lg border border-amber-500/40 bg-amber-50/50 p-3 dark:bg-amber-950/20">
            <div className="flex items-center gap-2">
                <GitBranch className="h-4 w-4 text-amber-600" />
                <span className="text-sm font-medium">Decision required — choose the routing branch</span>
                <Badge variant="secondary" className="text-[10px]">Manual</Badge>
            </div>

            {!canResolve && (
                <p className="mt-2 text-xs text-muted-foreground">
                    A manager or lead must resolve this decision. Pick the branch and they can
                    sign here — no need to log you out.
                </p>
            )}

            <div className="mt-2 flex flex-wrap gap-2">
                <Button
                    size="sm"
                    variant="default"
                    disabled={pending !== null || !def}
                    onClick={() => pick("DEFAULT")}
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
                    onClick={() => pick("ALTERNATE")}
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

            {cosignFor && (
                <SecondPersonCosignDialog
                    open
                    onOpenChange={(v) => {
                        if (!v) {
                            setCosignFor(null);
                            setCosignError(null);
                        }
                    }}
                    title="Manager sign-off — routing decision"
                    description={
                        `By signing you choose the ${cosignFor === "DEFAULT" ? "pass" : "fail / rework"} ` +
                        `branch${(cosignFor === "DEFAULT" ? def?.step_name : alt?.step_name)
                            ? ` (→ ${cosignFor === "DEFAULT" ? def?.step_name : alt?.step_name})` : ""}` +
                        ". The routing is recorded against your name, not the person logged in."
                    }
                    emailLabel="Manager or lead email"
                    confirmationText="I confirm this is my signature and I am authorized to resolve this routing decision."
                    confirmLabel="Confirm routing"
                    error={cosignError}
                    pending={pending !== null}
                    onConfirm={({ email, password }) =>
                        choose(cosignFor, { email, password })
                    }
                />
            )}
        </div>
        </div>
    );
}
