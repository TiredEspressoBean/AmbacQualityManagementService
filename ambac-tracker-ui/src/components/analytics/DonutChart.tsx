import { useMemo } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { cn } from "@/lib/utils";

export interface DonutChartDataItem {
  name: string;
  value: number;
  color?: string;
}

export interface DonutChartProps {
  data: DonutChartDataItem[];
  innerRadius?: number;
  outerRadius?: number;
  paddingAngle?: number;
  showLegend?: boolean;
  legendPosition?: "right" | "bottom";
  className?: string;
  height?: number;
  colors?: string[];
  centerLabel?: string;
  centerValue?: string | number;
}

const DEFAULT_COLORS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
];

export function DonutChart({
  data,
  innerRadius = 50,
  outerRadius = 75,
  paddingAngle = 3,
  showLegend = true,
  legendPosition = "right",
  className,
  height = 180,
  colors = DEFAULT_COLORS,
  centerLabel,
  centerValue,
}: DonutChartProps) {
  const total = useMemo(() => data.reduce((sum, d) => sum + d.value, 0), [data]);

  const chartData = useMemo(
    () =>
      data.map((item, i) => ({
        ...item,
        color: item.color || colors[i % colors.length],
        percentage: total > 0 ? Math.round((item.value / total) * 100) : 0,
      })),
    [data, colors, total]
  );

  const isHorizontal = legendPosition === "right";

  return (
    <div
      className={cn(
        "flex",
        isHorizontal ? "flex-row items-center gap-6" : "flex-col items-center gap-4",
        className
      )}
    >
      <div
        className="relative shrink-0"
        style={{
          width: isHorizontal ? outerRadius * 2 + 16 : "100%",
          height: height,
        }}
      >
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              dataKey="value"
              nameKey="name"
              innerRadius={innerRadius}
              outerRadius={outerRadius}
              paddingAngle={paddingAngle}
              cx="50%"
              cy="50%"
            >
              {chartData.map((entry) => (
                <Cell key={entry.name} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const item = payload[0].payload;
                return (
                  <div className="bg-background border border-border rounded-lg px-3 py-2 shadow-lg text-xs">
                    <div className="font-medium">{item.name}</div>
                    <div className="text-muted-foreground">
                      {item.value} ({item.percentage}%)
                    </div>
                  </div>
                );
              }}
            />
          </PieChart>
        </ResponsiveContainer>
        {(centerLabel || centerValue) && (
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            {centerValue !== undefined && (
              <span className="text-2xl font-bold">{centerValue}</span>
            )}
            {centerLabel && (
              <span className="text-xs text-muted-foreground">{centerLabel}</span>
            )}
          </div>
        )}
      </div>

      {showLegend && (
        <div
          className={cn(
            "space-y-2 text-sm",
            !isHorizontal && "flex flex-wrap gap-x-4 gap-y-2 space-y-0 justify-center"
          )}
        >
          {chartData.map((item) => (
            <div key={item.name} className="flex items-center gap-2">
              <span
                className="inline-block h-3 w-3 rounded-sm shrink-0"
                style={{ background: item.color }}
              />
              <span className="text-muted-foreground">{item.name}</span>
              <span className="font-medium ml-auto tabular-nums">{item.percentage}%</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
