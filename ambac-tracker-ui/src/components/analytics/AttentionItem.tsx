import { Link } from "@tanstack/react-router";
import { AlertTriangle, AlertCircle, Info, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

export type Severity = "critical" | "high" | "medium" | "low";

export interface AttentionItemProps {
  severity: Severity;
  message: string;
  count: number;
  link: string;
  linkParams?: Record<string, string>;
}

const severityConfig: Record<
  Severity,
  {
    icon: typeof AlertTriangle;
    bgColor: string;
    textColor: string;
    badgeColor: string;
    label: string;
  }
> = {
  critical: {
    icon: AlertTriangle,
    bgColor: "bg-destructive/10",
    textColor: "text-destructive",
    badgeColor: "bg-destructive text-destructive-foreground",
    label: "Critical",
  },
  high: {
    icon: AlertCircle,
    bgColor: "bg-orange-500/10",
    textColor: "text-orange-600",
    badgeColor: "bg-orange-500 text-white",
    label: "High",
  },
  medium: {
    icon: AlertCircle,
    bgColor: "bg-yellow-500/10",
    textColor: "text-yellow-600",
    badgeColor: "bg-yellow-500 text-white",
    label: "Medium",
  },
  low: {
    icon: Info,
    bgColor: "bg-blue-500/10",
    textColor: "text-blue-600",
    badgeColor: "bg-blue-500 text-white",
    label: "Low",
  },
};

export function AttentionItem({
  severity,
  message,
  count,
  link,
  linkParams,
}: AttentionItemProps) {
  const config = severityConfig[severity];
  const Icon = config.icon;

  return (
    <Link
      to={link}
      search={linkParams}
      className={cn(
        "flex items-center gap-3 p-3 rounded-lg transition-colors",
        config.bgColor,
        "hover:opacity-80"
      )}
    >
      <Icon className={cn("h-5 w-5 shrink-0", config.textColor)} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-foreground truncate">{message}</p>
      </div>
      <span
        className={cn(
          "inline-flex items-center justify-center px-2 py-0.5 rounded text-xs font-semibold shrink-0",
          config.badgeColor
        )}
      >
        {count}
      </span>
      <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
    </Link>
  );
}

export interface AttentionListProps {
  items: AttentionItemProps[];
  className?: string;
  emptyMessage?: string;
}

export function AttentionList({
  items,
  className,
  emptyMessage = "No items requiring attention",
}: AttentionListProps) {
  if (items.length === 0) {
    return (
      <div className={cn("text-sm text-muted-foreground text-center py-4", className)}>
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      {items.map((item, index) => (
        <AttentionItem key={index} {...item} />
      ))}
    </div>
  );
}
