import { useMemo } from "react";
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { cn } from "@/lib/utils";

export interface HorizontalBarDataItem {
  name: string;
  value: number;
  color?: string;
}

export interface HorizontalBarChartProps {
  data: HorizontalBarDataItem[];
  maxItems?: number;
  barHeight?: number;
  color?: string;
  showValues?: boolean;
  valueFormatter?: (value: number) => string;
  className?: string;
}

export function HorizontalBarChart({
  data,
  maxItems = 10,
  barHeight = 28,
  color = "var(--chart-1)",
  showValues = true,
  valueFormatter = (v) => v.toString(),
  className,
}: HorizontalBarChartProps) {
  const chartData = useMemo(
    () =>
      data
        .slice(0, maxItems)
        .sort((a, b) => b.value - a.value)
        .map((item) => ({
          ...item,
          color: item.color || color,
        })),
    [data, maxItems, color]
  );

  const maxValue = useMemo(
    () => Math.max(...chartData.map((d) => d.value), 1),
    [chartData]
  );

  const chartHeight = chartData.length * barHeight + 20;

  if (chartData.length === 0) {
    return (
      <div className={cn("flex items-center justify-center h-32 text-muted-foreground text-sm", className)}>
        No data available
      </div>
    );
  }

  return (
    <div className={className}>
      <ResponsiveContainer width="100%" height={chartHeight}>
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 0, right: showValues ? 50 : 10, left: 10, bottom: 0 }}
        >
          <XAxis type="number" hide domain={[0, maxValue * 1.1]} />
          <YAxis
            type="category"
            dataKey="name"
            axisLine={false}
            tickLine={false}
            width={120}
            tick={{ fontSize: 12, fill: "var(--muted-foreground)" }}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const item = payload[0].payload;
              return (
                <div className="bg-background border border-border rounded-lg px-3 py-2 shadow-lg text-xs">
                  <div className="font-medium">{item.name}</div>
                  <div className="text-muted-foreground">{valueFormatter(item.value)}</div>
                </div>
              );
            }}
          />
          <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={barHeight - 8}>
            {chartData.map((entry) => (
              <Cell key={entry.name} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {showValues && (
        <div
          className="absolute right-2 top-0"
          style={{ height: chartHeight }}
        >
          {chartData.map((item, index) => (
            <div
              key={item.name}
              className="absolute right-0 text-xs font-medium tabular-nums text-foreground"
              style={{
                top: index * barHeight + barHeight / 2 - 6,
              }}
            >
              {valueFormatter(item.value)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Simpler version without recharts for basic use cases
export interface SimpleBarItemProps {
  label: string;
  value: number;
  maxValue: number;
  color?: string;
  valueFormatter?: (value: number) => string;
  onClick?: (name: string) => void;
}

export function SimpleBarItem({
  label,
  value,
  maxValue,
  color = "var(--chart-1)",
  valueFormatter = (v) => v.toString(),
  onClick,
}: SimpleBarItemProps) {
  const percentage = maxValue > 0 ? (value / maxValue) * 100 : 0;

  return (
    <div
      className={cn("space-y-1", onClick && "cursor-pointer hover:opacity-80")}
      onClick={() => onClick?.(label)}
    >
      <div className="flex justify-between text-sm">
        <span className="text-muted-foreground truncate">{label}</span>
        <span className="font-medium tabular-nums">{valueFormatter(value)}</span>
      </div>
      <div className="h-2 bg-muted rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-300"
          style={{
            width: `${percentage}%`,
            backgroundColor: color,
          }}
        />
      </div>
    </div>
  );
}

export interface SimpleHorizontalBarChartProps {
  data: HorizontalBarDataItem[];
  maxItems?: number;
  color?: string;
  valueFormatter?: (value: number) => string;
  className?: string;
  onBarClick?: (name: string) => void;
}

export function SimpleHorizontalBarChart({
  data,
  maxItems = 5,
  color = "var(--chart-1)",
  valueFormatter = (v) => v.toString(),
  className,
  onBarClick,
}: SimpleHorizontalBarChartProps) {
  const sortedData = useMemo(
    () => [...data].sort((a, b) => b.value - a.value).slice(0, maxItems),
    [data, maxItems]
  );

  const maxValue = useMemo(
    () => Math.max(...sortedData.map((d) => d.value), 1),
    [sortedData]
  );

  if (sortedData.length === 0) {
    return (
      <div className={cn("flex items-center justify-center h-32 text-muted-foreground text-sm", className)}>
        No data available
      </div>
    );
  }

  return (
    <div className={cn("space-y-3", className)}>
      {sortedData.map((item) => (
        <SimpleBarItem
          key={item.name}
          label={item.name}
          value={item.value}
          maxValue={maxValue}
          color={item.color || color}
          valueFormatter={valueFormatter}
          onClick={onBarClick}
        />
      ))}
    </div>
  );
}
