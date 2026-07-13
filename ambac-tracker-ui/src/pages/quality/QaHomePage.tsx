/**
 * The QA inspector's real landing — the task-inbox tier, live data.
 *
 * Productionizes /dev/qa-home (see Documents/OPERATOR_EXPERIENCE_DESIGN.md §6):
 *  - TASK INBOX, not a metrics dashboard; one flat list, never WO-grouped.
 *  - First-piece requests are QUEUE-JUMPERS with andon semantics: pinned
 *    banner, live waiting age, acknowledge ("I'm on it") → the operator's
 *    surface shows "Seen by X" from the same record.
 *  - Type-count chips filter the flat list; oldest-age under each chip
 *    (counts alone hide rot). Zero-count chips hide.
 *  - Four-state due dot per row; sampling shown as the ANSWER ("n=13 · Ac 1");
 *    severity badges explain the switch-back rule; blocked rows sink but stay
 *    counted; partially-captured lots show resume progress.
 *  - "Available to claim": group-eligible approvals nobody has picked up.
 *  - Personal gauge-calibration nag pre-empts the point-of-use gate.
 *  - Deliberately absent: batch-approve, throughput-vs-goal, MRU lists.
 */
import { useMemo, useState } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
    ArrowRight, CheckCircle2, ClipboardCheck, Gauge, Inbox, PackageSearch,
    PauseCircle, Ruler, Siren, Truck,
} from "lucide-react";
import { useAuthUser, type AuthUser } from "@/hooks/useAuthUser";
import { useAcknowledgeFpi } from "@/hooks/useAcknowledgeFpi";
import { useClaimApproval } from "@/hooks/useClaimApproval";
import { useClaimableApprovals } from "@/hooks/useClaimableApprovals";
import { useGaugeNag } from "@/hooks/useGaugeNag";
import { useInspectionInbox, type InspectionInboxRow } from "@/hooks/useInspectionInbox";
import { useMyCapaTasks } from "@/hooks/useMyCapaTasks";
import { useMyDispositions } from "@/hooks/useMyDispositions";
import { useMyPendingApprovals } from "@/hooks/useMyPendingApprovals";
import { usePendingFpis } from "@/hooks/usePendingFpis";

type InboxType = InspectionInboxRow["type"];

const DUE_DOT: Record<string, string> = {
    red: "bg-red-500", orange: "bg-orange-400", green: "bg-emerald-500", gray: "bg-muted-foreground/40",
};

const TYPE_META: Record<string, { label: string; icon: React.ComponentType<{ className?: string }> }> = {
    receiving: { label: "Receiving", icon: PackageSearch },
    outside_process: { label: "OSP returns", icon: Truck },
    in_process: { label: "In-process", icon: Ruler },
    fpi: { label: "First piece", icon: ClipboardCheck },
};

/** "0.6" hours → "35m"; "5" → "5h"; "50" → "2d". */
function formatAge(hours: number | null | undefined): string {
    if (hours == null) return "";
    if (hours < 1) return `${Math.max(1, Math.round(hours * 60))}m`;
    if (hours < 24) return `${Math.round(hours)}h`;
    return `${Math.round(hours / 24)}d`;
}

function severityWhy(sev: NonNullable<InspectionInboxRow["severity"]>): string {
    const since = sev.severity_since ? ` since ${sev.severity_since.slice(0, 10)}` : "";
    if (sev.severity === "TIGHTENED") {
        const tail = sev.accepts_needed != null
            ? ` ${sev.accepts_needed} more accepted lot${sev.accepts_needed === 1 ? "" : "s"} returns to Normal.`
            : "";
        return `Tightened${since} (${sev.rejects_in_window} rejected in the last 5 lots).${tail}`;
    }
    if (sev.severity === "REDUCED") {
        return `Reduced${since} — one rejected (or gap) lot returns to Normal.`;
    }
    return `Normal${since}.`;
}

// ---------------------------------------------------------------------------
// FPI queue-jumper banner — andon semantics. A machine and an operator may be
// idle behind each pending first piece; the age is the urgency.
// ---------------------------------------------------------------------------

