import { cn } from '@/lib/utils';
import { Package } from 'lucide-react';

interface PartCountBadgeProps {
  count: number;
  className?: string;
  /** Highlight when parts are present */
  highlighted?: boolean;
}

/**
 * Badge showing number of parts at a step.
 * Used in workorder progress view.
 */
export function PartCountBadge({ count, className, highlighted }: PartCountBadgeProps) {
  if (count === 0) return null;

  return (
    <div
      className={cn(
        'flex items-center gap-1 px-1.5 py-0.5 rounded-full text-xs font-medium',
        'bg-primary text-primary-foreground shadow-sm',
        highlighted && 'ring-2 ring-primary/50 ring-offset-1',
        className
      )}
    >
      <Package className="h-3 w-3" />
      <span>{count}</span>
    </div>
  );
}
