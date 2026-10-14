import type { ComponentProps } from "react";
import { Handle, type HandleProps } from "@xyflow/react";

import { cn } from "@/lib/utils";

export type BaseHandleProps = HandleProps;

export function BaseHandle({
  className,
  children,
  ...props
}: ComponentProps<typeof Handle>) {
  return (
    <Handle
      {...props}
      className={cn(
        "dark:border-secondary dark:bg-secondary h-[11px] w-[11px] rounded-full border border-slate-300 bg-slate-100 transition",
        // An 11px dot is a hard target to hit, and harder still on the shop's
        // tablets — connecting a Pass or Fail branch meant pixel-hunting. The dot
        // stays 11px so the canvas looks the same, and an invisible pseudo-element
        // widens what the pointer can actually grab to ~31px. `-inset-[10px]`
        // rather than a bigger handle because growing the handle itself shifts
        // every edge's anchor point and the node's measured size, which the ELK
        // layout then lays out around.
        "before:absolute before:-inset-[10px] before:rounded-full before:content-['']",
        // And a little feedback, so it is clear the thing is grabbable.
        "hover:scale-125",
        className,
      )}
    >
      {children}
    </Handle>
  );
}