function FpiBanner() {
    const navigate = useNavigate();
    const { data: fpis = [] } = usePendingFpis();
    const acknowledge = useAcknowledgeFpi();

    if (fpis.length === 0) return null;

    return (
        <div className="space-y-2">
            {fpis.slice(0, 3).map((f) => {
                const ageMs = f.created_at ? Date.now() - new Date(f.created_at).getTime() : null;
                const age = ageMs != null ? formatAge(ageMs / 3_600_000) : "";
                const seenBy = f.acknowledged_by_info?.first_name || f.acknowledged_by_info?.username;
                return (
                    <div
                        key={f.id}
                        className="flex items-center gap-3 rounded-xl border-2 border-red-300 bg-red-50 p-3 dark:border-red-900 dark:bg-red-950"
                    >
                        <Siren className="h-7 w-7 shrink-0 text-red-600" />
                        <div className="min-w-0 flex-1">
                            <div className="font-semibold">
                                First piece waiting{f.step_info?.name ? ` — ${f.step_info.name}` : ""}
                            </div>
                            <div className="truncate text-sm text-muted-foreground">
                                {[
                                    f.work_order_info?.erp_id,
                                    f.equipment_info?.name,
                                    f.designated_part_info?.erp_id,
                                ].filter(Boolean).join(" · ") || f.part_type_info?.name || ""}
                            </div>
                        </div>
                        {age && (
                            <div className="shrink-0 text-right">
                                <div className="font-mono text-lg font-semibold text-red-600">{age}</div>
                                <div className="text-xs text-muted-foreground">waiting</div>
                            </div>
                        )}
                        {seenBy ? (
                            <Badge variant="outline" className="shrink-0">Seen by {seenBy}</Badge>
                        ) : (
                            <Button
                                variant="outline" className="shrink-0"
                                disabled={acknowledge.isPending}
                                onClick={() =>
                                    acknowledge.mutate(f.id, {
                                        onSuccess: () => toast.success("Acknowledged — the operator sees you're on it."),
                                        onError: () => toast.error("Could not acknowledge."),
                                    })
                                }
                            >
                                I'm on it
                            </Button>
                        )}
                        {f.work_order_info?.id && (
                            <Button
                                className="h-12 shrink-0"
                                onClick={() => navigate({
                                    to: "/workorder/$workOrderId/control",
                                    params: { workOrderId: String(f.work_order_info!.id) },
                                })}
                            >
                                Start check
                            </Button>
                        )}
                    </div>
                );
            })}
        </div>
    );
}

// ---------------------------------------------------------------------------
// The inbox — one flat list + count-filter chips.
// ---------------------------------------------------------------------------

