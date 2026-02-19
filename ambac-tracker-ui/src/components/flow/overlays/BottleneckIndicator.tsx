import { cn } from '@/lib/utils';
import { AlertTriangle } from 'lucide-react';

interface BottleneckIndicatorProps {
  /** Severity level 0-1 (0 = fine, 1 = severe bottleneck) */
  severity: number;
  className?: string;
  /** Show icon badge or just glow */
  showBadge?: boolean;
}

/**
 * Get color class based on severity.
 */
function getSeverityColor(severity: number): string {
  if (severity < 0.3) return 'text-green-500';
  if (severity < 0.6) return 'text-yellow-500';
  if (severity < 0.8) return 'text-orange-500';
  return 'text-red-500';
}

/**
 * Get glow class based on severity.
 */
function getGlowClass(severity: number): string {
  if (severity < 0.3) return '';
  if (severity < 0.6) return 'shadow-yellow-500/30 shadow-lg';
  if (severity < 0.8) return 'shadow-orange-500/40 shadow-lg';
  return 'shadow-red-500/50 shadow-xl animate-pulse';
}

/**
 * Visual indicator for bottleneck steps.
 * Can be used as a badge or applied as a glow effect.
 */
export function BottleneckIndicator({
  severity,
  className,
  showBadge = true,
}: BottleneckIndicatorProps) {
  if (severity < 0.3) return null;

  if (!showBadge) {
    // Return class name for parent to apply
    return null;
  }

  return (
    <div
      className={cn(
        'flex items-center gap-1 px-1.5 py-0.5 rounded-full text-xs font-medium',
        'bg-background border shadow-sm',
        getSeverityColor(severity),
        className
      )}
    >
      <AlertTriangle className="h-3 w-3" />
      {severity >= 0.8 && <span>Bottleneck</span>}
    </div>
  );
}

/**
 * Hook to get bottleneck styling for a node.
 */
export function useBottleneckStyle(severity: number) {
  return {
    className: getGlowClass(severity),
    isBottleneck: severity >= 0.6,
    isSevere: severity >= 0.8,
  };
}
