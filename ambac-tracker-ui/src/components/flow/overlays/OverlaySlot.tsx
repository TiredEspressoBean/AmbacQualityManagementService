import { type ReactNode } from 'react';
import { cn } from '@/lib/utils';

export type OverlayPosition =
  | 'top-left'
  | 'top-right'
  | 'bottom-left'
  | 'bottom-right'
  | 'top-center'
  | 'bottom-center';

interface OverlaySlotProps {
  position: OverlayPosition;
  children: ReactNode;
  className?: string;
}

const positionClasses: Record<OverlayPosition, string> = {
  'top-left': 'absolute -top-2 -left-2',
  'top-right': 'absolute -top-2 -right-2',
  'bottom-left': 'absolute -bottom-2 -left-2',
  'bottom-right': 'absolute -bottom-2 -right-2',
  'top-center': 'absolute -top-2 left-1/2 -translate-x-1/2',
  'bottom-center': 'absolute -bottom-2 left-1/2 -translate-x-1/2',
};

/**
 * Container for positioning overlays on nodes.
 */
export function OverlaySlot({ position, children, className }: OverlaySlotProps) {
  return (
    <div className={cn(positionClasses[position], 'z-10', className)}>
      {children}
    </div>
  );
}
