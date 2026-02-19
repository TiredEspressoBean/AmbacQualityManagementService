import { cn } from '@/lib/utils';
import { Clock, TrendingUp } from 'lucide-react';
import type { NodeMetrics } from '../types';

interface MetricsBadgeProps {
  metrics: NodeMetrics;
  className?: string;
  /** Show compact or detailed view */
  compact?: boolean;
}

/**
 * Format milliseconds to human-readable duration.
 */
function formatDuration(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  if (ms < 3600000) return `${(ms / 60000).toFixed(1)}m`;
  return `${(ms / 3600000).toFixed(1)}h`;
}

/**
 * Badge showing performance metrics for a step.
 * Used in evaluation/bottleneck analysis mode.
 */
export function MetricsBadge({ metrics, className, compact = true }: MetricsBadgeProps) {
  if (compact) {
    return (
      <div
        className={cn(
          'flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium',
          'bg-muted text-muted-foreground',
          className
        )}
      >
        <Clock className="h-3 w-3" />
        <span>{formatDuration(metrics.avgDwellTime)}</span>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'flex flex-col gap-0.5 px-2 py-1 rounded text-xs',
        'bg-muted text-muted-foreground',
        className
      )}
    >
      <div className="flex items-center gap-1">
        <Clock className="h-3 w-3" />
        <span>Avg: {formatDuration(metrics.avgDwellTime)}</span>
      </div>
      <div className="flex items-center gap-1">
        <TrendingUp className="h-3 w-3" />
        <span>{metrics.throughput.toFixed(1)}/hr</span>
      </div>
      {metrics.passRate !== undefined && (
        <div className="text-green-600">
          Pass: {metrics.passRate.toFixed(0)}%
        </div>
      )}
    </div>
  );
}