function InboxList() {
    const navigate = useNavigate();
    const { data: allRows = [], isLoading } = useInspectionInbox();
    const [typeFilter, setTypeFilter] = useState<InboxType | "all">("all");

    // FPI rows live in the banner, not the list.
    const rows = useMemo(() => allRows.filter((r) => r.type !== "fpi"), [allRows]);
    const visible = typeFilter === "all" ? rows : rows.filter((r) => r.type === typeFilter);
    // Chips derive from the rows: count + oldest-age per type (counts alone hide rot).
    const counts = useMemo(() => {
        const acc: Record<string, { count: number; oldest_age_hours: number | null }> = {};
        for (const r of rows) {
            const c = (acc[r.type] ??= { count: 0, oldest_age_hours: null });
            c.count += 1;
            if (r.age_hours != null) {
                c.oldest_age_hours = Math.max(c.oldest_age_hours ?? 0, r.age_hours);
            }
        }
        return acc;
    }, [rows]);
    const chipTypes = (Object.keys(TYPE_META) as InboxType[])
        .filter((t) => t !== "fpi" && (counts[t]?.count ?? 0) > 0);
    const overdue = rows.filter((r) => r.due_tone === "red").length;

    const open = (row: InspectionInboxRow) => {
        if (row.blocked_reason) {
            toast.info(`Held: ${row.blocked_reason.replace(/_/g, " ").toLowerCase()}`, {
                description: "Resolve the hold from the incoming queue.",
            });
            return;
        }
        if (row.subject_kind === "material_lot") {
            navigate({ to: "/production/receiving-inspection/$lotId", params: { lotId: row.id } });
        } else if (row.subject_kind === "shipment") {
            navigate({ to: "/production/incoming" });
        } else if (row.subject_kind === "operation") {
            const workOrderId = row.id.split(":")[0];
            navigate({ to: "/workorder/$workOrderId/control", params: { workOrderId } });
        }
    };

    return (
        <div className="rounded-xl border bg-card p-4">
            <div className="flex flex-wrap items-center gap-2">
                <Inbox className="h-4 w-4 text-muted-foreground" />
                <button
                    onClick={() => setTypeFilter("all")}
                    className={`rounded-full border px-3 py-1 text-sm transition-colors ${typeFilter === "all" ? "border-primary bg-primary/10 font-medium" : "hover:bg-accent"}`}
                >
                    All {rows.length}
                </button>
                {chipTypes.map((t) => (
                    <button
                        key={t}
                        onClick={() => setTypeFilter(typeFilter === t ? "all" : t)}
                        className={`rounded-full border px-3 py-1 text-sm transition-colors ${typeFilter === t ? "border-primary bg-primary/10 font-medium" : "hover:bg-accent"}`}
                        title={counts[t]?.oldest_age_hours != null ? `oldest: ${formatAge(counts[t]!.oldest_age_hours)}` : undefined}
                    >
                        {TYPE_META[t].label} {counts[t]?.count}
                        {counts[t]?.oldest_age_hours != null && (
                            <span className="ml-1 text-xs text-muted-foreground">· {formatAge(counts[t]!.oldest_age_hours)}</span>
                        )}
                    </button>
                ))}
                {overdue > 0 && (
                    <span className="ml-auto rounded-full bg-red-100 px-3 py-1 text-sm font-medium text-red-700 dark:bg-red-900 dark:text-red-300">
                        Urgent {overdue}
                    </span>
                )}
            </div>

            <div className="mt-3 space-y-1">
                {isLoading && <p className="p-2 text-sm text-muted-foreground">Loading inbox…</p>}
                {!isLoading && visible.length === 0 && (
                    <div className="flex items-center justify-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-5 text-sm text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-300">
                        <CheckCircle2 className="h-4 w-4" /> All caught up — nothing awaiting inspection.
                    </div>
                )}
                {visible.map((row) => {
                    const T = TYPE_META[row.type] ?? TYPE_META.in_process;
                    return (
                        <button
                            key={`${row.type}:${row.id}`}
                            onClick={() => open(row)}
                            className={`flex w-full items-center gap-3 rounded-lg border p-2.5 text-left transition-colors hover:bg-accent ${row.blocked_reason ? "opacity-55" : ""}`}
                        >
                            <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${DUE_DOT[row.due_tone] ?? DUE_DOT.gray}`} />
                            <T.icon className="h-4 w-4 shrink-0 text-muted-foreground" />
                            <span className="min-w-0 flex-1">
                                <span className="flex items-center gap-2">
                                    <span className="min-w-0 truncate text-sm font-medium">{row.title}</span>
                                    {row.severity && row.severity.severity !== "NORMAL" && (
                                        <Badge
                                            title={severityWhy(row.severity)}
                                            className={row.severity.severity === "TIGHTENED"
                                                ? "bg-amber-100 text-amber-700 hover:bg-amber-100 dark:bg-amber-900 dark:text-amber-300"
                                                : "bg-emerald-100 text-emerald-700 hover:bg-emerald-100 dark:bg-emerald-900 dark:text-emerald-300"}
                                        >
                                            {row.severity.severity === "TIGHTENED" ? "Tightened" : "Reduced"}
                                        </Badge>
                                    )}
                                    {row.resume && (
                                        <span className="flex shrink-0 items-center gap-1 text-xs text-blue-600 dark:text-blue-400">
                                            <PauseCircle className="h-3 w-3" /> {row.resume}
                                        </span>
                                    )}
                                </span>
                                <span className="block truncate text-xs text-muted-foreground">
                                    {row.detail}
                                    {row.wo ? <> · <span className="font-mono">{row.wo}</span></> : null}
                                    {row.blocked_reason ? (
                                        <> · <span className="text-amber-700 dark:text-amber-400">
                                            ⏸ {row.blocked_reason.replace(/_/g, " ").toLowerCase()}
                                        </span></>
                                    ) : null}
                                </span>
                            </span>
                            {row.plan && (
                                <span className="shrink-0 rounded border px-1.5 py-0.5 font-mono text-xs text-muted-foreground">{row.plan}</span>
                            )}
                            <span className="w-28 shrink-0 text-right text-xs text-muted-foreground">
                                {row.due_label || (row.age_hours != null ? `${formatAge(row.age_hours)} old` : "")}
                            </span>
                        </button>
                    );
                })}
            </div>
        </div>
    );
}

// ---------------------------------------------------------------------------
// My quality actions + available-to-claim + gauge nag.
// ---------------------------------------------------------------------------

function MyActionsPanel({ user }: { user: AuthUser }) {
    const { data: approvals = [] } = useMyPendingApprovals();
    const { data: tasks = [] } = useMyCapaTasks();
    const { data: claimable = [] } = useClaimableApprovals();
    const claim = useClaimApproval();
    const { data: dispositions = [] } = useMyDispositions(user.pk);

    const openTasks = tasks.filter((t) => t.status !== "COMPLETED");
    const overdue = openTasks.filter((t) => t.due_date && new Date(t.due_date) < new Date()).length
        + approvals.filter((a) => a.is_overdue).length;

    return (
        <div className="rounded-xl border bg-card p-4 md:col-span-2">
            <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                My quality actions
                {overdue > 0 && <Badge variant="destructive">{overdue} overdue</Badge>}
            </div>
            <div className="mt-2 grid grid-cols-3 gap-3 text-center">
                <Link to="/inbox" className="rounded-md border p-2 transition-colors hover:bg-accent">
                    <div className="text-xl font-semibold tabular-nums">{approvals.length}</div>
                    <div className="text-xs text-muted-foreground">Approvals</div>
                </Link>
                <Link to="/inbox" className="rounded-md border p-2 transition-colors hover:bg-accent">
                    <div className={`text-xl font-semibold tabular-nums ${overdue > 0 ? "text-destructive" : ""}`}>
                        {openTasks.length}
                    </div>
                    <div className="text-xs text-muted-foreground">CAPA tasks</div>
                </Link>
                <Link to="/production/dispositions" className="rounded-md border p-2 transition-colors hover:bg-accent">
                    <div className="text-xl font-semibold tabular-nums">{dispositions.length}</div>
                    <div className="text-xs text-muted-foreground">My dispositions</div>
                </Link>
            </div>

            {claimable.length > 0 && (
                <div className="mt-3">
                    <div className="text-xs text-muted-foreground">
                        Available to claim — your group is eligible, nobody has it:
                    </div>
                    {claimable.map((c) => (
                        <div key={c.id} className="mt-1 flex items-center gap-3 rounded-lg border border-dashed p-2.5">
                            <ArrowRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                            <span className="min-w-0 flex-1">
                                <span className="block truncate text-sm">
                                    {c.approval_number} · {c.reason || c.approval_type}
                                </span>
                                {c.due_date && (
                                    <span className="block text-xs text-muted-foreground">
                                        due {c.due_date.slice(0, 10)}
                                    </span>
                                )}
                            </span>
                            <Button
                                size="sm" variant="outline" className="h-8 shrink-0"
                                disabled={claim.isPending}
                                onClick={() =>
                                    claim.mutate(c.id, {
                                        onSuccess: () => toast.success("Claimed — moved to your approvals."),
                                        onError: () => toast.error("Could not claim (someone may have beaten you to it)."),
                                    })
                                }
                            >
                                Accept
                            </Button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

function GaugeNagTile() {
    const { data: gauges = [] } = useGaugeNag();
    return (
        <div className="flex flex-col justify-between rounded-xl border bg-card p-4">
            <div>
                <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    <Gauge className="h-3.5 w-3.5" /> Your gauges
                </div>
                {gauges.length === 0 ? (
                    <div className="mt-2 text-sm text-muted-foreground">
                        Nothing you've used recently is due for calibration.
                    </div>
                ) : (
                    <>
                        <div className="mt-2 text-sm">
                            <b>{gauges.length} gauge{gauges.length === 1 ? "" : "s"} you used recently</b>
                            {" "}need{gauges.length === 1 ? "s" : ""} calibration soon.
                        </div>
                        <div className="mt-1 space-y-0.5 text-xs text-muted-foreground">
                            {gauges.slice(0, 3).map((g) => (
                                <div key={g.equipment_id} className={g.overdue ? "text-destructive" : ""}>
                                    {g.equipment_name} — {g.overdue
                                        ? `overdue ${Math.abs(g.days_until_due)}d`
                                        : `due in ${g.days_until_due}d`}
                                </div>
                            ))}
                        </div>
                    </>
                )}
            </div>
            <Link to="/quality/calibrations" className="mt-3">
                <Button variant="outline" className="h-10 w-full">Review calibrations</Button>
            </Link>
        </div>
    );
}

// ---------------------------------------------------------------------------

/** Route wrapper (/quality/inbox) — Home renders QaHomePage directly for QA
 *  personas; this lets everyone else (leads, admins) reach the same surface. */
export function QaHomeRoute() {
    const { data: user } = useAuthUser();
    if (!user) return null;
    return <QaHomePage user={user} />;
}

export function QaHomePage({ user }: { user: AuthUser }) {
    return (
        <div className="mx-auto max-w-4xl space-y-3 p-4">
            <div className="flex items-center gap-3">
                <h1 className="min-w-0 flex-1 truncate text-2xl font-semibold tracking-tight">
                    Welcome back{user.first_name ? `, ${user.first_name}` : ""}
                </h1>
                <Link to="/production/incoming">
                    <Button variant="outline">
                        Incoming queue <ArrowRight className="ml-1 h-4 w-4" />
                    </Button>
                </Link>
            </div>
            <FpiBanner />
            <InboxList />
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                <MyActionsPanel user={user} />
                <GaugeNagTile />
            </div>
        </div>
    );
}

export default QaHomePage;
