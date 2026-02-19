import { useState, useCallback } from "react";
import { Link } from "@tanstack/react-router";
import {
    Area,
    AreaChart,
    CartesianGrid,
    XAxis,
    YAxis,
    ReferenceLine,
} from "recharts";
import {
    ArrowLeft,
    X,
    Download,
    Plus,
    ExternalLink,
    Filter,
    TrendingUp,
    TrendingDown,
    Minus,
    AlertTriangle,
    BarChart3,
    Hash,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { DateRangeToggle, rangeToDays, type DateRange } from "@/components/analytics";
import { cn } from "@/lib/utils";

// Hooks
import { useDefectPareto } from "@/hooks/useDefectPareto";
import { useDefectsByProcess } from "@/hooks/useDefectsByProcess";
import { useDefectRecords } from "@/hooks/useDefectRecords";
import { useFilterOptions } from "@/hooks/useFilterOptions";
import { useDefectTrend } from "@/hooks/useDefectTrend";
import { useQualityRates } from "@/hooks/useQualityRates";

// Filter state type
type Filters = {
    defect_type: string | null;
    process: string | null;
    part_type: string | null;
};

// Clickable breakdown bar component
function BreakdownBar({
    label,
    count,
    maxCount,
    isActive,
    onClick,
}: {
    label: string;
    count: number;
    maxCount: number;
    isActive: boolean;
    onClick: () => void;
}) {
    const percentage = maxCount > 0 ? (count / maxCount) * 100 : 0;

    return (
        <button
            onClick={onClick}
            className={cn(
                "w-full text-left p-2 rounded-md transition-colors",
                "hover:bg-muted/50",
                isActive && "bg-primary/10 ring-1 ring-primary/30"
            )}
        >
            <div className="flex justify-between items-center mb-1">
                <span className={cn(
                    "text-sm truncate",
                    isActive ? "font-medium text-primary" : "text-muted-foreground"
                )}>
                    {label}
                </span>
                <span className="text-sm font-mono font-medium ml-2">{count}</span>
            </div>
            <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                <div
                    className={cn(
                        "h-full rounded-full transition-all",
                        isActive ? "bg-primary" : "bg-chart-1"
                    )}
                    style={{ width: `${percentage}%` }}
                />
            </div>
        </button>
    );
}

export function DefectAnalysisPage() {
    const [range, setRange] = useState<DateRange>("30d");
    const [filters, setFilters] = useState<Filters>({
        defect_type: null,
        process: null,
        part_type: null,
    });
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

    const days = rangeToDays(range);
    const hasActiveFilters = filters.defect_type || filters.process || filters.part_type;
    const activeFilterCount = [filters.defect_type, filters.process, filters.part_type].filter(Boolean).length;

    // API Hooks
    const { data: paretoResponse, isLoading: isLoadingPareto } = useDefectPareto({ days, limit: 8 });
    const { data: processData, isLoading: isLoadingProcess } = useDefectsByProcess({ days });
    const { data: filterOptions } = useFilterOptions({ days });
    const { data: recordsResponse, isLoading: isLoadingRecords } = useDefectRecords({
        days,
        defect_type: filters.defect_type,
        process: filters.process,
        part_type: filters.part_type,
        limit: 100,
    });
    const { data: trendData, isLoading: isLoadingTrend } = useDefectTrend({ days });
    const { data: qualityRates } = useQualityRates({ days });

    // Transform data
    const defectTypes = paretoResponse?.data ?? [];
    const processes = processData?.data ?? [];
    const records = recordsResponse?.data ?? [];
    const totalRecords = recordsResponse?.total ?? 0;
    const trendPoints = trendData?.data ?? [];
    const trendSummary = trendData?.summary;

    const maxDefectCount = defectTypes[0]?.count ?? 1;
    const maxProcessCount = processes[0]?.count ?? 1;

    // Calculate defect rate (defects per 100 inspections)
    const defectRate = qualityRates?.total_inspected
        ? ((qualityRates.total_failed / qualityRates.total_inspected) * 100).toFixed(1)
        : "0.0";

    // Top defect type
    const topDefectType = defectTypes[0]?.errorType ?? "N/A";

    // Chart config
    const chartConfig = {
        count: { label: "Defects", color: "var(--chart-2)" },
    } as const;

    // Filter handlers
    const toggleFilter = useCallback((key: keyof Filters, value: string) => {
        setFilters(prev => ({
            ...prev,
            [key]: prev[key] === value ? null : value
        }));
        setSelectedIds(new Set());
    }, []);

    const clearAllFilters = useCallback(() => {
        setFilters({ defect_type: null, process: null, part_type: null });
        setSelectedIds(new Set());
    }, []);

    // Selection handlers
    const toggleSelection = useCallback((id: string) => {
        setSelectedIds(prev => {
            const next = new Set(prev);
            if (next.has(id)) {
                next.delete(id);
            } else {
                next.add(id);
            }
            return next;
        });
    }, []);

    const toggleSelectAll = useCallback(() => {
        if (selectedIds.size === records.length) {
            setSelectedIds(new Set());
        } else {
            setSelectedIds(new Set(records.map(r => r.id)));
        }
    }, [records, selectedIds.size]);

    // CSV Export
    const exportToCsv = useCallback(() => {
        const dataToExport = selectedIds.size > 0
            ? records.filter(r => selectedIds.has(r.id))
            : records;

        const headers = ["Part", "Part Type", "Process", "Defect Types", "Date", "Inspector", "Order", "Disposition"];
        const rows = dataToExport.map(r => [
            r.part_erp_id,
            r.part_type,
            r.step,
            r.error_types.join("; "),
            r.date,
            r.inspector,
            r.order,
            r.disposition_type || "Pending",
        ]);

        const csv = [headers, ...rows].map(row => row.map(cell => `"${cell}"`).join(",")).join("\n");
        const blob = new Blob([csv], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `defects-${new Date().toISOString().split("T")[0]}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    }, [records, selectedIds]);

    return (
        <div className="container mx-auto p-5 space-y-4">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div className="flex items-center gap-4">
                    <Button variant="ghost" size="sm" asChild>
                        <Link to="/analysis">
                            <ArrowLeft className="h-4 w-4 mr-2" />
                            Dashboard
                        </Link>
                    </Button>
                    <div>
                        <h1 className="text-xl font-semibold">Defect Records</h1>
                        <p className="text-sm text-muted-foreground">
                            {totalRecords} defects in {days} days
                            {hasActiveFilters && " (filtered)"}
                        </p>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <DateRangeToggle value={range} onChange={setRange} />
                </div>
            </div>

            {/* KPIs Row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <Card className="border-muted/40">
                    <CardContent className="p-4">
                        <div className="flex items-center gap-2">
                            <Hash className="h-4 w-4 text-muted-foreground" />
                            <span className="text-xs font-medium text-muted-foreground uppercase">Total Defects</span>
                        </div>
                        <p className="text-2xl font-bold mt-1">{trendSummary?.total ?? totalRecords}</p>
                        <p className="text-xs text-muted-foreground">in {days} days</p>
                    </CardContent>
                </Card>
                <Card className="border-muted/40">
                    <CardContent className="p-4">
                        <div className="flex items-center gap-2">
                            <BarChart3 className="h-4 w-4 text-muted-foreground" />
                            <span className="text-xs font-medium text-muted-foreground uppercase">Defect Rate</span>
                        </div>
                        <p className="text-2xl font-bold mt-1">{defectRate}%</p>
                        <p className="text-xs text-muted-foreground">of inspections</p>
                    </CardContent>
                </Card>
                <Card className="border-muted/40">
                    <CardContent className="p-4">
                        <div className="flex items-center gap-2">
                            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
                            <span className="text-xs font-medium text-muted-foreground uppercase">Top Type</span>
                        </div>
                        <p className="text-lg font-bold mt-1 truncate" title={topDefectType}>{topDefectType}</p>
                        <p className="text-xs text-muted-foreground">{defectTypes[0]?.count ?? 0} occurrences</p>
                    </CardContent>
                </Card>
                <Card className="border-muted/40">
                    <CardContent className="p-4">
                        <div className="flex items-center gap-2">
                            {trendSummary?.trend_direction === "up" ? (
                                <TrendingUp className="h-4 w-4 text-red-500" />
                            ) : trendSummary?.trend_direction === "down" ? (
                                <TrendingDown className="h-4 w-4 text-green-500" />
                            ) : (
                                <Minus className="h-4 w-4 text-muted-foreground" />
                            )}
                            <span className="text-xs font-medium text-muted-foreground uppercase">Trend</span>
                        </div>
                        <p className="text-2xl font-bold mt-1">
                            {trendSummary?.daily_avg ?? 0}
                            <span className="text-sm font-normal text-muted-foreground">/day</span>
                        </p>
                        <p className={cn(
                            "text-xs",
                            trendSummary?.trend_direction === "up" ? "text-red-500" :
                            trendSummary?.trend_direction === "down" ? "text-green-500" :
                            "text-muted-foreground"
                        )}>
                            {trendSummary?.trend_change > 0 ? "+" : ""}{trendSummary?.trend_change ?? 0}% vs prior period
                        </p>
                    </CardContent>
                </Card>
            </div>

            {/* Defect Trend Chart */}
            <Card className="border-muted/40">
                <CardHeader className="py-3 px-4">
                    <CardTitle className="text-sm font-medium">Defect Trend</CardTitle>
                </CardHeader>
                <CardContent className="px-2 pb-3">
                    {isLoadingTrend ? (
                        <div className="h-[160px] flex items-center justify-center text-muted-foreground text-sm">
                            Loading...
                        </div>
                    ) : trendPoints.length === 0 ? (
                        <div className="h-[160px] flex items-center justify-center text-muted-foreground text-sm">
                            No data
                        </div>
                    ) : (
                        <ChartContainer className="h-[160px] w-full" config={chartConfig}>
                            <AreaChart data={trendPoints} margin={{ left: 0, right: 0, top: 8, bottom: 0 }}>
                                <defs>
                                    <linearGradient id="defectGradient" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="var(--chart-2)" stopOpacity={0.3} />
                                        <stop offset="95%" stopColor="var(--chart-2)" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                <XAxis
                                    dataKey="label"
                                    tickLine={false}
                                    axisLine={false}
                                    tick={{ fontSize: 10 }}
                                    interval="preserveStartEnd"
                                />
                                <YAxis
                                    width={30}
                                    tickLine={false}
                                    axisLine={false}
                                    tick={{ fontSize: 10 }}
                                    allowDecimals={false}
                                />
                                <ChartTooltip
                                    content={<ChartTooltipContent formatter={(value) => `${value} defects`} />}
                                />
                                {trendSummary?.daily_avg && (
                                    <ReferenceLine
                                        y={trendSummary.daily_avg}
                                        stroke="var(--chart-4)"
                                        strokeDasharray="3 3"
                                        strokeOpacity={0.7}
                                    />
                                )}
                                <Area
                                    dataKey="count"
                                    type="monotone"
                                    stroke="var(--chart-2)"
                                    fill="url(#defectGradient)"
                                    strokeWidth={2}
                                />
                            </AreaChart>
                        </ChartContainer>
                    )}
                </CardContent>
            </Card>

            {/* Active Filters Bar */}
            {hasActiveFilters && (
                <div className="flex flex-wrap items-center gap-2 p-2 bg-muted/30 rounded-lg">
                    <Filter className="h-4 w-4 text-muted-foreground" />
                    {filters.defect_type && (
                        <Badge variant="secondary" className="gap-1">
                            {filters.defect_type}
                            <X
                                className="h-3 w-3 cursor-pointer"
                                onClick={() => toggleFilter("defect_type", filters.defect_type!)}
                            />
                        </Badge>
                    )}
                    {filters.process && (
                        <Badge variant="secondary" className="gap-1">
                            {filters.process}
                            <X
                                className="h-3 w-3 cursor-pointer"
                                onClick={() => toggleFilter("process", filters.process!)}
                            />
                        </Badge>
                    )}
                    {filters.part_type && (
                        <Badge variant="secondary" className="gap-1">
                            {filters.part_type}
                            <X
                                className="h-3 w-3 cursor-pointer"
                                onClick={() => toggleFilter("part_type", filters.part_type!)}
                            />
                        </Badge>
                    )}
                    <Button variant="ghost" size="sm" onClick={clearAllFilters} className="h-6 text-xs">
                        Clear all
                    </Button>
                </div>
            )}

            {/* Two Panel Layout */}
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
                {/* Left Panel - Breakdowns */}
                <div className="lg:col-span-1 space-y-4">
                    {/* By Defect Type */}
                    <Card>
                        <CardHeader className="py-3 px-4">
                            <CardTitle className="text-sm font-medium">By Defect Type</CardTitle>
                        </CardHeader>
                        <CardContent className="px-2 pb-2 space-y-1">
                            {isLoadingPareto ? (
                                <div className="text-sm text-muted-foreground p-2">Loading...</div>
                            ) : defectTypes.length === 0 ? (
                                <div className="text-sm text-muted-foreground p-2">No defects</div>
                            ) : (
                                defectTypes.map((d) => (
                                    <BreakdownBar
                                        key={d.errorType}
                                        label={d.errorType}
                                        count={d.count}
                                        maxCount={maxDefectCount}
                                        isActive={filters.defect_type === d.errorType}
                                        onClick={() => toggleFilter("defect_type", d.errorType)}
                                    />
                                ))
                            )}
                        </CardContent>
                    </Card>

                    {/* By Process */}
                    <Card>
                        <CardHeader className="py-3 px-4">
                            <CardTitle className="text-sm font-medium">By Process</CardTitle>
                        </CardHeader>
                        <CardContent className="px-2 pb-2 space-y-1">
                            {isLoadingProcess ? (
                                <div className="text-sm text-muted-foreground p-2">Loading...</div>
                            ) : processes.length === 0 ? (
                                <div className="text-sm text-muted-foreground p-2">No data</div>
                            ) : (
                                processes.slice(0, 8).map((p) => (
                                    <BreakdownBar
                                        key={p.process_name}
                                        label={p.process_name}
                                        count={p.count}
                                        maxCount={maxProcessCount}
                                        isActive={filters.process === p.process_name}
                                        onClick={() => toggleFilter("process", p.process_name)}
                                    />
                                ))
                            )}
                        </CardContent>
                    </Card>

                    {/* Part Type Filter */}
                    <Card>
                        <CardHeader className="py-3 px-4">
                            <CardTitle className="text-sm font-medium">By Part Type</CardTitle>
                        </CardHeader>
                        <CardContent className="px-3 pb-3">
                            <Select
                                value={filters.part_type ?? ""}
                                onValueChange={(v) => toggleFilter("part_type", v)}
                            >
                                <SelectTrigger className="h-8 text-sm">
                                    <SelectValue placeholder="All part types" />
                                </SelectTrigger>
                                <SelectContent>
                                    {filterOptions?.part_types.map(opt => (
                                        <SelectItem key={opt.value} value={opt.value}>
                                            {opt.label} ({opt.count})
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </CardContent>
                    </Card>

                </div>

                {/* Right Panel - Records Table */}
                <Card className="lg:col-span-3">
                    <CardHeader className="py-3 px-4 flex flex-row items-center justify-between">
                        <div>
                            <CardTitle className="text-sm font-medium">
                                Records
                                {selectedIds.size > 0 && (
                                    <span className="ml-2 text-muted-foreground font-normal">
                                        ({selectedIds.size} selected)
                                    </span>
                                )}
                            </CardTitle>
                        </div>
                        <div className="flex items-center gap-2">
                            {selectedIds.size > 0 && (
                                <Button variant="default" size="sm" asChild>
                                    <Link to="/quality/capas">
                                        <Plus className="h-4 w-4 mr-1" />
                                        Create CAPA
                                    </Link>
                                </Button>
                            )}
                            <Button variant="outline" size="sm" onClick={exportToCsv}>
                                <Download className="h-4 w-4 mr-1" />
                                Export
                            </Button>
                        </div>
                    </CardHeader>
                    <CardContent className="p-0">
                        <div className="border-t">
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead className="w-10 pl-4">
                                            <Checkbox
                                                checked={records.length > 0 && selectedIds.size === records.length}
                                                onCheckedChange={toggleSelectAll}
                                            />
                                        </TableHead>
                                        <TableHead>Part</TableHead>
                                        <TableHead>Part Type</TableHead>
                                        <TableHead>Process</TableHead>
                                        <TableHead>Defect</TableHead>
                                        <TableHead>Date</TableHead>
                                        <TableHead>Status</TableHead>
                                        <TableHead className="w-10"></TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {isLoadingRecords ? (
                                        <TableRow>
                                            <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                                                Loading...
                                            </TableCell>
                                        </TableRow>
                                    ) : records.length === 0 ? (
                                        <TableRow>
                                            <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                                                No defects found
                                            </TableCell>
                                        </TableRow>
                                    ) : (
                                        records.map((record) => (
                                            <TableRow
                                                key={record.id}
                                                className={cn(
                                                    selectedIds.has(record.id) && "bg-muted/30"
                                                )}
                                            >
                                                <TableCell className="pl-4">
                                                    <Checkbox
                                                        checked={selectedIds.has(record.id)}
                                                        onCheckedChange={() => toggleSelection(record.id)}
                                                    />
                                                </TableCell>
                                                <TableCell className="font-mono text-xs">
                                                    {record.part_erp_id}
                                                </TableCell>
                                                <TableCell className="text-sm">
                                                    {record.part_type}
                                                </TableCell>
                                                <TableCell className="text-sm">
                                                    {record.step}
                                                </TableCell>
                                                <TableCell>
                                                    <div className="flex flex-wrap gap-1">
                                                        {record.error_types.slice(0, 2).map((err, i) => (
                                                            <span
                                                                key={i}
                                                                className="text-xs bg-muted px-1.5 py-0.5 rounded"
                                                            >
                                                                {err}
                                                            </span>
                                                        ))}
                                                        {record.error_types.length > 2 && (
                                                            <span className="text-xs text-muted-foreground">
                                                                +{record.error_types.length - 2}
                                                            </span>
                                                        )}
                                                    </div>
                                                </TableCell>
                                                <TableCell className="text-xs text-muted-foreground">
                                                    {record.date_formatted}
                                                </TableCell>
                                                <TableCell>
                                                    <Badge
                                                        variant={
                                                            record.disposition_status === "CLOSED" ? "secondary" :
                                                            record.disposition_status === "IN_PROGRESS" ? "default" :
                                                            "outline"
                                                        }
                                                        className="text-xs"
                                                    >
                                                        {record.disposition_type || "Pending"}
                                                    </Badge>
                                                </TableCell>
                                                <TableCell>
                                                    {record.part_id && (
                                                        <Button variant="ghost" size="sm" className="h-7 w-7 p-0" asChild>
                                                            <Link to={`/editors/parts/${record.part_id}`}>
                                                                <ExternalLink className="h-3.5 w-3.5" />
                                                            </Link>
                                                        </Button>
                                                    )}
                                                </TableCell>
                                            </TableRow>
                                        ))
                                    )}
                                </TableBody>
                            </Table>
                        </div>
                        {records.length > 0 && totalRecords > records.length && (
                            <div className="text-xs text-muted-foreground text-center py-2 border-t">
                                Showing {records.length} of {totalRecords}
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}

export default DefectAnalysisPage;
