import { cn } from '@/lib/utils';
import {
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  PlayCircle,
  PauseCircle,
} from 'lucide-react';

type StatusType =
  | 'pending'
  | 'in_progress'
  | 'completed'
  | 'approved'
  | 'rejected'
  | 'on_hold'
  | 'cancelled';

interface StatusBadgeProps {
  status: StatusType | string;
  className?: string;
  showIcon?: boolean;
}

const statusConfig: Record<
  StatusType,
  { icon: typeof Clock; colorClass: string; label: string }
> = {
  pending: {
    icon: Clock,
    colorClass: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
    label: 'Pending',
  },
  in_progress: {
    icon: PlayCircle,
    colorClass: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
    label: 'In Progress',
  },
  completed: {
    icon: CheckCircle,
    colorClass: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
    label: 'Completed',
  },
  approved: {
    icon: CheckCircle,
    colorClass: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
    label: 'Approved',
  },
  rejected: {
    icon: XCircle,
    colorClass: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
    label: 'Rejected',
  },
  on_hold: {
    icon: PauseCircle,
    colorClass: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
    label: 'On Hold',
  },
  cancelled: {
    icon: AlertCircle,
    colorClass: 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400',
    label: 'Cancelled',
  },
};

/**
 * Generic status badge for flow nodes.
 * Used for CAPA, approval, and other workflow states.
 */
export function StatusBadge({ status, className, showIcon = true }: StatusBadgeProps) {
  const config = statusConfig[status as StatusType] || {
    icon: AlertCircle,
    colorClass: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
    label: status,
  };

  const Icon = config.icon;

  return (
    <div
      className={cn(
        'flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium',
        config.colorClass,
        className
      )}
    >
      {showIcon && <Icon className="h-3 w-3" />}
      <span>{config.label}</span>
    </div>
  );
}
