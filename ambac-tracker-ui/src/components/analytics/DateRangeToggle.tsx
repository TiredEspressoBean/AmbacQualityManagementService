import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type DateRange = "7d" | "30d" | "60d" | "90d";

export interface DateRangeToggleProps {
  value: DateRange;
  onChange: (value: DateRange) => void;
  options?: DateRange[];
  className?: string;
}

const rangeLabels: Record<DateRange, string> = {
  "7d": "7 days",
  "30d": "30 days",
  "60d": "60 days",
  "90d": "90 days",
};

export function DateRangeToggle({
  value,
  onChange,
  options = ["30d", "60d", "90d"],
  className,
}: DateRangeToggleProps) {
  return (
    <div className={cn("flex items-center gap-1", className)}>
      {options.map((range) => (
        <Button
          key={range}
          variant={value === range ? "default" : "outline"}
          size="sm"
          onClick={() => onChange(range)}
          className="h-8 px-3 text-xs"
        >
          {rangeLabels[range]}
        </Button>
      ))}
    </div>
  );
}

// Helper to convert range to days number
export function rangeToDays(range: DateRange): number {
  const map: Record<DateRange, number> = {
    "7d": 7,
    "30d": 30,
    "60d": 60,
    "90d": 90,
  };
  return map[range];
}
