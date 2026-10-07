import { useState, useMemo } from "react";
import { Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { Package, Clock, CheckCircle2, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
    KpiCard,
    KpiGrid,
    ChartCard,
    DateRangeToggle,
    DonutChart,
    TrendLineChart,
    AgingBucketChart,
    AnalyticsTable,
    StatusBadge,
    rangeToDays,
    type DateRange,
    type AnalyticsColumnDef,
} from "@/components/analytics";

// Hooks
import { useNcrTrend } from "@/hooks/useNcrTrend";
import { useDispositionBreakdown } from "@/hooks/useDispositionBreakdown";
import { useNcrAging } from "@/hooks/useNcrAging";
import { useOpenDispositions } from "@/hooks/useDashboardData";

// Types for the table
type DispositionRow = {
    id: string;
    part: string;
    part_id: string | null;
    disposition: string;
    reason: string;
    assignee: string;
    created: string;
    status: string;
};

type UndecidedRow = { id: string; report: string; item: string; description: string; created: string };

// Failed reports nobody has decided on — raise a CAPA, or record why not
// (services/qms/capa_decision). The decision itself lives on the report's page.
const undecidedColumns: AnalyticsColumnDef<UndecidedRow>[] = [
    { key: "report", header: "Report", accessor: (r) => <span className="font-mono text-xs text-primary">{r.report}</span>,
      sortable: true, sortValue: (r) => r.report },
    { key: "item", header: "Part / lot", accessor: (r) => r.item },
    { key: "description", header: "Finding",
      accessor: (r) => <span className="truncate max-w-[260px] block" title={r.description}>{r.description}</span> },
    { key: "created", header: "Reported", accessor: (r) => r.created, sortable: true, sortValue: (r) => r.created },
];

export function NcrAnalysisPage() {
    const [range, setRange] = useState<DateRange>("30d");

    // API Hooks
    const { data: ncrTrendData, isLoading: isLoadingTrend } = useNcrTrend({ days: rangeToDays(range) });
    const { data: dispositionData, isLoading: isLoadingDisposition } = useDispositionBreakdown({ days: rangeToDays(range) });
    const { data: agingData, isLoading: isLoadingAging } = useNcrAging();
    const { data: dispositionsResponse, isLoading: isLoadingTable } = useOpenDispositions(20);
    const { data: undecided, isLoading: isLoadingUndecided } = useQuery({
        queryKey: ["ncr-awaiting-decision"],
        queryFn: () => api.api_QualityReports_list({ queries: {
            status: "FAIL", capa_decision__isnull: true, ordering: "created_at", limit: 50 } }),
    });
    const undecidedRows: UndecidedRow[] = useMemo(() => (undecided?.results ?? []).map((q) => ({
        id: String(q.id),
        report: q.report_number || "—",
        item: q.part_display || "—",
        description: q.description || "",
        created: q.created_at ? new Date(q.created_at).toLocaleDateString() : "",
    })), [undecided]);

    // Transform NCR trend data for chart
    const ncrChartData = useMemo(() => {
        if (!ncrTrendData?.data) return [];
        return ncrTrendData.data.map(d => ({
            date: d.date,
            created: d.created,
            closed: d.closed,
        }));
    }, [ncrTrendData]);

    // Transform disposition breakdown for donut chart
    const donutData = useMemo(() => {
        if (!dispositionData?.data) return [];
        return dispositionData.data.map(d => ({
            name: d.type,
            value: d.count,
        }));
    }, [dispositionData]);

    // KPI values
    const totalCreated = ncrTrendData?.summary?.total_created ?? 0;
    const totalClosed = ncrTrendData?.summary?.total_closed ?? 0;
    const closureRate = totalCreated > 0 ? Math.round((totalClosed / totalCreated) * 100) : 0;
    const avgAge = agingData?.avg_age_days ?? 0;
    const overdueCount = agingData?.overdue_count ?? 0;

    // Table columns
    const columns: AnalyticsColumnDef<DispositionRow>[] = [
        {
            key: "part",
            header: "Part",
            accessor: (row) => (
                <span className="font-mono text-xs text-primary">{row.part}</span>
            ),
            sortable: true,
            sortValue: (row) => row.part,
        },
        {
            key: "disposition",
            header: "Disposition",
            accessor: (row) => <StatusBadge status={row.disposition} />,
        },
        {
            key: "reason",
            header: "Reason",
            accessor: (row) => (
                <span className="truncate max-w-[200px] block" title={row.reason}>
                    {row.reason}
                </span>
            ),
        },
        {
            key: "assignee",
            header: "Assignee",
            accessor: (row) => row.assignee,
        },
        {
            key: "created",
            header: "Created",
            accessor: (row) => (
                <span className="text-muted-foreground">{row.created}</span>
            ),
        },
        {
            key: "status",
            header: "Status",
            accessor: (row) => <StatusBadge status={row.status} />,
        },
    ];

    const tableData: DispositionRow[] = (dispositionsResponse?.data ?? []).map(d => ({
        id: d.id,
        part: d.part,
        part_id: d.part_id,
        disposition: d.disposition,
        reason: d.reason,
        assignee: d.assignee,
        created: d.created,
        status: d.status,
    }));

    return (
        <div className="container mx-auto p-5 space-y-5">
            {/* Header */}
            <div className="flex flex-col gap-4">
                <div className="flex items-center gap-4">
                    <Button variant="ghost" size="sm" asChild>
                        <Link to="/analysis">
                            <ArrowLeft className="h-4 w-4 mr-2" />
                            Back to Dashboard
                        </Link>
                    </Button>
                </div>
                <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
                    <div>
                        <h1 className="text-2xl font-semibold tracking-tight">NCR & Disposition Analysis</h1>
                        <p className="text-sm text-muted-foreground">
                            Non-conformance reports, aging analysis, and disposition tracking.
                        </p>
                    </div>
                    <DateRangeToggle value={range} onChange={setRange} />
                </div>
            </div>

            {/* KPI Cards */}
            <KpiGrid columns={4}>
                <KpiCard
                    title="Total NCRs"
                    value={totalCreated}
                    subtitle={`Created in ${rangeToDays(range)}d`}
                    icon={Package}
                    isLoading={isLoadingTrend}
                />
                <KpiCard
                    title="Open NCRs"
                    value={totalCreated - totalClosed}
                    subtitle="Currently unresolved"
                    icon={Clock}
                    variant={totalCreated - totalClosed > 10 ? "warning" : "default"}
                    isLoading={isLoadingTrend}
                />
                <KpiCard
                    title="Avg Age"
                    value={avgAge}
                    subtitle="Days open"
                    icon={Clock}
                    variant={avgAge > 7 ? "warning" : "default"}
                    isLoading={isLoadingAging}
                    formatValue={(v) => `${v} days`}
                />
                <KpiCard
                    title="Closure Rate"
                    value={closureRate}
                    subtitle={`${totalClosed} closed`}
                    icon={CheckCircle2}
                    isLoading={isLoadingTrend}
                    formatValue={(v) => `${v}%`}
                />
            </KpiGrid>

            {/* Charts Row */}
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                {/* NCR Trend */}
                <ChartCard
                    title="NCR Trend"
                    description="NCRs created vs closed over time"
                    isLoading={isLoadingTrend}
                >
                    <TrendLineChart
                        data={ncrChartData}
                        series={[
                            { dataKey: "created", label: "Created", color: "var(--chart-1)", type: "line" },
                            { dataKey: "closed", label: "Closed", color: "var(--chart-2)", type: "line" },
                        ]}
                        height={220}
                    />
                </ChartCard>

                {/* Disposition Breakdown */}
                <ChartCard
                    title="Disposition Breakdown"
                    description="Distribution by disposition type"
                    isLoading={isLoadingDisposition}
                >
                    <DonutChart
                        data={donutData}
                        centerValue={dispositionData?.total ?? 0}
                        centerLabel="Total"
                        height={220}
                    />
                </ChartCard>
            </div>

            {/* Second Charts Row */}
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                {/* Aging Buckets */}
                <ChartCard
                    title="NCR Aging"
                    description={`${overdueCount} NCRs overdue (>7 days)`}
                    isLoading={isLoadingAging}
                >
                    <AgingBucketChart
                        data={agingData?.data ?? []}
                        height={180}
                        defaultColor="var(--chart-3)"
                    />
                </ChartCard>

                {/* Quick Stats */}
                <ChartCard
                    title="Summary Statistics"
                    description={`${rangeToDays(range)}-day period`}
                >
                    <div className="grid grid-cols-2 gap-4 p-4">
                        <div className="p-4 bg-muted/30 rounded-lg">
                            <p className="text-2xl font-bold">{totalCreated}</p>
                            <p className="text-xs text-muted-foreground">NCRs Created</p>
                        </div>
                        <div className="p-4 bg-muted/30 rounded-lg">
                            <p className="text-2xl font-bold">{totalClosed}</p>
                            <p className="text-xs text-muted-foreground">NCRs Closed</p>
                        </div>
                        <div className="p-4 bg-muted/30 rounded-lg">
                            <p className="text-2xl font-bold">{ncrTrendData?.summary?.net_change ?? 0}</p>
                            <p className="text-xs text-muted-foreground">Net Change</p>
                        </div>
                        <div className="p-4 bg-muted/30 rounded-lg">
                            <p className="text-2xl font-bold text-amber-600">{overdueCount}</p>
                            <p className="text-xs text-muted-foreground">Overdue (&gt;7 days)</p>
                        </div>
                    </div>
                </ChartCard>
            </div>

            {/* Failed reports with no CAPA decision yet (ISO 9001 10.2.1: evaluate the need for action) */}
            <ChartCard
                title={`Awaiting a CAPA decision${undecided?.count ? ` (${undecided.count})` : ""}`}
                description="Failed reports nobody has decided on yet: raise a CAPA, or record why one isn't needed"
                isLoading={isLoadingUndecided}
            >
                <AnalyticsTable
                    data={undecidedRows}
                    columns={undecidedColumns}
                    rowLink={(row) => `/details/QualityReports/${row.id}`}
                    maxRows={10}
                    emptyMessage="Every failed report has a CAPA decision"
                    compact
                />
            </ChartCard>

            {/* Open Dispositions Table */}
            <ChartCard
                title="Open Dispositions"
                description="Non-conforming parts awaiting or undergoing disposition"
                isLoading={isLoadingTable}
                controls={
                    <Button variant="outline" size="sm" asChild>
                        <Link to="/production/dispositions">View All</Link>
                    </Button>
                }
            >
                <AnalyticsTable
                    data={tableData}
                    columns={columns}
                    rowLink={(row) => row.part_id ? `/editors/parts/${row.part_id}` : "/production/dispositions"}
                    maxRows={10}
                    showViewAll
                    viewAllLink="/production/dispositions"
                    emptyMessage="No open dispositions"
                    compact
                />
            </ChartCard>
        </div>
    );
}

export default NcrAnalysisPage;
