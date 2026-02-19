import { useState, useMemo } from "react";
import { Link } from "@tanstack/react-router";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ArrowUpDown, ArrowUp, ArrowDown, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

export type SortDirection = "asc" | "desc" | null;

export interface AnalyticsColumnDef<T> {
  key: string;
  header: string;
  accessor: (row: T) => React.ReactNode;
  sortable?: boolean;
  sortValue?: (row: T) => string | number | Date;
  className?: string;
  headerClassName?: string;
}

export interface AnalyticsTableProps<T extends { id: string | number }> {
  data: T[];
  columns: AnalyticsColumnDef<T>[];
  rowLink?: (row: T) => string;
  rowLinkParams?: (row: T) => Record<string, string>;
  onRowClick?: (row: T) => void;
  maxRows?: number;
  showViewAll?: boolean;
  viewAllLink?: string;
  viewAllText?: string;
  emptyMessage?: string;
  className?: string;
  compact?: boolean;
}

export function AnalyticsTable<T extends { id: string | number }>({
  data,
  columns,
  rowLink,
  rowLinkParams,
  onRowClick,
  maxRows,
  showViewAll = false,
  viewAllLink,
  viewAllText = "View all",
  emptyMessage = "No data available",
  className,
  compact = false,
}: AnalyticsTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>(null);

  const sortedData = useMemo(() => {
    if (!sortKey || !sortDirection) return data;

    const column = columns.find((c) => c.key === sortKey);
    if (!column || !column.sortValue) return data;

    return [...data].sort((a, b) => {
      const aVal = column.sortValue!(a);
      const bVal = column.sortValue!(b);

      let comparison = 0;
      if (typeof aVal === "string" && typeof bVal === "string") {
        comparison = aVal.localeCompare(bVal);
      } else if (aVal instanceof Date && bVal instanceof Date) {
        comparison = aVal.getTime() - bVal.getTime();
      } else {
        comparison = Number(aVal) - Number(bVal);
      }

      return sortDirection === "asc" ? comparison : -comparison;
    });
  }, [data, sortKey, sortDirection, columns]);

  const displayData = maxRows ? sortedData.slice(0, maxRows) : sortedData;

  const handleSort = (key: string) => {
    if (sortKey === key) {
      if (sortDirection === "asc") {
        setSortDirection("desc");
      } else if (sortDirection === "desc") {
        setSortKey(null);
        setSortDirection(null);
      }
    } else {
      setSortKey(key);
      setSortDirection("asc");
    }
  };

  const SortIcon = ({ columnKey }: { columnKey: string }) => {
    if (sortKey !== columnKey) return <ArrowUpDown className="h-3 w-3 ml-1" />;
    if (sortDirection === "asc") return <ArrowUp className="h-3 w-3 ml-1" />;
    return <ArrowDown className="h-3 w-3 ml-1" />;
  };

  if (data.length === 0) {
    return (
      <div className={cn("text-center py-8 text-muted-foreground text-sm", className)}>
        {emptyMessage}
      </div>
    );
  }

  const rowContent = (row: T) => (
    <>
      {columns.map((column) => (
        <TableCell key={column.key} className={cn(compact && "py-2", column.className)}>
          {column.accessor(row)}
        </TableCell>
      ))}
      {(rowLink || onRowClick) && (
        <TableCell className={cn("w-8", compact && "py-2")}>
          <ChevronRight className="h-4 w-4 text-muted-foreground" />
        </TableCell>
      )}
    </>
  );

  return (
    <div className={className}>
      <Table>
        <TableHeader>
          <TableRow>
            {columns.map((column) => (
              <TableHead
                key={column.key}
                className={cn(
                  column.sortable && "cursor-pointer select-none hover:text-foreground",
                  compact && "py-2",
                  column.headerClassName
                )}
                onClick={column.sortable ? () => handleSort(column.key) : undefined}
              >
                <div className="flex items-center">
                  {column.header}
                  {column.sortable && <SortIcon columnKey={column.key} />}
                </div>
              </TableHead>
            ))}
            {(rowLink || onRowClick) && <TableHead className={cn("w-8", compact && "py-2")} />}
          </TableRow>
        </TableHeader>
        <TableBody>
          {displayData.map((row) =>
            rowLink ? (
              <TableRow key={row.id} className="cursor-pointer hover:bg-muted/50">
                <Link
                  to={rowLink(row)}
                  search={rowLinkParams?.(row)}
                  className="contents"
                >
                  {rowContent(row)}
                </Link>
              </TableRow>
            ) : onRowClick ? (
              <TableRow
                key={row.id}
                className="cursor-pointer hover:bg-muted/50"
                onClick={() => onRowClick(row)}
              >
                {rowContent(row)}
              </TableRow>
            ) : (
              <TableRow key={row.id}>{rowContent(row)}</TableRow>
            )
          )}
        </TableBody>
      </Table>

      {showViewAll && viewAllLink && data.length > (maxRows || 0) && (
        <div className="pt-3 text-center">
          <Link to={viewAllLink}>
            <Button variant="ghost" size="sm">
              {viewAllText} ({data.length})
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </Link>
        </div>
      )}
    </div>
  );
}

// Helper components for common cell types
export function StatusBadge({
  status,
  variants,
  labels,
}: {
  status: string;
  variants?: Record<string, "default" | "secondary" | "destructive" | "outline">;
  labels?: Record<string, string>;
}) {
  const defaultVariants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
    OPEN: "destructive",
    IN_PROGRESS: "default",
    PENDING: "secondary",
    COMPLETED: "outline",
    CLOSED: "outline",
  };

  const variant = variants?.[status] || defaultVariants[status] || "secondary";
  const label = labels?.[status] || status.replace(/_/g, " ");

  return <Badge variant={variant}>{label}</Badge>;
}

export function DateCell({ date, showOverdue = false }: { date: string | Date; showOverdue?: boolean }) {
  const dateObj = typeof date === "string" ? new Date(date) : date;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const isOverdue = showOverdue && dateObj < today;

  const diffDays = Math.ceil((dateObj.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));

  let text: string;
  if (diffDays === 0) text = "Today";
  else if (diffDays === 1) text = "Tomorrow";
  else if (diffDays < 0) text = `${Math.abs(diffDays)}d overdue`;
  else if (diffDays <= 7) text = `in ${diffDays}d`;
  else text = dateObj.toLocaleDateString(undefined, { month: "short", day: "numeric" });

  return (
    <span className={cn(isOverdue && "text-destructive font-medium")}>
      {text}
    </span>
  );
}
