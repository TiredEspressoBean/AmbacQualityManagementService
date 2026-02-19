import { cn } from "@/lib/utils";

export interface KpiGridProps {
  children: React.ReactNode;
  columns?: 2 | 3 | 4 | 6 | 7 | 8;
  className?: string;
}

export function KpiGrid({ children, columns = 4, className }: KpiGridProps) {
  const colStyles = {
    2: "grid-cols-2",
    3: "grid-cols-2 lg:grid-cols-3",
    4: "grid-cols-2 lg:grid-cols-4",
    6: "grid-cols-2 md:grid-cols-3 lg:grid-cols-6",
    7: "grid-cols-2 md:grid-cols-4 lg:grid-cols-7",
    8: "grid-cols-2 md:grid-cols-4 lg:grid-cols-8",
  };

  return (
    <div className={cn("grid gap-3", colStyles[columns], className)}>
      {children}
    </div>
  );
}
