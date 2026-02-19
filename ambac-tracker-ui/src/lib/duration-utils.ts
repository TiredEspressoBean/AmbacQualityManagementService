/**
 * Duration utility functions for converting between:
 * - Minutes (for user input)
 * - HH:MM:SS format (for Django DurationField)
 * - Human-readable display (e.g., "2h 30m")
 */

/** Parse duration string (HH:MM:SS or similar) to minutes */
export function parseDurationToMinutes(duration: string | null | undefined): number | '' {
  if (!duration) return '';
  // Handle "HH:MM:SS" format
  const match = duration.match(/^(\d+):(\d+):(\d+)$/);
  if (match) {
    const hours = parseInt(match[1]);
    const minutes = parseInt(match[2]);
    return hours * 60 + minutes;
  }
  // Handle "D days, HH:MM:SS" format
  const daysMatch = duration.match(/^(\d+)\s*days?,?\s*(\d+):(\d+):(\d+)$/);
  if (daysMatch) {
    const days = parseInt(daysMatch[1]);
    const hours = parseInt(daysMatch[2]);
    const minutes = parseInt(daysMatch[3]);
    return days * 24 * 60 + hours * 60 + minutes;
  }
  // Try parsing as a number (already minutes)
  const num = parseInt(duration);
  return isNaN(num) ? '' : num;
}

/** Format minutes to HH:MM:SS for backend (Django DurationField) */
export function formatMinutesToDuration(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:00`;
}

/** Format duration for human-readable display */
export function formatDurationDisplay(duration: string | null | undefined): string {
  const minutes = parseDurationToMinutes(duration);
  if (minutes === '' || minutes === 0) return 'Not set';
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  if (mins === 0) return `${hours}h`;
  return `${hours}h ${mins}m`;
}

/** Parse seconds to minutes */
export function secondsToMinutes(seconds: number | null | undefined): number | '' {
  if (seconds === null || seconds === undefined) return '';
  return Math.round(seconds / 60);
}

/** Convert minutes to seconds */
export function minutesToSeconds(minutes: number): number {
  return minutes * 60;
}
