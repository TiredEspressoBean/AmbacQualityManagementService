import { useMemo } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  XAxis,
  YAxis,
} from "recharts";
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import { cn } from "@/lib/utils";

export interface TrendDataPoint {
  date: string | Date;
  [key: string]: string | number | Date | null;
}

export interface TrendLineSeries {
  dataKey: string;
  label: string;
  color: string;
  type?: "line" | "area";
  strokeDasharray?: string;
}

export interface TrendLineChartProps {
  data: TrendDataPoint[];
  series: TrendLineSeries[];
  xAxisKey?: string;
  height?: number;
  showGrid?: boolean;
  showLegend?: boolean;
  referenceLines?: { value: number; label: string; color: string }[];
  xAxisFormatter?: (value: string | Date) => string;
  yAxisFormatter?: (value: number) => string;
  tooltipFormatter?: (value: number, name: string) => string;
  yDomain?: [number | "auto", number | "auto"];
  className?: string;
}

function defaultXAxisFormatter(value: string | Date): string {
  const date = typeof value === "string" ? new Date(value) : value;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function TrendLineChart({
  data,
  series,
  xAxisKey = "date",
  height = 220,
  showGrid = true,
  showLegend: _showLegend = false,
  referenceLines = [],
  xAxisFormatter = defaultXAxisFormatter,
  yAxisFormatter,
  tooltipFormatter,
  yDomain = ["auto", "auto"],
  className,
}: TrendLineChartProps) {
  const chartConfig = useMemo((): ChartConfig => {
    const config: ChartConfig = {};
    for (const s of series) {
      config[s.dataKey] = {
        label: s.label,
        color: s.color,
      };
    }
    return config;
  }, [series]);

  const hasArea = series.some((s) => s.type === "area");

  if (data.length === 0) {
    return (
      <div className={cn("flex items-center justify-center text-muted-foreground text-sm", className)} style={{ height }}>
        No data available
      </div>
    );
  }

  return (
    <ChartContainer config={chartConfig} className={cn("w-full", className)} style={{ height }}>
      {hasArea ? (
        <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          {showGrid && <CartesianGrid strokeDasharray="3 3" vertical={false} />}
          <XAxis
            dataKey={xAxisKey}
            tickFormatter={xAxisFormatter}
            tickLine={false}
            axisLine={false}
            tick={{ fontSize: 11 }}
          />
          <YAxis
            domain={yDomain}
            tickFormatter={yAxisFormatter}
            tickLine={false}
            axisLine={false}
            tick={{ fontSize: 11 }}
            width={40}
          />
          <ChartTooltip
            content={
              <ChartTooltipContent
                labelFormatter={(value) =>
                  typeof value === "string" ? xAxisFormatter(value) : String(value)
                }
                formatter={
                  tooltipFormatter
                    ? (value, name) => tooltipFormatter(value as number, name as string)
                    : undefined
                }
              />
            }
          />
          {referenceLines.map((ref) => (
            <ReferenceLine
              key={ref.label}
              y={ref.value}
              stroke={ref.color}
              strokeDasharray="3 3"
              label={{ value: ref.label, position: "insideTopRight", fontSize: 10 }}
            />
          ))}
          {series.map((s) =>
            s.type === "area" ? (
              <Area
                key={s.dataKey}
                type="monotone"
                dataKey={s.dataKey}
                stroke={s.color}
                fill={s.color}
                fillOpacity={0.2}
                strokeWidth={2}
                dot={false}
                strokeDasharray={s.strokeDasharray}
              />
            ) : (
              <Line
                key={s.dataKey}
                type="monotone"
                dataKey={s.dataKey}
                stroke={s.color}
                strokeWidth={2}
                dot={false}
                strokeDasharray={s.strokeDasharray}
              />
            )
          )}
        </AreaChart>
      ) : (
        <LineChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          {showGrid && <CartesianGrid strokeDasharray="3 3" vertical={false} />}
          <XAxis
            dataKey={xAxisKey}
            tickFormatter={xAxisFormatter}
            tickLine={false}
            axisLine={false}
            tick={{ fontSize: 11 }}
          />
          <YAxis
            domain={yDomain}
            tickFormatter={yAxisFormatter}
            tickLine={false}
            axisLine={false}
            tick={{ fontSize: 11 }}
            width={40}
          />
          <ChartTooltip
            content={
              <ChartTooltipContent
                labelFormatter={(value) =>
                  typeof value === "string" ? xAxisFormatter(value) : String(value)
                }
                formatter={
                  tooltipFormatter
                    ? (value, name) => tooltipFormatter(value as number, name as string)
                    : undefined
                }
              />
            }
          />
          {referenceLines.map((ref) => (
            <ReferenceLine
              key={ref.label}
              y={ref.value}
              stroke={ref.color}
              strokeDasharray="3 3"
              label={{ value: ref.label, position: "insideTopRight", fontSize: 10 }}
            />
          ))}
          {series.map((s) => (
            <Line
              key={s.dataKey}
              type="monotone"
              dataKey={s.dataKey}
              stroke={s.color}
              strokeWidth={2}
              dot={false}
              strokeDasharray={s.strokeDasharray}
            />
          ))}
        </LineChart>
      )}
    </ChartContainer>
  );
}

// Simpler wrapper for single-line trends
export interface SimpleTrendLineProps {
  data: { date: string | Date; value: number | null }[];
  color?: string;
  label?: string;
  height?: number;
  showArea?: boolean;
  referenceLine?: { value: number; label: string };
  className?: string;
}

export function SimpleTrendLine({
  data,
  color = "var(--chart-1)",
  label = "Value",
  height = 200,
  showArea = false,
  referenceLine,
  className,
}: SimpleTrendLineProps) {
  return (
    <TrendLineChart
      data={data}
      series={[{ dataKey: "value", label, color, type: showArea ? "area" : "line" }]}
      referenceLines={referenceLine ? [{ ...referenceLine, color: "var(--chart-4)" }] : []}
      height={height}
      className={className}
    />
  );
}
