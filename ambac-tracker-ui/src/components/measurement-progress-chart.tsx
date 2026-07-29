import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { TrendingUp, AlertTriangle, CheckCircle2 } from "lucide-react";
import { useQualityReports, useMeasurementDefinitions } from "@/hooks/useQualityReports";

type StepHistoryEntry = {
    step_id: string;
    step_name: string;
    step_order: number;
    parts_at_step: number;
    parts_completed: number;
    parts_reached: number;
    status?: string;
};

type Props = {
    workOrder: any;
    stepHistory?: StepHistoryEntry[];
};

export function MeasurementProgressChart({ workOrder, stepHistory = [] }: Props) {
    const { data: qualityReports, isLoading: loadingReports } = useQualityReports({
        part__work_order: workOrder.id,
        limit: 500
    }, undefined, {
        enabled: !!workOrder.id
    });

    // Scope to definitions whose step belongs to this WO's process. The WO
    // itself carries `process`; `related_order_info` never exposed a
    // `process_id`, which is why this widget silently stayed empty for
    // every real work order before the filter was fixed.
    const processId = workOrder.process as string | undefined;
    const { data: measurementDefs, isLoading: loadingDefs } = useMeasurementDefinitions({
        limit: 100,
        step__process: processId,
    } as never, undefined, {
        enabled: !!processId,
    });

    if (loadingReports || loadingDefs) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <TrendingUp className="h-4 w-4" />
                        Measurement Progress
                    </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    {Array.from({ length: 3 }).map((_, i) => (
                        <div key={i} className="space-y-2">
                            <Skeleton className="h-4 w-32" />
                            <Skeleton className="h-2 w-full" />
                        </div>
                    ))}
                </CardContent>
            </Card>
        );
    }

    const reports = qualityReports?.results || [];
    const definitions = measurementDefs?.results || [];

    // Per-definition stats
    const defStats = definitions.map(def => {
        const measurements = reports.flatMap(report =>
            (report.measurements || []).filter((m: any) => m.definition === def.id)
        );
        const totalMeasurements = measurements.length;
        const passCount = measurements.filter((m: any) => {
            if (def.type === "PASS_FAIL") return m.value_pass_fail === "PASS";
            if (def.type === "NUMERIC") return m.is_within_spec === true;
            return false;
        }).length;
        const failCount = totalMeasurements - passCount;
        const passRate = totalMeasurements > 0 ? (passCount / totalMeasurements) * 100 : 0;

        // How many *distinct parts* have a capture for this def? That's the
        // meaningful numerator for "who still owes me a capture" — one part
        // can have several measurement rows if a step's been re-visited, but
        // for coverage we care about unique parts.
        const partsWithCapture = new Set(
            reports
                .filter(r => (r.measurements || []).some((m: any) => m.definition === def.id))
                .map(r => (r as any).part)
        ).size;

        return { def, totalMeasurements, passCount, failCount, passRate, partsWithCapture };
    });

    // Group defs by step id
    const defsByStep = new Map<string, typeof defStats>();
    for (const stat of defStats) {
        const stepId = (stat.def as any).step as string | null;
        if (!stepId) continue;
        if (!defsByStep.has(stepId)) defsByStep.set(stepId, []);
        defsByStep.get(stepId)!.push(stat);
    }

    // Step history keyed by id — gives us process order and A2 denominator
    // (parts that have reached this step: parts_at_step + parts_completed).
    const stepMeta = new Map<string, StepHistoryEntry>();
    for (const s of stepHistory) stepMeta.set(s.step_id, s);

    // Build ordered step groups. Steps with defs but no history entry
    // (shouldn't happen in practice, but be defensive) land at the bottom.
    const orderedGroups = Array.from(defsByStep.entries())
        .map(([stepId, stats]) => {
            const meta = stepMeta.get(stepId);
            const partsReached = meta?.parts_reached ?? 0;
            const stepName = meta?.step_name || (stats[0]?.def as any)?.step_name || "Unknown step";
            const stepOrder = meta?.step_order ?? 9999;
            return { stepId, stepName, stepOrder, partsReached, stats };
        })
        .sort((a, b) => a.stepOrder - b.stepOrder);

    const overallPass = defStats.reduce((s, x) => s + x.passCount, 0);
    const overallFail = defStats.reduce((s, x) => s + x.failCount, 0);
    const overallTotal = overallPass + overallFail;
    const overallPassRate = overallTotal > 0 ? (overallPass / overallTotal) * 100 : 0;

    if (definitions.length === 0) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <TrendingUp className="h-4 w-4" />
                        Measurement Progress
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="text-center py-4 text-sm text-muted-foreground">
                        No measurement definitions found for this process.
                    </div>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card>
            <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-lg">
                    <TrendingUp className="h-4 w-4" />
                    Measurement Progress
                </CardTitle>
                <div className="flex items-center gap-4 text-sm">
                    <div className="flex items-center gap-1">
                        <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                        <span>{overallPass} Pass</span>
                    </div>
                    <div className="flex items-center gap-1">
                        <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                        <span>{overallFail} Fail</span>
                    </div>
                    <Badge variant={overallPassRate >= 95 ? "default" : overallPassRate >= 80 ? "secondary" : "destructive"}>
                        {overallPassRate.toFixed(1)}% Pass Rate
                    </Badge>
                </div>
            </CardHeader>
            <CardContent className="space-y-4">
                {orderedGroups.map(group => (
                    <div key={group.stepId} className="space-y-2 rounded-lg border p-3">
                        <div className="flex items-center justify-between">
                            <p className="font-medium text-sm">{group.stepName}</p>
                            <span className="text-xs text-muted-foreground">
                                {group.stats.length} {group.stats.length === 1 ? "check" : "checks"}
                                {" · "}
                                {group.partsReached} {group.partsReached === 1 ? "part reached" : "parts reached"}
                            </span>
                        </div>
                        <div className="space-y-2 pl-1">
                            {group.stats.map(stat => {
                                const denom = group.partsReached;
                                const numer = stat.partsWithCapture;
                                const coverage = denom > 0 ? (numer / denom) * 100 : 0;
                                return (
                                    <div key={stat.def.id} className="space-y-1">
                                        <div className="flex items-center justify-between text-xs">
                                            <div className="flex items-center gap-2 min-w-0">
                                                <span className="font-medium truncate">{stat.def.label}</span>
                                                {stat.def.unit && (
                                                    <span className="text-muted-foreground">({stat.def.unit})</span>
                                                )}
                                            </div>
                                            <div className="flex items-center gap-2 shrink-0">
                                                <span className="text-muted-foreground">
                                                    {numer}/{denom} captured
                                                </span>
                                                {stat.totalMeasurements > 0 && (
                                                    stat.passRate >= 95 ? (
                                                        <CheckCircle2 className="h-3.5 w-3.5 text-green-600" />
                                                    ) : stat.passRate < 80 ? (
                                                        <AlertTriangle className="h-3.5 w-3.5 text-red-600" />
                                                    ) : null
                                                )}
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <Progress value={coverage} className="h-1.5 flex-1" />
                                            <span className="text-[10px] text-muted-foreground min-w-[70px] text-right">
                                                {stat.totalMeasurements > 0
                                                    ? `${stat.passRate.toFixed(0)}% pass`
                                                    : "no data"}
                                            </span>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                ))}

                {overallTotal === 0 && (
                    <div className="text-center py-4 text-sm text-muted-foreground">
                        No measurements recorded yet for this work order.
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
