import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Format a duty's date range. Shows "start–end" for multi-day, just "start" for single-day. */
export function formatDutyDates(startDate: string, durationDays: number): string {
  if (durationDays <= 1) return startDate;
  const start = new Date(startDate + "T00:00:00");
  const end = new Date(start);
  end.setDate(end.getDate() + durationDays - 1);
  const endStr = end.toISOString().slice(0, 10);
  return `${startDate}\u2013${endStr}`;
}
