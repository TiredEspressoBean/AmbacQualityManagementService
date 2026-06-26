import { Link } from "@tanstack/react-router";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useRetrieveCompanies } from "@/hooks/useRetrieveCompanies";
import { useSupplierScorecard } from "@/hooks/useSupplierScorecard";

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

function ScorecardCard({ id, name }: { id: string; name: string }) {
    const { data: sc, isLoading } = useSupplierScorecard(id);
    const scarLink = {
        to: "/quality/capas" as const,
        search: { supplier: id, capa_type: "SUPPLIER" } as never,
    };
    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center justify-between">
                    <span>{name}</span>
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
