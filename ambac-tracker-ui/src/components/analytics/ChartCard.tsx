import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ChartCardProps {
  title: string;
  description?: string;
  children: React.ReactNode;
  controls?: React.ReactNode;
  className?: string;
  contentClassName?: string;
  isLoading?: boolean;
  loadingHeight?: string;
}

export function ChartCard({
  title,
  description,
  children,
  controls,
  className,
  contentClassName,
  isLoading = false,
  loadingHeight = "h-[220px]",
}: ChartCardProps) {
  return (
    <Card className={cn("border-muted/40", className)}>
      <CardHeader className="pb-2 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <CardTitle className="text-base sm:text-lg">{title}</CardTitle>
          {description && (
            <CardDescription className="text-xs sm:text-sm">
              {description}
            </CardDescription>
          )}
        </div>
        {controls && (
          <div className="flex flex-wrap items-center gap-3">{controls}</div>
        )}
      </CardHeader>
      <CardContent className={cn("pt-0", contentClassName)}>
        {isLoading ? (
          <div className={cn("w-full flex items-center justify-center", loadingHeight)}>
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          children
        )}
      </CardContent>
    </Card>
  );
}
