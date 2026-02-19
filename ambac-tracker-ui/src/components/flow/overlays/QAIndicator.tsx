import { cn } from '@/lib/utils';
import { ClipboardCheck, FlaskConical } from 'lucide-react';

interface QAIndicatorProps {
  /** Whether QA signoff is required */
  qaRequired?: boolean;
  /** Sampling rate percentage (0-100) */
  samplingRate?: number;
  className?: string;
}

/**
 * Indicator showing QA requirements for a step.
 */
export function QAIndicator({ qaRequired, samplingRate, className }: QAIndicatorProps) {
  if (!qaRequired && !samplingRate) return null;

  return (
    <div className={cn('flex items-center gap-1', className)}>
      {qaRequired && (
        <div
          className="flex items-center gap-0.5 px-1.5 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300"
          title="QA Signoff Required"
        >
          <ClipboardCheck className="h-3 w-3" />
          <span>QA</span>
        </div>
      )}
      {samplingRate !== undefined && samplingRate > 0 && (
        <div
          className="flex items-center gap-0.5 px-1.5 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300"
          title={`${samplingRate}% Sampling`}
        >
          <FlaskConical className="h-3 w-3" />
          <span>{samplingRate}%</span>
        </div>
      )}
    </div>
  );
}
