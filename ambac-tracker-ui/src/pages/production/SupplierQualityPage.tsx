import { Link } from "@tanstack/react-router";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useRetrieveCompanies } from "@/hooks/useRetrieveCompanies";
import { useSupplierScorecard } from "@/hooks/useSupplierScorecard";
import { useSupplierQualificationStatus } from "@/hooks/useSupplierQualifications";

const pct = (v: number) => `${Math.round(v * 100)}%`;

function Metric({ label, value, tone }: { label: string; value: string; tone?: "good" | "bad" | "warn" }) {
    const color =
        tone === "bad" ? "text-destructive" : tone === "warn" ? "text-amber-600" : tone === "good" ? "text-green-600" : "";
    return (
        <div className="rounded-md border p-3">
            <div className="text-xs text-muted-foreground">{label}</div>
            <div className={`text-xl font-semibold tabular-nums ${color}`}>{value}</div>
        </div>
    );
}

function QualificationBadge({ supplierId }: { supplierId: string }) {
    const { data: q } = useSupplierQualificationStatus(supplierId);
    if (!q) return null;
    if (!q.qualified) {
        return <Badge variant="outline" className="text-muted-foreground">Not qualified</Badge>;
    }
    const tone = q.status === "CONDITIONAL" ? "secondary" : "default";
    const expiringSoon = q.days_to_expiry != null && q.days_to_expiry <= 30;
    return (
        <Badge variant={expiringSoon ? "secondary" : tone}>
            {q.status === "CONDITIONAL" ? "Conditional" : "Qualified"}
            {expiringSoon ? ` · ${q.days_to_expiry}d` : ""}
        </Badge>
    );
}

const RATING_STYLE: Record<string, string> = {
    A: "bg-green-600 text-white",
    B: "bg-amber-500 text-white",
    C: "bg-destructive text-destructive-foreground",
};

function RatingBadge({ rating, reason }: { rating: string | null; reason?: string }) {
    if (!rating) return null;
    return (
        <Badge className={RATING_STYLE[rating] ?? ""} title={reason}>
            Rating {rating}
        </Badge>
    );
}

// Recommend-only standing review from the scorecard (never auto-transitions —
// this is the human's cue to act via the qualification lifecycle).
const STANDING_STYLE: Record<string, { label: string; className: string }> = {
    REVIEW_SUSPEND: { label: "Review: suspend", className: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300" },
    REVIEW_CONDITIONAL: { label: "Review: conditional", className: "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300" },
    REVIEW_RESTORE: { label: "Review: restore", className: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300" },
};

function StandingBadge({ action, reason }: { action?: string; reason?: string }) {
    if (!action || action === "NONE") return null;
    const cfg = STANDING_STYLE[action];
    if (!cfg) return null;
    // Link to the ASL — that's where a QA manager confirms the review (grant / suspend / restore).
    return (
        <Link to="/production/supplier-qualifications">
            <Badge className={`cursor-pointer hover:opacity-80 ${cfg.className}`} title={reason}>
                {cfg.label}
            </Badge>
        </Link>
    );
}

function ScorecardCard({ id, name }: { id: string; name: string }) {
    const { data: sc, isLoading } = useSupplierScorecard(id);
    const scarLink = {
        to: "/quality/capas" as const,
        search: { supplier: id, capa_type: "SUPPLIER" } as never,
    };
    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center justify-between gap-2">
                    <span className="flex items-center gap-2">
                        {name}
                        {sc && <RatingBadge rating={sc.rating} reason={sc.rating_reason} />}
                        {sc && <StandingBadge action={sc.recommended_action} reason={sc.recommendation_reason} />}
                        <QualificationBadge supplierId={id} />
                    </span>
                    {sc && sc.open_scar_count > 0 && (
                        <Link {...scarLink}>
                            <Badge variant="destructive" className="cursor-pointer hover:opacity-80">
                                {sc.open_scar_count} open SCAR{sc.open_scar_count === 1 ? "" : "s"}
                            </Badge>
                        </Link>
                    )}
                </CardTitle>
            </CardHeader>
            <CardContent>
                {isLoading || !sc ? (
                    <p className="text-sm text-muted-foreground">Loading…</p>
                ) : sc.lots_received === 0 ? (
                    <p className="text-sm text-muted-foreground">No material lots received from this supplier yet.</p>
                ) : (
                    <>
                        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                            <Metric label="Lots received" value={String(sc.lots_received)} />
                            <Metric label="Accepted" value={String(sc.lots_accepted)} tone="good" />
                            <Metric label="Rejected" value={String(sc.lots_rejected)} tone={sc.lots_rejected > 0 ? "bad" : undefined} />
                            <Metric label="Reject rate" value={pct(sc.reject_rate)} tone={sc.reject_rate > 0 ? "warn" : "good"} />
                            <Metric label="CoC compliance" value={pct(sc.coc_compliance)} tone={sc.coc_compliance < 1 ? "warn" : "good"} />
                            <Metric
                                label="On-time delivery"
                                value={sc.on_time_rate === null ? "—" : pct(sc.on_time_rate)}
                                tone={sc.on_time_rate !== null && sc.on_time_rate < 0.9 ? "warn" : undefined}
                            />
                        </div>
                        <div className="mt-3 text-right">
                            <Link {...scarLink} className="text-sm text-primary hover:underline">
                                View SCARs →
                            </Link>
                        </div>
                    </>
                )}
            </CardContent>
        </Card>
    );
}

export function SupplierQualityPage() {
    const { data: companies, isLoading } = useRetrieveCompanies({ limit: 200 } as never);
    return (
        <div className="space-y-4 p-2">
            <div>
                <h1 className="text-2xl font-semibold tracking-tight">Supplier Quality</h1>
                <p className="text-sm text-muted-foreground">
                    Receiving-inspection scorecards: acceptance, reject rate, CoC compliance, on-time delivery, and open SCARs.
                </p>
            </div>
            {isLoading ? (
                <p className="text-sm text-muted-foreground">Loading suppliers…</p>
            ) : (
                <div className="grid gap-4 lg:grid-cols-2">
                    {(companies?.results ?? []).map((c) => (
                        <ScorecardCard key={c.id} id={String(c.id)} name={c.name} />
                    ))}
                </div>
            )}
        </div>
    );
}
