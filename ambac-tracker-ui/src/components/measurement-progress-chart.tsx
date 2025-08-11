import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { TrendingUp, TrendingDown, AlertTriangle, CheckCircle2 } from "lucide-react";
import { useQualityReports, useMeasurementDefinitions } from "@/hooks/useQualityReports";

type Props = {
    workOrder: any;
    parts: any[];
};

export function MeasurementProgressChart({ workOrder, parts }: Props) {
    // Since part__work_order filtering isn't available in the API,
    // we fetch all quality reports and filter client-side for now
    // TODO: Add proper filtering to QualityReportViewSet in backend
    const { data: qualityReports, isLoading: loadingReports } = useQualityReports({
        queries: {
            limit: 1000 // Get more reports to ensure we capture work order data
        }
    });

    // Get measurement definitions for the work order's process steps
    const { data: measurementDefs, isLoading: loadingDefs } = useMeasurementDefinitions({
        queries: {
            step__process: workOrder.related_order_info?.process_id,
            limit: 100
        }
    }, {
        enabled: !!workOrder.related_order_info?.process_id
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
                            <div className="flex gap-2">
                                <Skeleton className="h-4 w-12" />
                                <Skeleton className="h-4 w-16" />
                            </div>
                        </div>
                    ))}
                </CardContent>
            </Card>
        );
    }

    // Filter quality reports to only include parts from this work order
    const allReports = qualityReports?.results || [];
    const partIds = parts.map(part => part.id);
    const reports = allReports.filter(report => 
        report.part && partIds.includes(report.part)
    );
    
    const definitions = measurementDefs?.results || [];

    // Process measurement data for visualization
    const measurementStats = definitions.map(def => {
        const relatedReports = reports.filter(report => 
            report.measurements?.some((m: any) => m.definition === def.id)
        );

        const measurements = relatedReports.flatMap(report => 
            report.measurements?.filter((m: any) => m.definition === def.id) || []
        );

        const totalMeasurements = measurements.length;
        const passCount = measurements.filter((m: any) => {
            if (def.type === "PASS_FAIL") {
                return m.value_pass_fail === "PASS";
            } else if (def.type === "NUMERIC") {
                // Check if measurement is within tolerance
                return m.is_within_spec === true;
            }
            return false;
        }).length;

        const failCount = totalMeasurements - passCount;
        const passRate = totalMeasurements > 0 ? (passCount / totalMeasurements) * 100 : 0;

        // Calculate trend (simplified - comparing recent vs older measurements)
        const recentMeasurements = measurements.slice(-Math.ceil(measurements.length / 2));
        const olderMeasurements = measurements.slice(0, Math.floor(measurements.length / 2));
        
        const recentPassRate = recentMeasurements.length > 0 
            ? (recentMeasurements.filter((m: any) => 
                def.type === "PASS_FAIL" ? m.value_pass_fail === "PASS" : m.is_within_spec === true
            ).length / recentMeasurements.length) * 100 
            : 0;

        const olderPassRate = olderMeasurements.length > 0
            ? (olderMeasurements.filter((m: any) => 
                def.type === "PASS_FAIL" ? m.value_pass_fail === "PASS" : m.is_within_spec === true
            ).length / olderMeasurements.length) * 100
            : 0;

        const trend = recentPassRate - olderPassRate;

        return {
            definition: def,
            totalMeasurements,
            passCount,
            failCount,
            passRate,
            trend,
            measurements: measurements.slice(-10) // Keep last 10 for detail view
        };
    });

    const overallStats = {
        totalMeasurements: measurementStats.reduce((sum, stat) => sum + stat.totalMeasurements, 0),
        totalPass: measurementStats.reduce((sum, stat) => sum + stat.passCount, 0),
        totalFail: measurementStats.reduce((sum, stat) => sum + stat.failCount, 0)
    };

    const overallPassRate = overallStats.totalMeasurements > 0 
        ? (overallStats.totalPass / overallStats.totalMeasurements) * 100 
        : 0;

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
                        <span>{overallStats.totalPass} Pass</span>
                    </div>
                    <div className="flex items-center gap-1">
                        <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                        <span>{overallStats.totalFail} Fail</span>
                    </div>
                    <Badge variant={overallPassRate >= 95 ? "default" : overallPassRate >= 80 ? "secondary" : "destructive"}>
                        {overallPassRate.toFixed(1)}% Pass Rate
                    </Badge>
                </div>
            </CardHeader>
            <CardContent className="space-y-4">
                {/* Overall Progress */}
                <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                        <span className="font-medium">Overall Quality</span>
                        <span>{overallStats.totalMeasurements} measurements</span>
                    </div>
                    <Progress 
                        value={overallPassRate} 
                        className="h-3"
                    />
                </div>

                {/* Individual Measurement Progress */}
                <div className="space-y-3 max-h-64 overflow-y-auto">
                    {measurementStats.map((stat, index) => (
                        <div key={stat.definition.id} className="space-y-2 p-3 bg-muted/30 rounded-lg">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <span className="font-medium text-sm">
                                        {stat.definition.label}
                                    </span>
                                    {stat.definition.unit && (
                                        <span className="text-xs text-muted-foreground">
                                            ({stat.definition.unit})
                                        </span>
                                    )}
                                    {/* Trend indicator */}
                                    {Math.abs(stat.trend) > 5 && (
                                        <div className="flex items-center gap-1">
                                            {stat.trend > 0 ? (
                                                <TrendingUp className="h-3 w-3 text-green-600" />
                                            ) : (
                                                <TrendingDown className="h-3 w-3 text-red-600" />
                                            )}
                                            <span className="text-xs text-muted-foreground">
                                                {stat.trend > 0 ? '+' : ''}{stat.trend.toFixed(1)}%
                                            </span>
                                        </div>
                                    )}
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="text-xs text-muted-foreground">
                                        {stat.passCount}/{stat.totalMeasurements}
                                    </span>
                                    {stat.passRate >= 95 ? (
                                        <CheckCircle2 className="h-4 w-4 text-green-600" />
                                    ) : stat.passRate < 80 ? (
                                        <AlertTriangle className="h-4 w-4 text-red-600" />
                                    ) : null}
                                </div>
                            </div>
                            
                            <div className="flex items-center gap-2">
                                <Progress 
                                    value={stat.passRate} 
                                    className="h-2 flex-1"
                                />
                                <span className="text-xs font-medium min-w-[45px]">
                                    {stat.passRate.toFixed(0)}%
                                </span>
                            </div>

                            {stat.definition.type === "NUMERIC" && (
                                <div className="text-xs text-muted-foreground">
                                    Target: {stat.definition.nominal || '—'}
                                    {stat.definition.lower_tol && stat.definition.upper_tol && (
                                        <span> (±{stat.definition.upper_tol})</span>
                                    )}
                                </div>
                            )}
                        </div>
                    ))}
                </div>

                {overallStats.totalMeasurements === 0 && (
                    <div className="text-center py-4 text-sm text-muted-foreground">
                        No measurements recorded yet for this work order.
                    </div>
                )}
            </CardContent>
        </Card>
    );
}