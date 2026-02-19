import { cn } from '@/lib/utils';
import { RefreshCw } from 'lucide-react';

interface VisitCountBadgeProps {
  current: number;
  max: number;
  className?: string;
}

/**
 * Badge showing rework visit count (e.g., "2/3").
 * Changes color as visits approach max.
 */
export function VisitCountBadge({ current, max, className }: VisitCountBadgeProps) {
  const ratio = current / max;

  const colorClass =
    ratio < 0.5
      ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
      : ratio < 0.8
        ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300'
        : 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300';

  return (
    <div
      className={cn(
        'flex items-center gap-1 px-1.5 py-0.5 rounded-full text-xs font-medium',
        colorClass,
        className
      )}
    >
      <RefreshCw className="h-3 w-3" />
      <span>
        {current}/{max}
      </span>
    </div>
  );
}
