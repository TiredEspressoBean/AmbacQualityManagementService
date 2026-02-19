import * as React from "react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export interface DurationInputProps {
  /** Value in minutes */
  value: number | null | undefined;
  /** Called with value in minutes */
  onChange: (minutes: number | null) => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

/**
 * Duration input that displays as HH:MM:SS but stores value in minutes.
 * Accepts input like "1:30:00" or "1:30" or "90" (all = 90 minutes).
 */
export function DurationInput({
  value,
  onChange,
  placeholder = "HH:MM:SS",
  disabled,
  className,
}: DurationInputProps) {
  // Convert minutes to HH:MM:SS display
  const formatDisplay = (minutes: number | null | undefined): string => {
    if (minutes === null || minutes === undefined) return "";
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours.toString().padStart(2, "0")}:${mins.toString().padStart(2, "0")}:00`;
  };

  // Parse various formats to minutes
  const parseInput = (input: string): number | null => {
    const trimmed = input.trim();
    if (!trimmed) return null;

    // Handle HH:MM:SS format
    const fullMatch = trimmed.match(/^(\d+):(\d{1,2}):(\d{1,2})$/);
    if (fullMatch) {
      const hours = parseInt(fullMatch[1]) || 0;
      const mins = parseInt(fullMatch[2]) || 0;
      // Ignore seconds for storage, but accept the input
      return hours * 60 + mins;
    }

    // Handle HH:MM format
    const shortMatch = trimmed.match(/^(\d+):(\d{1,2})$/);
    if (shortMatch) {
      const hours = parseInt(shortMatch[1]) || 0;
      const mins = parseInt(shortMatch[2]) || 0;
      return hours * 60 + mins;
    }

    // Handle plain number (treat as minutes)
    const num = parseInt(trimmed);
    return isNaN(num) ? null : num;
  };

  const [displayValue, setDisplayValue] = React.useState(() => formatDisplay(value));

  // Sync display when external value changes
  React.useEffect(() => {
    setDisplayValue(formatDisplay(value));
  }, [value]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setDisplayValue(e.target.value);
  };

  const handleBlur = () => {
    const minutes = parseInput(displayValue);
    onChange(minutes);
    setDisplayValue(formatDisplay(minutes));
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      const minutes = parseInput(displayValue);
      onChange(minutes);
      setDisplayValue(formatDisplay(minutes));
    }
  };

  return (
    <Input
      type="text"
      value={displayValue}
      onChange={handleChange}
      onBlur={handleBlur}
      onKeyDown={handleKeyDown}
      placeholder={placeholder}
      disabled={disabled}
      className={cn("font-mono", className)}
    />
  );
}
