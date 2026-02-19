import { Link } from "@tanstack/react-router";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

export interface KpiCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  link?: string;
  linkParams?: Record<string, string>;
  trend?: {
    value: number;
    direction: "up" | "down" | "flat";
  };
  variant?: "default" | "warning" | "danger";
  isLoading?: boolean;
  formatValue?: (value: string | number) => string;
}

export function KpiCard({
  title,
  value,
  subtitle,
  icon: Icon,
  link,
  linkParams,
  trend,
  variant = "default",
  isLoading = false,
  formatValue,
}: KpiCardProps) {
  const displayValue = formatValue ? formatValue(value) : value;

  const variantStyles = {
    default: "border-muted/40 hover:border-primary/50",
    warning: "border-yellow-500/40 hover:border-yellow-500/60",
    danger: "border-destructive/40 hover:border-destructive/60",
  };

  const valueStyles = {
    default: "text-foreground",
    warning: "text-yellow-600",
    danger: "text-destructive",
  };

  const trendIcon = {
    up: TrendingUp,
    down: TrendingDown,
    flat: Minus,
  };

  const trendColor = {
    up: "text-green-600",
    down: "text-red-600",
    flat: "text-muted-foreground",
  };

  const cardContent = (
    <Card
      className={cn(
        variantStyles[variant],
        "hover:shadow-sm transition-all",
        link && "cursor-pointer"
      )}
    >
      <CardHeader className="pb-1 flex flex-row items-center justify-between space-y-0">
        <CardTitle className="text-xs font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent className="pt-0">
        {isLoading ? (
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        ) : (
          <>
            <div className="flex items-baseline gap-2">
              <span className={cn("text-2xl font-bold", valueStyles[variant])}>
                {displayValue}
              </span>
              {trend && (
                <span className={cn("flex items-center text-xs", trendColor[trend.direction])}>
                  {(() => {
                    const TrendIcon = trendIcon[trend.direction];
                    return <TrendIcon className="h-3 w-3 mr-0.5" />;
                  })()}
                  {trend.value}%
                </span>
              )}
            </div>
            {subtitle && (
              <p className="text-xs text-muted-foreground">{subtitle}</p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );

  if (link) {
    return (
      <Link to={link} search={linkParams} className="block">
        {cardContent}
      </Link>
    );
  }

  return cardContent;
}
