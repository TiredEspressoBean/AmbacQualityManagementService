// Analytics shared components
// All components use ShadCN/ui primitives where applicable

export { KpiCard, type KpiCardProps } from "./KpiCard";
export { KpiGrid, type KpiGridProps } from "./KpiGrid";
export { ChartCard, type ChartCardProps } from "./ChartCard";
export { DateRangeToggle, rangeToDays, type DateRange, type DateRangeToggleProps } from "./DateRangeToggle";
export { AttentionItem, AttentionList, type AttentionItemProps, type AttentionListProps, type Severity } from "./AttentionItem";
export { DonutChart, type DonutChartProps, type DonutChartDataItem } from "./DonutChart";
export {
  HorizontalBarChart,
  SimpleBarItem,
  SimpleHorizontalBarChart,
  type HorizontalBarChartProps,
  type HorizontalBarDataItem,
  type SimpleBarItemProps,
  type SimpleHorizontalBarChartProps,
} from "./HorizontalBarChart";
export {
  TrendLineChart,
  SimpleTrendLine,
  type TrendLineChartProps,
  type TrendDataPoint,
  type TrendLineSeries,
  type SimpleTrendLineProps,
} from "./TrendLineChart";
export {
  StackedBarChart,
  AgingBucketChart,
  type StackedBarChartProps,
  type StackedBarSeries,
  type StackedBarDataPoint,
  type AgingBucketChartProps,
  type AgingBucketData,
} from "./StackedBarChart";
export {
  AnalyticsTable,
  StatusBadge,
  DateCell,
  type AnalyticsTableProps,
  type AnalyticsColumnDef,
  type SortDirection,
} from "./AnalyticsTable";
