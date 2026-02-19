import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Legend,
} from "recharts";
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import { cn } from "@/lib/utils";

export interface StackedBarSeries {
  dataKey: string;
  label: string;
  color: string;
}

export interface StackedBarDataPoint {
  category: string;
  [key: string]: string | number;
}

export interface StackedBarChartProps {
  data: StackedBarDataPoint[];
  series: StackedBarSeries[];
  height?: number;
  barSize?: number;
  showGrid?: boolean;
  showLegend?: boolean;
  layout?: "horizontal" | "vertical";
  xAxisFormatter?: (value: string) => string;
  yAxisFormatter?: (value: number) => string;
  className?: string;
}

export function StackedBarChart({
  data,
  series,
  height = 220,
  barSize,
  showGrid = true,
  showLegend = true,
  layout = "horizontal",
  xAxisFormatter,
  yAxisFormatter,
  className,
}: StackedBarChartProps) {
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

  if (data.length === 0) {
    return (
      <div className={cn("flex items-center justify-center text-muted-foreground text-sm", className)} style={{ height }}>
        No data available
      </div>
    );
  }

  const isVertical = layout === "vertical";

  return (
    <ChartContainer config={chartConfig} className={cn("w-full", className)} style={{ height }}>
      <BarChart
        data={data}
        layout={isVertical ? "vertical" : "horizontal"}
        margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
      >
        {showGrid && <CartesianGrid strokeDasharray="3 3" vertical={!isVertical} horizontal={isVertical} />}
        {isVertical ? (
          <>
            <XAxis type="number" tickFormatter={yAxisFormatter} tickLine={false} axisLine={false} tick={{ fontSize: 11 }} />
            <YAxis
              type="category"
              dataKey="category"
              tickFormatter={xAxisFormatter}
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 11 }}
              width={80}
            />
          </>
        ) : (
          <>
            <XAxis
              dataKey="category"
              tickFormatter={xAxisFormatter}
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 11 }}
            />
            <YAxis
              tickFormatter={yAxisFormatter}
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 11 }}
              width={40}
            />
          </>
        )}
        <ChartTooltip content={<ChartTooltipContent />} />
        {showLegend && (
          <Legend
            verticalAlign="top"
            wrapperStyle={{ paddingBottom: 10 }}
            formatter={(value) => chartConfig[value]?.label || value}
          />
        )}
        {series.map((s, index) => (
          <Bar
            key={s.dataKey}
            dataKey={s.dataKey}
            stackId="stack"
            fill={s.color}
            radius={index === series.length - 1 ? [4, 4, 0, 0] : [0, 0, 0, 0]}
            barSize={barSize}
          />
        ))}
      </BarChart>
    </ChartContainer>
  );
}

// Variant for aging buckets (0-3d, 4-7d, etc.)
export interface AgingBucketData {
  bucket: string;
  count: number;
  color?: string;
}

export interface AgingBucketChartProps {
  data: AgingBucketData[];
  height?: number;
  defaultColor?: string;
  className?: string;
}

export function AgingBucketChart({
  data,
  height = 180,
  defaultColor = "var(--chart-1)",
  className,
}: AgingBucketChartProps) {
  const chartData = data.map((d) => ({
    category: d.bucket,
    count: d.count,
    fill: d.color || defaultColor,
  }));

  const chartConfig: ChartConfig = {
    count: {
      label: "Count",
      color: defaultColor,
    },
  };

  if (data.length === 0) {
    return (
      <div className={cn("flex items-center justify-center text-muted-foreground text-sm", className)} style={{ height }}>
        No data available
      </div>
    );
  }

  return (
    <ChartContainer config={chartConfig} className={cn("w-full", className)} style={{ height }}>
      <BarChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="category" tickLine={false} axisLine={false} tick={{ fontSize: 11 }} />
        <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 11 }} width={30} />
        <ChartTooltip
          content={
            <ChartTooltipContent
              formatter={(value) => [`${value}`, "Count"]}
            />
          }
        />
        <Bar dataKey="count" radius={[4, 4, 0, 0]}>
          {chartData.map((entry, index) => (
            <Bar key={`cell-${index}`} dataKey="count" fill={entry.fill} />
          ))}
        </Bar>
      </BarChart>
    </ChartContainer>
  );
}
